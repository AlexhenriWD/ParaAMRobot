import RPi.GPIO as GPIO
import time
import platform
import os

def is_raspberry_pi():
    """Check if running on a Raspberry Pi"""
    return platform.machine().startswith('arm') or os.path.exists('/sys/class/gpio')

class Ultrasonic:
    def __init__(self, trig=23, echo=24, max_distance=300):
        self.trig = trig
        self.echo = echo
        self.max_distance = max_distance
        
        # Configurar GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.trig, GPIO.OUT)
        GPIO.setup(self.echo, GPIO.IN)
    
    def get_distance(self):
        # Garantir que o trigger está baixo
        GPIO.output(self.trig, False)
        time.sleep(0.01)
        
        # Enviar pulso de 10µs
        GPIO.output(self.trig, True)
        time.sleep(0.00001)
        GPIO.output(self.trig, False)
        
        # Medir tempo de resposta
        pulse_start = time.time()
        timeout = pulse_start + 0.05  # Timeout de 50ms
        
        # Esperar pelo início do pulso
        while GPIO.input(self.echo) == 0:
            pulse_start = time.time()
            if pulse_start > timeout:
                return None
                
        pulse_end = time.time()
        timeout = pulse_end + 0.05  # Timeout para esperar pelo fim do pulso
        
        # Esperar pelo fim do pulso
        while GPIO.input(self.echo) == 1:
            pulse_end = time.time()
            if pulse_end > timeout:
                return None
                
        # Calcular distância
        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150  # Velocidade do som * tempo / 2
        distance = round(distance, 2)
        
        if distance > self.max_distance:
            return self.max_distance
        
        return distance
    
    def close(self):
        pass  # Não precisa limpar aqui, será feito pelo motor