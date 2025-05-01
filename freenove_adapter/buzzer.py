import RPi.GPIO as GPIO
import platform
import os

def is_raspberry_pi():
    """Check if running on a Raspberry Pi"""
    return platform.machine().startswith('arm') or os.path.exists('/sys/class/gpio')
class Buzzer:
    def __init__(self, pin=17):
        self.pin = pin
        
        # Configurar GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.LOW)
        
        self.state = False
    
    def set_state(self, state):
        """Definir estado do buzzer (True/False)"""
        self.state = state
        GPIO.output(self.pin, GPIO.HIGH if state else GPIO.LOW)
    
    def close(self):
        """Desligar o buzzer"""
        self.set_state(False)