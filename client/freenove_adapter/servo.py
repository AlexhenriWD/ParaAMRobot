import time
import math
import platform
import os

def is_raspberry_pi():
    """Check if running on a Raspberry Pi"""
    return platform.machine().startswith('arm') or os.path.exists('/sys/class/gpio')
class Servo:
    def __init__(self):
        import Adafruit_PCA9685
        self.pwm = Adafruit_PCA9685.PCA9685()
        self.pwm.set_pwm_freq(50)  # Frequência para servos
        
        # Canais dos servos
        self.servo_horizontal = 2  # Servo 0 (horizontal)
        self.servo_vertical = 3    # Servo 1 (vertical)
    
    def map(self, value, in_min, in_max, out_min, out_max):
        """Mapear valor de um intervalo para outro"""
        return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    
    def set_servo_pulse(self, channel, pulse):
        """Definir pulso do servo em microssegundos"""
        pulse_length = 1000000    # 1,000,000 µs por segundo
        pulse_length //= 50       # 50 Hz
        pulse_length //= 4096     # 12 bits de resolução
        pulse *= 1000             # Converter para µs
        pulse //= pulse_length
        self.pwm.set_pwm(channel, 0, pulse)
    
    def set_servo_pwm(self, servo_id, angle):
        """Definir ângulo do servo (0-180)"""
        # Limitar ângulo
        angle = max(0, min(180, angle))
        
        # Mapear ângulo para pulso
        pulse = self.map(angle, 0, 180, 500, 2500)
        
        # Direcionar para o servo correto
        if servo_id == '0':
            self.pwm.set_pwm(self.servo_horizontal, 0, int(pulse / (1000000 / 50 / 4096)))
        elif servo_id == '1':
            self.pwm.set_pwm(self.servo_vertical, 0, int(pulse / (1000000 / 50 / 4096)))
    
    def close(self):
        # Centralizar servos
        self.set_servo_pwm('0', 90)
        self.set_servo_pwm('1', 90)