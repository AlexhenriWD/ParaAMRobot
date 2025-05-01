#!/usr/bin/env python3
import asyncio
import json
import logging
import websockets
import signal
import sys
import os
#2
# Add path to the Server directory to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("car_server.log")
    ]
)
logger = logging.getLogger("command_server")

# Import the car module that integrates all components
try:
    from car import Car
except Exception as e:
    logger.error(f"Error importing car module: {e}")
    sys.exit(1)

class CarServer:
    def __init__(self, host="0.0.0.0", port=8000):
        self.host = host
        self.port = port
        self.active_clients = set()
        
        # Initialize the car with existing module
        try:
            logger.info("Initializing car...")
            self.car = Car()
            logger.info("Car initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize car: {e}")
            raise
        
        self.running = True
    
    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        # Start the telemetry background task
        asyncio.create_task(self.telemetry_task())
        
        # Start the WebSocket server
        try:
            stop = asyncio.Future()
            async with websockets.serve(self.handle_client, self.host, self.port):
                await stop
        except Exception as e:
            logger.error(f"Server error: {e}")
            self.cleanup()
    
    async def handle_client(self, websocket, path):
        """Handle a client connection"""
        client_id = str(id(websocket))
        logger.info(f"New client connected: {client_id}")
        
        # Add client to active clients
        self.active_clients.add(websocket)
        
        try:
            async for message in websocket:
                await self.process_command(message, websocket)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            # Remove client from active clients
            self.active_clients.remove(websocket)
    
    async def process_command(self, message, websocket):
        """Process a command from a client"""
        try:
            # Split commands by newline terminator
            commands = message.strip().split('\n')
            
            for cmd in commands:
                if not cmd:
                    continue
                
                # Parse command and parameters
                cmd_parts = cmd.split('#')
                if len(cmd_parts) < 2:
                    logger.warning(f"Invalid command format: {cmd}")
                    continue
                
                cmd_type = cmd_parts[0]
                parameters = cmd_parts[1:]
                
                logger.debug(f"Processing command: {cmd_type} with parameters: {parameters}")
                
                # Route command to the appropriate mode or function in car
                if cmd_type == "CMD_MODE":
                    mode = int(parameters[0])
                    if mode == 0:   # Control mode
                        pass  # Default mode
                    elif mode == 1: # Light mode
                        asyncio.create_task(self.run_mode_function(self.car.mode_light))
                    elif mode == 2: # Line tracking mode
                        asyncio.create_task(self.run_mode_function(self.car.mode_infrared))
                    elif mode == 3: # Obstacle avoidance mode
                        asyncio.create_task(self.run_mode_function(self.car.mode_ultrasonic))
                    
                    response = {"status": "ok", "mode": mode}
                    await websocket.send(json.dumps(response))
                    
                elif cmd_type == "CMD_MOTOR":
                    if len(parameters) == 4:
                        fl = int(parameters[0])
                        bl = int(parameters[1])
                        fr = int(parameters[2])
                        br = int(parameters[3])
                        self.car.motor.set_motor_model(fl, bl, fr, br)
                        response = {"status": "ok", "motor": "set"}
                        await websocket.send(json.dumps(response))
                    
                elif cmd_type == "CMD_SERVO":
                    if len(parameters) == 2:
                        servo0 = int(parameters[0])
                        servo1 = int(parameters[1])
                        self.car.servo.set_servo_pwm('0', servo0)
                        self.car.servo.set_servo_pwm('1', servo1)
                        response = {"status": "ok", "servo": "set"}
                        await websocket.send(json.dumps(response))
                        
                # Add other command types as needed...
        
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            await self.send_error(websocket, str(e))
    
    async def run_mode_function(self, mode_function):
        """Run a specific mode function in a continuous loop"""
        try:
            # Run the mode function in a loop
            while self.running:
                mode_function()
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in mode function: {e}")
    
    async def telemetry_task(self):
        """Background task to send telemetry data to clients"""
        import time
        while self.running:
            try:
                # Collect sensor data from car
                telemetry = {
                    "battery": self.car.adc.read_adc(2) * (3 if self.car.adc.pcb_version == 1 else 2),
                    "light_left": self.car.adc.read_adc(0),
                    "light_right": self.car.adc.read_adc(1),
                    "timestamp": time.time()
                }
                
                # Try to get ultrasonic distance if available
                try:
                    telemetry["ultrasonic"] = self.car.sonic.get_distance()
                except:
                    pass
                
                # Try to get infrared data if available
                try:
                    telemetry["infrared"] = self.car.infrared.read_all_infrared()
                except:
                    pass
                
                # Send telemetry to all clients
                if self.active_clients:
                    telemetry_json = json.dumps(telemetry)
                    await asyncio.gather(
                        *[client.send(telemetry_json) for client in self.active_clients]
                    )
                
                # Wait for next telemetry update
                await asyncio.sleep(0.5)
            
            except Exception as e:
                logger.error(f"Error in telemetry task: {e}")
                await asyncio.sleep(1)  # Delay before retry
    
    async def send_error(self, websocket, error_message):
        """Send an error message to a client"""
        try:
            error_json = json.dumps({"error": error_message})
            await websocket.send(error_json)
        except Exception as e:
            logger.error(f"Error sending error message: {e}")
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources...")
        self.running = False
        
        # Stop all motors
        try:
            self.car.motor.set_motor_model(0, 0, 0, 0)
        except:
            pass
        
        # Center servos
        try:
            self.car.servo.set_servo_pwm('0', 90)
            self.car.servo.set_servo_pwm('1', 90)
        except:
            pass
        
        logger.info("Cleanup complete")

def signal_handler(sig, frame):
    """Handle Ctrl+C to properly shut down"""
    logger.info("Interrupt received, shutting down...")
    sys.exit(0)

def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start the server
    try:
        server = CarServer(host="0.0.0.0", port=8000)
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error starting server: {e}")
    finally:
        logger.info("Server shutdown complete")

if __name__ == "__main__":
    main()
