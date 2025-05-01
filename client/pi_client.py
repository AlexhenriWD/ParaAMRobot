#!/usr/bin/env python3
import asyncio
import websockets
import json
import logging
import time
import threading
from queue import Queue
import sys
import os

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler("pi_client.log")]
)
logger = logging.getLogger("pi_client")

# Importar adaptadores Freenove
from freenove_adapter.motor import Ordinary_Car
from freenove_adapter.ultrasonic import Ultrasonic
from freenove_adapter.servo import Servo
from freenove_adapter.adc import ADC
from freenove_adapter.led import Led
from freenove_adapter.buzzer import Buzzer

class PiClient:
    def __init__(self, server_url):
        self.server_url = server_url
        self.connected = False
        self.websocket = None
        self.command_queue = Queue()
        self.stop_event = threading.Event()
        
        # Inicializar hardware
        try:
            self.motor = Ordinary_Car()
            self.ultrasonic = Ultrasonic()
            self.servo = Servo()
            self.adc = ADC()
            self.led = Led()
            self.buzzer = Buzzer()
            
            # Reset inicial
            self.motor.set_motor_model(0, 0, 0, 0)
            self.servo.set_servo_pwm('0', 90)
            self.servo.set_servo_pwm('1', 90)
            self.led.colorBlink(0)
            self.buzzer.set_state(False)
            
            logger.info("Hardware inicializado")
        except Exception as e:
            logger.error(f"Erro ao inicializar hardware: {e}")
            raise
    
    async def connect(self):
        while not self.stop_event.is_set():
            try:
                self.websocket = await websockets.connect(self.server_url)
                self.connected = True
                logger.info(f"Conectado ao servidor: {self.server_url}")
                
                await asyncio.gather(
                    self.process_commands(),
                    self.send_telemetry()
                )
            except Exception as e:
                self.connected = False
                logger.error(f"Erro de conexão: {e}")
                logger.info(f"Tentando reconectar em 5 segundos...")
                await asyncio.sleep(5)
    
    async def process_commands(self):
        try:
            while self.connected and not self.stop_event.is_set():
                message = await self.websocket.recv()
                try:
                    command = json.loads(message)
                    logger.info(f"Comando recebido: {command}")
                    self.command_queue.put(command)
                except json.JSONDecodeError:
                    logger.error(f"Comando inválido: {message}")
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            logger.info("Conexão fechada")
    
    async def send_telemetry(self):
        try:
            while self.connected and not self.stop_event.is_set():
                telemetry = self.get_telemetry()
                await self.websocket.send(json.dumps(telemetry))
                await asyncio.sleep(0.5)
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
    
    def get_telemetry(self):
        telemetry = {}
        try:
            # Leitura dos sensores
            distance = self.ultrasonic.get_distance()
            if distance is not None:
                telemetry["sensor"] = "ultrasonic"
                telemetry["value"] = distance
                
            # Leitura da bateria
            battery = self.adc.read_adc(2) * (3 if self.adc.pcb_version == 1 else 2)
            telemetry["battery"] = battery
            
            # Leitura dos fotoresistores
            left_light = self.adc.read_adc(0)
            right_light = self.adc.read_adc(1)
            telemetry["light"] = {"left": left_light, "right": right_light}
            
        except Exception as e:
            logger.error(f"Erro ao obter telemetria: {e}")
        
        return telemetry
    
    def process_command_queue(self):
        while not self.stop_event.is_set():
            try:
                if not self.command_queue.empty():
                    command = self.command_queue.get()
                    self.execute_command(command)
                    self.command_queue.task_done()
                else:
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"Erro ao processar comando: {e}")
    
    def execute_command(self, command):
        try:
            action = command.get("action", "")
            
            if action == "move":
                # Comando de movimento
                direction = command.get("dir", "")
                speed = command.get("speed", 50)
                motor_speed = int(speed * 40.96)  # Converter para escala do motor
                
                if direction == "forward":
                    self.motor.set_motor_model(motor_speed, motor_speed, motor_speed, motor_speed)
                elif direction == "backward":
                    self.motor.set_motor_model(-motor_speed, -motor_speed, -motor_speed, -motor_speed)
                elif direction == "left":
                    self.motor.set_motor_model(-motor_speed, -motor_speed, motor_speed, motor_speed)
                elif direction == "right":
                    self.motor.set_motor_model(motor_speed, motor_speed, -motor_speed, -motor_speed)
                elif direction == "stop":
                    self.motor.set_motor_model(0, 0, 0, 0)
                elif direction == "move_left":
                    self.motor.set_motor_model(-motor_speed, motor_speed, motor_speed, -motor_speed)
                elif direction == "move_right":
                    self.motor.set_motor_model(motor_speed, -motor_speed, -motor_speed, motor_speed)
                
            elif action == "camera":
                # Comando de câmera
                servo_id = command.get("servo", "0")
                angle = command.get("angle", 90)
                self.servo.set_servo_pwm(servo_id, angle)
                
            elif action == "led":
                # Comando de LED
                led_id = command.get("id", 0)
                r = command.get("r", 0)
                g = command.get("g", 0)
                b = command.get("b", 0)
                
                if led_id == "all":
                    for i in range(8):
                        self.led.ledIndex(1 << i, r, g, b)
                else:
                    led_id = int(led_id)
                    self.led.ledIndex(1 << led_id, r, g, b)
                    
            elif action == "buzzer":
                # Comando do buzzer
                state = command.get("state", False)
                self.buzzer.set_state(state)
                
            elif action == "mode":
                # Alternar modo
                mode = command.get("mode", "manual")
                logger.info(f"Alterando para modo: {mode}")
                
        except Exception as e:
            logger.error(f"Erro ao executar comando: {e}")
    
    def start(self):
        # Thread para processamento de comandos
        command_thread = threading.Thread(target=self.process_command_queue)
        command_thread.daemon = True
        command_thread.start()
        
        # Loop de eventos assíncrono
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self.connect())
        except KeyboardInterrupt:
            logger.info("Encerrando cliente...")
        finally:
            self.stop()
            loop.close()
    
    def stop(self):
        self.stop_event.set()
        try:
            self.motor.set_motor_model(0, 0, 0, 0)
            self.led.colorBlink(0)
            self.buzzer.set_state(False)
            self.motor.close()
        except:
            pass
        logger.info("Cliente finalizado")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cliente Raspberry Pi")
    parser.add_argument("--host", default="192.168.1.100", help="IP do servidor")
    parser.add_argument("--port", type=int, default=8000, help="Porta do servidor")
    args = parser.parse_args()
    
    server_url = f"ws://{args.host}:{args.port}/ws/pi"
    client = PiClient(server_url)
    
    try:
        client.start()
    except KeyboardInterrupt:
        client.stop()