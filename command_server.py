#!/usr/bin/env python3
import asyncio
import json
import logging
import websockets
import signal
import sys
import time
from threading import Thread

# Import car component modules
from motor import Ordinary_Car
from servo import Servo
from led import Led
from adc import ADC
from ultrasonic import Ultrasonic
from infrared import Infrared
from buzzer import Buzzer

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

# Command definitions
class COMMAND:
    CMD_MOTOR = "CMD_MOTOR"
    CMD_M_MOTOR = "CMD_M_MOTOR"
    CMD_CAR_ROTATE = "CMD_CAR_ROTATE"
    CMD_LED = "CMD_LED"
    CMD_LED_MOD = "CMD_LED_MOD"
    CMD_SERVO = "CMD_SERVO"
    CMD_BUZZER = "CMD_BUZZER"
    CMD_MODE = "CMD_MODE"

class CarServer:
    def __init__(self, host="0.0.0.0", port=8000):
        self.host = host
        self.port = port
        
        # Active client connections
        self.active_clients = set()
        
        # Initialize hardware components
        logger.info("Initializing hardware components...")
        try:
            self.motor = Ordinary_Car()
            self.servo = Servo()
            self.led = Led()
            self.adc = ADC()
            self.ultrasonic = Ultrasonic()
            self.infrared = Infrared()
            self.buzzer = Buzzer()
            
            # Set default positions
            self.servo.set_servo_pwm('0', 90)  # Center servo 0
            self.servo.set_servo_pwm('1', 90)  # Center servo 1
            self.motor.set_motor_model(0, 0, 0, 0)  # Stop motors
            
            # Current operating mode
            self.current_mode = 0  # 0: Manual, 1: Light-tracking, 2: Line-tracking, 3: Obstacle avoidance
            
            # State variables
            self.running = True
            self.telemetry_interval = 0.5  # seconds
            
            logger.info("Hardware components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize hardware: {e}")
            raise
    
    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        # Start the telemetry background task
        asyncio.create_task(self.telemetry_task())
        
        # Start the mode handler background task
        asyncio.create_task(self.mode_handler_task())
        
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
                
                # Route command to appropriate handler
                if cmd_type == COMMAND.CMD_MOTOR:
                    await self.handle_motor_command(parameters)
                elif cmd_type == COMMAND.CMD_M_MOTOR:
                    await self.handle_m_motor_command(parameters)
                elif cmd_type == COMMAND.CMD_CAR_ROTATE:
                    await self.handle_car_rotate_command(parameters)
                elif cmd_type == COMMAND.CMD_LED:
                    await self.handle_led_command(parameters)
                elif cmd_type == COMMAND.CMD_LED_MOD:
                    await self.handle_led_mod_command(parameters)
                elif cmd_type == COMMAND.CMD_SERVO:
                    await self.handle_servo_command(parameters)
                elif cmd_type == COMMAND.CMD_BUZZER:
                    await self.handle_buzzer_command(parameters)
                elif cmd_type == COMMAND.CMD_MODE:
                    await self.handle_mode_command(parameters)
                else:
                    logger.warning(f"Unknown command type: {cmd_type}")
        
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            await self.send_error(websocket, str(e))
    
    async def handle_motor_command(self, parameters):
        """Handle direct motor control command"""
        if len(parameters) < 4:
            raise ValueError("Not enough parameters for motor command")
        
        # Parse motor speeds
        fl = int(parameters[0])  # Front Left
        bl = int(parameters[1])  # Back Left
        fr = int(parameters[2])  # Front Right
        br = int(parameters[3])  # Back Right
        
        # Set motor speeds
        self.motor.set_motor_model(fl, bl, fr, br)
        logger.debug(f"Motors set to FL: {fl}, BL: {bl}, FR: {fr}, BR: {br}")
    
    async def handle_m_motor_command(self, parameters):
        """Handle mecanum motor control command"""
        if len(parameters) < 4:
            raise ValueError("Not enough parameters for mecanum motor command")
        
        # Parse joystick parameters
        angle1 = float(parameters[0])
        distance1 = float(parameters[1])
        angle2 = float(parameters[2])
        distance2 = float(parameters[3])
        
        # Calculate mecanum wheel speeds based on joystick inputs
        # Implement mecanum wheel control logic here
        # This is a simplified example:
        
        import math
        
        # Convert angle to radians for math functions
        angle_rad = math.radians(angle1)
        
        # Calculate X and Y components
        x_component = -distance1 * math.sin(angle_rad)
        y_component = distance1 * math.cos(angle_rad)
        
        # Calculate rotation component (from second joystick)
        rotation = distance2 * math.sin(math.radians(angle2))
        
        # Mecanum wheel calculations
        fl = y_component + x_component - rotation
        bl = y_component - x_component - rotation
        fr = y_component - x_component + rotation
        br = y_component + x_component + rotation
        
        # Scale to motor values
        max_value = max(abs(fl), abs(bl), abs(fr), abs(br))
        if max_value > 0:
            scale = min(distance1, 4000) / max_value
            fl = int(fl * scale)
            bl = int(bl * scale)
            fr = int(fr * scale)
            br = int(br * scale)
        
        # Set motor speeds
        self.motor.set_motor_model(fl, bl, fr, br)
        logger.debug(f"Mecanum motors set to FL: {fl}, BL: {bl}, FR: {fr}, BR: {br}")
    
    async def handle_car_rotate_command(self, parameters):
        """Handle car rotation command"""
        if len(parameters) < 4:
            raise ValueError("Not enough parameters for car rotate command")
        
        # Parse parameters
        angle = float(parameters[0])
        distance = float(parameters[1])
        angle2 = float(parameters[2])
        distance2 = float(parameters[3])
        
        import math
        
        # Calculate rotation pattern
        W = 2000  # Rotation speed
        VY = int(2000 * math.cos(math.radians(angle)))
        VX = -int(2000 * math.sin(math.radians(angle)))
        
        # Calculate wheel speeds with rotation
        FR = VY - VX + W
        FL = VY + VX - W
        BL = VY - VX - W
        BR = VY + VX + W
        
        # Apply speeds
        self.motor.set_motor_model(FL, BL, FR, BR)
        
        # Sleep briefly for rotation effect
        bat_compensate = 7.5 / (self.adc.read_adc(2) * (3 if self.adc.pcb_version == 1 else 2))
        time_compensate = 0.1  # Adjust as needed
        await asyncio.sleep(5 * time_compensate * bat_compensate / 1000)
        
        logger.debug(f"Car rotating with angle: {angle}")
    
    async def handle_led_command(self, parameters):
        """Handle LED control command"""
        if len(parameters) < 4:
            raise ValueError("Not enough parameters for LED command")
        
        # Parse RGB values and LED index
        r = int(parameters[0])
        g = int(parameters[1])
        b = int(parameters[2])
        index = int(parameters[3], 16) if len(parameters) > 3 else 0xFF
        
        # Set LED colors
        self.led.ledIndex(index, r, g, b)
        logger.debug(f"LED set to R: {r}, G: {g}, B: {b}, Index: {index}")
    
    async def handle_led_mod_command(self, parameters):
        """Handle LED mode command"""
        if len(parameters) < 1:
            raise ValueError("Not enough parameters for LED mode command")
        
        # Parse mode
        mode = int(parameters[0])
        
        # Set LED mode
        if mode == 0:
            self.led.colorWipe(self.led.strip, color(0, 0, 0))  # Off
        elif mode == 1:
            # Default RGB mode - handled by LED commands
            pass
        elif mode == 2:
            # Following mode
            self.led.ledIndex(0x01, 255, 0, 0)  # Example: Red at index 1
        elif mode == 3:
            # Blink mode
            self.led.colorBlink(1)
        elif mode == 4:
            # Breathing mode - would need to be implemented
            pass
        elif mode == 5:
            # Rainbow mode - would need to be implemented
            pass
        
        logger.debug(f"LED mode set to: {mode}")
    
    async def handle_servo_command(self, parameters):
        """Handle servo control command"""
        if len(parameters) < 2:
            raise ValueError("Not enough parameters for servo command")
        
        # Parse servo angles
        servo0_angle = int(parameters[0])
        servo1_angle = int(parameters[1])
        
        # Set servo angles
        self.servo.set_servo_pwm('0', servo0_angle)
        self.servo.set_servo_pwm('1', servo1_angle)
        logger.debug(f"Servos set to Servo0: {servo0_angle}, Servo1: {servo1_angle}")
    
    async def handle_buzzer_command(self, parameters):
        """Handle buzzer control command"""
        if len(parameters) < 1:
            raise ValueError("Not enough parameters for buzzer command")
        
        # Parse buzzer state
        state = parameters[0]
        
        # Set buzzer state
        self.buzzer.set_state(state == '1')
        logger.debug(f"Buzzer state set to: {state}")
    
    async def handle_mode_command(self, parameters):
        """Handle mode control command"""
        if len(parameters) < 1:
            raise ValueError("Not enough parameters for mode command")
        
        # Parse mode
        mode = int(parameters[0])
        
        # Set current mode
        self.current_mode = mode
        logger.info(f"Operating mode changed to: {mode}")
        
        # Reset hardware for mode change
        self.motor.set_motor_model(0, 0, 0, 0)  # Stop motors
        
        # Additional setup specific to each mode can be added here
    
    async def mode_handler_task(self):
        """Background task to handle different operating modes"""
        while self.running:
            try:
                if self.current_mode == 0:
                    # Manual mode - do nothing, commands control the car
                    pass
                elif self.current_mode == 1:
                    # Light-tracking mode
                    await self.light_tracking_mode()
                elif self.current_mode == 2:
                    # Line-tracking mode
                    await self.line_tracking_mode()
                elif self.current_mode == 3:
                    # Obstacle avoidance mode
                    await self.obstacle_avoidance_mode()
                
                # Small delay to prevent CPU overuse
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in mode handler: {e}")
                await asyncio.sleep(1)  # Delay before retry
    
    async def light_tracking_mode(self):
        """Light tracking mode implementation"""
        # Read light sensor values
        left_light = self.adc.read_adc(0)
        right_light = self.adc.read_adc(1)
        
        # Logic for light tracking
        if left_light < 2.99 and right_light < 2.99:
            self.motor.set_motor_model(600, 600, 600, 600)  # Forward
        elif abs(left_light - right_light) < 0.15:
            self.motor.set_motor_model(0, 0, 0, 0)  # Stop
        elif left_light > 3 or right_light > 3:
            if left_light > right_light:
                self.motor.set_motor_model(-1200, -1200, 1400, 1400)  # Turn left
            else:
                self.motor.set_motor_model(1400, 1400, -1200, -1200)  # Turn right
    
    async def line_tracking_mode(self):
        """Line tracking mode implementation"""
        # Read infrared sensors
        infrared_value = self.infrared.read_all_infrared()
        
        # Logic for line tracking
        if infrared_value == 2:  # Middle sensor detects line
            self.motor.set_motor_model(800, 800, 800, 800)  # Forward
        elif infrared_value == 4:  # Right sensor detects line
            self.motor.set_motor_model(-1500, -1500, 2500, 2500)  # Turn left
        elif infrared_value == 6:  # Middle and right sensors detect line
            self.motor.set_motor_model(-2000, -2000, 4000, 4000)  # Turn left sharper
        elif infrared_value == 1:  # Left sensor detects line
            self.motor.set_motor_model(2500, 2500, -1500, -1500)  # Turn right
        elif infrared_value == 3:  # Left and middle sensors detect line
            self.motor.set_motor_model(4000, 4000, -2000, -2000)  # Turn right sharper
        elif infrared_value == 7:  # All sensors detect line
            self.motor.set_motor_model(0, 0, 0, 0)  # Stop
    
    async def obstacle_avoidance_mode(self):
        """Obstacle avoidance mode implementation"""
        # Move servo to different positions and measure distances
        distances = [0, 0, 0]  # Left, center, right
        
        # Measure left distance
        self.servo.set_servo_pwm('0', 30)
        await asyncio.sleep(0.2)
        distances[0] = self.ultrasonic.get_distance()
        
        # Measure center distance
        self.servo.set_servo_pwm('0', 90)
        await asyncio.sleep(0.2)
        distances[1] = self.ultrasonic.get_distance()
        
        # Measure right distance
        self.servo.set_servo_pwm('0', 150)
        await asyncio.sleep(0.2)
        distances[2] = self.ultrasonic.get_distance()
        
        # Logic for obstacle avoidance
        if (distances[0] < 30 and distances[1] < 30 and distances[2] < 30) or distances[1] < 30:
            # Obstacles all around or directly ahead - back up and turn
            self.motor.set_motor_model(-1450, -1450, -1450, -1450)
            await asyncio.sleep(0.1)
            
            # Turn in direction with more space
            if distances[0] < distances[2]:
                self.motor.set_motor_model(1450, 1450, -1450, -1450)  # Turn right
            else:
                self.motor.set_motor_model(-1450, -1450, 1450, 1450)  # Turn left
        elif distances[0] < 30 and distances[1] < 30:
            # Obstacles on left and center - turn right
            self.motor.set_motor_model(1500, 1500, -1500, -1500)
        elif distances[2] < 30 and distances[1] < 30:
            # Obstacles on right and center - turn left
            self.motor.set_motor_model(-1500, -1500, 1500, 1500)
        elif distances[0] < 20:
            # Obstacle on left - turn right slightly
            self.motor.set_motor_model(2000, 2000, -500, -500)
            if distances[0] < 10:
                # Very close to left obstacle - turn right more
                self.motor.set_motor_model(1500, 1500, -1000, -1000)
        elif distances[2] < 20:
            # Obstacle on right - turn left slightly
            self.motor.set_motor_model(-500, -500, 2000, 2000)
            if distances[2] < 10:
                # Very close to right obstacle - turn left more
                self.motor.set_motor_model(-1500, -1500, 1500, 1500)
        else:
            # No obstacles - move forward
            self.motor.set_motor_model(600, 600, 600, 600)
    
    async def telemetry_task(self):
        """Background task to send telemetry data to clients"""
        while self.running:
            try:
                # Collect sensor data
                telemetry = {
                    "battery": self.adc.read_adc(2) * (3 if self.adc.pcb_version == 1 else 2),
                    "light_left": self.adc.read_adc(0),
                    "light_right": self.adc.read_adc(1),
                    "ultrasonic": self.ultrasonic.get_distance(),
                    "infrared": self.infrared.read_all_infrared(),
                    "mode": self.current_mode,
                    "timestamp": time.time()
                }
                
                # Send telemetry to all clients
                if self.active_clients:
                    telemetry_json = json.dumps(telemetry)
                    await asyncio.gather(
                        *[client.send(telemetry_json) for client in self.active_clients]
                    )
                
                # Check battery level for safety
                if telemetry["battery"] < 7.0:
                    # Battery low, beep warning
                    if not self.buzzer.state:
                        await self.buzzer.set_state(True)
                        await asyncio.sleep(0.1)
                        await self.buzzer.set_state(False)
                
                # Wait for next telemetry update
                await asyncio.sleep(self.telemetry_interval)
            
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
        """Clean up hardware resources"""
        logger.info("Cleaning up resources...")
        
        # Stop all motors
        if hasattr(self, 'motor'):
            self.motor.set_motor_model(0, 0, 0, 0)
        
        # Center servos
        if hasattr(self, 'servo'):
            self.servo.set_servo_pwm('0', 90)
            self.servo.set_servo_pwm('1', 90)
        
        # Turn off LEDs
        if hasattr(self, 'led'):
            try:
                self.led.colorWipe(self.led.strip, color(0, 0, 0))
            except:
                pass
        
        # Turn off buzzer
        if hasattr(self, 'buzzer'):
            self.buzzer.set_state(False)
        
        # Set flag to stop background tasks
        self.running = False
        
        logger.info("Cleanup complete")

def signal_handler(sig, frame):
    """Handle Ctrl+C to properly shut down the server"""
    logger.info("Interrupt received, shutting down...")
    # The actual cleanup will be done by the server
    sys.exit(0)

def color(r, g, b, w=0):
    """Create a color value for LED control"""
    return (w << 24) | (r << 16) | (g << 8) | b

def main():
    """Main entry point"""
    # Register signal handler for graceful shutdown
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
        # This will be called when asyncio.run() completes
        logger.info("Server shutdown complete")

if __name__ == "__main__":
    main()
