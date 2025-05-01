import paho.mqtt.client as mqtt
import json
import logging
import time
import threading

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("mqtt_client")

class MQTTClient:
    """Cliente MQTT para o Raspberry Pi"""
    
    def __init__(self, broker_host, broker_port=1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client = mqtt.Client()
        self.connected = False
        
        # Configurar callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        # Handlers para comandos recebidos
        self.command_handlers = {
            "move": self.handle_move_command,
            "camera": self.handle_camera_command,
            "mode": self.handle_mode_command,
            "led": self.handle_led_command,
            "buzzer": self.handle_buzzer_command
        }
        
        # Status do sistema
        self.system_status = {
            "mode": "manual",
            "camera_active": False,
            "sensors": {}
        }
        
        # Thread de reconexão
        self.reconnect_thread = None
        self.reconnect_flag = False
        
        logger.info(f"Cliente MQTT inicializado, broker: {broker_host}:{broker_port}")
    
    def start(self):
        """Iniciar cliente MQTT"""
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # Iniciar thread de sensores
            sensor_thread = threading.Thread(target=self.sensor_loop)
            sensor_thread.daemon = True
            sensor_thread.start()
            
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar MQTT: {e}")
            self.start_reconnect_thread()
            return False
    
    def stop(self):
        """Parar cliente MQTT"""
        self.client.loop_stop()
        self.client.disconnect()
        self.reconnect_flag = False
        logger.info("Cliente MQTT desconectado")
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback quando conecta ao broker"""
        if rc == 0:
            logger.info("Conectado ao broker MQTT")
            self.connected = True
            
            # Inscrever nos tópicos de comando
            self.client.subscribe("iacar/command/#")
            
            # Publicar status de conexão
            self.publish_status({"connected": True})
        else:
            logger.error(f"Falha na conexão MQTT, código: {rc}")
            self.connected = False
            self.start_reconnect_thread()
    
    def on_disconnect(self, client, userdata, rc):
        """Callback quando desconecta do broker"""
        logger.warning(f"Desconectado do broker MQTT, código: {rc}")
        self.connected = False
        
        if rc != 0:
            self.start_reconnect_thread()
    
    def on_message(self, client, userdata, msg):
        """Callback quando recebe mensagem"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            logger.debug(f"Mensagem recebida no tópico {topic}: {payload}")
            
            # Extrair tipo de comando do tópico
            if topic.startswith("iacar/command/"):
                command_type = topic.split("/")[-1]
                self._process_command(command_type, payload)
        except json.JSONDecodeError:
            logger.error(f"Payload inválido no tópico {topic}")
        except Exception as e:
            logger.error(f"Erro ao processar mensagem MQTT: {e}")
    
    def _process_command(self, command_type, data):
        """Processar comandos recebidos"""
        if command_type in self.command_handlers:
            self.command_handlers[command_type](data)
        else:
            logger.warning(f"Comando desconhecido: {command_type}")
    
    def handle_move_command(self, data):
        """Processar comando de movimento"""
        direction = data.get("dir", "stop")
        speed = data.get("speed", 0)
        logger.info(f"Executando movimento: {direction}, velocidade: {speed}")
        
        # Aqui implementaria o controle dos motores
        # Por exemplo, chamando a classe Motor:
        # from motor import Motor
        # motor = Motor()
        # motor.move(direction, speed)
    
    def handle_camera_command(self, data):
        """Processar comando de câmera"""
        servo = data.get("servo")
        angle = data.get("angle")
        logger.info(f"Movendo câmera: servo {servo}, ângulo {angle}")
        
        # Aqui implementaria o controle do servo da câmera
        # Por exemplo, chamando a classe Servo:
        # from servo import Servo
        # servo_controller = Servo()
        # servo_controller.set_angle(servo, angle)
        
        # Atualizar status da câmera
        self.system_status["camera_active"] = True
        self.publish_status({"camera_active": True})
    
    def handle_mode_command(self, data):
        """Processar comando de modo"""
        mode = data.get("mode", "manual")
        logger.info(f"Alterando modo para: {mode}")
        
        # Atualizar modo do sistema
        self.system_status["mode"] = mode
        self.publish_status({"mode": mode})
    
    def handle_led_command(self, data):
        """Processar comando de LED"""
        led_id = data.get("id")
        color = data.get("color")
        logger.info(f"Controlando LED {led_id}: {color}")
        
        # Aqui implementaria o controle dos LEDs
        # Por exemplo, chamando a classe Led:
        # from led import Led
        # led_controller = Led()
        # led_controller.set_color(led_id, color)
    
    def handle_buzzer_command(self, data):
        """Processar comando de buzzer"""
        state = data.get("state", False)
        logger.info(f"Buzzer: {'ligado' if state else 'desligado'}")
        
        # Aqui implementaria o controle do buzzer
        # Por exemplo, chamando a classe Buzzer:
        # from buzzer import Buzzer
        # buzzer = Buzzer()
        # buzzer.set_state(state)
    
    def publish_sensor_data(self, sensor_type, data):
        """Publicar dados de sensores"""
        if not self.connected:
            return False
        
        topic = f"iacar/sensor/{sensor_type}"
        try:
            self.client.publish(topic, json.dumps(data), qos=1)
            return True
        except Exception as e:
            logger.error(f"Erro ao publicar dados do sensor: {e}")
            return False
    
    def publish_status(self, status_data):
        """Publicar atualizações de status"""
        if not self.connected:
            return False
        
        try:
            self.client.publish("iacar/status", json.dumps(status_data), qos=1)
            return True
        except Exception as e:
            logger.error(f"Erro ao publicar status: {e}")
            return False
    
    def sensor_loop(self):
        """Loop de leitura e publicação de sensores"""
        while self.connected or self.reconnect_flag:
            if self.connected:
                try:
                    # Aqui implementaria a leitura dos sensores
                    # Por exemplo, para o sensor ultrassônico:
                    # from ultrasonic import Ultrasonic
                    # ultrasonic = Ultrasonic()
                    # distance = ultrasonic.get_distance()
                    
                    # Simular leituras para este exemplo
                    ultrasonic_data = {"value": 50}  # cm
                    light_data = {"left": 2.5, "right": 2.3}  # volts
                    battery_data = {"level": 7.8}  # volts
                    
                    # Publicar dados dos sensores
                    self.publish_sensor_data("ultrasonic", ultrasonic_data)
                    self.publish_sensor_data("light", light_data)
                    self.publish_sensor_data("battery", battery_data)
                    
                    # Atualizar cache local
                    self.system_status["sensors"]["ultrasonic"] = ultrasonic_data["value"]
                    self.system_status["sensors"]["light_left"] = light_data["left"]
                    self.system_status["sensors"]["light_right"] = light_data["right"]
                except Exception as e:
                    logger.error(f"Erro no loop de sensores: {e}")
            
            time.sleep(0.5)  # Publicar a cada 500ms
    
    def start_reconnect_thread(self):
        """Iniciar thread de reconexão"""
        if self.reconnect_thread is None or not self.reconnect_thread.is_alive():
            self.reconnect_flag = True
            self.reconnect_thread = threading.Thread(target=self.reconnect_loop)
            self.reconnect_thread.daemon = True
            self.reconnect_thread.start()
    
    def reconnect_loop(self):
        """Loop de reconexão"""
        retry_interval = 5  # segundos
        while self.reconnect_flag and not self.connected:
            try:
                logger.info(f"Tentando reconectar ao broker MQTT...")
                self.client.connect(self.broker_host, self.broker_port, 60)
                logger.info("Reconectado com sucesso")
                break
            except Exception as e:
                logger.error(f"Falha na reconexão: {e}")
            
            time.sleep(retry_interval)