import time
import math
import platform
import os

def is_raspberry_pi():
    """Check if running on a Raspberry Pi"""
    return platform.machine().startswith('arm') or os.path.exists('/sys/class/gpio')

class Ordinary_Car:
    def __init__(self):
        self.simulation_mode = not is_raspberry_pi()
        self.pwm_frequency = 50
        self.min_value = 0
        self.max_value = 4095
        
        if self.simulation_mode:
            print("SIMULATION MODE: Motors initialized (simulated)")
            return
            
        # Pi-specific initialization - only runs on actual Pi
        try:
            import RPi.GPIO as GPIO
            import Adafruit_PCA9685
            
            # Configure pins
            self.pwm_A = 0
            self.pwm_B = 1
            self.pin_A = 27
            self.pin_B = 22
            
            self.pwm_C = 4
            self.pwm_D = 5
            self.pin_C = 0
            self.pin_D = 5
            
            self.pwm_E = 10
            self.pwm_F = 11
            self.pin_E = 24
            self.pin_F = 25
            
            self.pwm_G = 12
            self.pwm_H = 13
            self.pin_G = 4
            self.pin_H = 6
            
            # Initialize GPIO
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin_A, GPIO.OUT)
            GPIO.setup(self.pin_B, GPIO.OUT)
            GPIO.setup(self.pin_C, GPIO.OUT)
            GPIO.setup(self.pin_D, GPIO.OUT)
            GPIO.setup(self.pin_E, GPIO.OUT)
            GPIO.setup(self.pin_F, GPIO.OUT)
            GPIO.setup(self.pin_G, GPIO.OUT)
            GPIO.setup(self.pin_H, GPIO.OUT)
            
            # Initialize PCA9685
            self.pwm = Adafruit_PCA9685.PCA9685(address=0x40)
            self.pwm.set_pwm_freq(self.pwm_frequency)
        except Exception as e:
            print(f"Hardware initialization error: {e}")
            self.simulation_mode = True
            print("Falling back to SIMULATION MODE")
    
    def duty_range(self, duty1, duty2, duty3, duty4):
        # Limit values to allowed range
        if duty1 > 0: duty1 = min(duty1, self.max_value)
        elif duty1 < 0: duty1 = max(duty1, -self.max_value)
            
        if duty2 > 0: duty2 = min(duty2, self.max_value)
        elif duty2 < 0: duty2 = max(duty2, -self.max_value)
            
        if duty3 > 0: duty3 = min(duty3, self.max_value)
        elif duty3 < 0: duty3 = max(duty3, -self.max_value)
            
        if duty4 > 0: duty4 = min(duty4, self.max_value)
        elif duty4 < 0: duty4 = max(duty4, -self.max_value)
            
        return duty1, duty2, duty3, duty4
    
    def left_upper_wheel(self, duty):
        if self.simulation_mode:
            print(f"SIM: Left upper wheel set to {duty}")
            return
            
        import RPi.GPIO as GPIO
        if duty > 0:
            GPIO.output(self.pin_A, GPIO.HIGH)
            GPIO.output(self.pin_B, GPIO.LOW)
            self.pwm.set_pwm(self.pwm_A, 0, duty)
        elif duty < 0:
            GPIO.output(self.pin_A, GPIO.LOW)
            GPIO.output(self.pin_B, GPIO.HIGH)
            self.pwm.set_pwm(self.pwm_B, 0, -duty)
        else:
            GPIO.output(self.pin_A, GPIO.LOW)
            GPIO.output(self.pin_B, GPIO.LOW)
            self.pwm.set_pwm(self.pwm_A, 0, 0)
            self.pwm.set_pwm(self.pwm_B, 0, 0)
    
    def left_lower_wheel(self, duty):
        if self.simulation_mode:
            print(f"SIM: Left lower wheel set to {duty}")
            return
            
        import RPi.GPIO as GPIO
        if duty > 0:
            GPIO.output(self.pin_C, GPIO.HIGH)
            GPIO.output(self.pin_D, GPIO.LOW)
            self.pwm.set_pwm(self.pwm_C, 0, duty)
        elif duty < 0:
            GPIO.output(self.pin_C, GPIO.LOW)
            GPIO.output(self.pin_D, GPIO.HIGH)
            self.pwm.set_pwm(self.pwm_D, 0, -duty)
        else:
            GPIO.output(self.pin_C, GPIO.LOW)
            GPIO.output(self.pin_D, GPIO.LOW)
            self.pwm.set_pwm(self.pwm_C, 0, 0)
            self.pwm.set_pwm(self.pwm_D, 0, 0)
    
    def right_upper_wheel(self, duty):
        if self.simulation_mode:
            print(f"SIM: Right upper wheel set to {duty}")
            return
            
        import RPi.GPIO as GPIO
        if duty > 0:
            GPIO.output(self.pin_E, GPIO.HIGH)
            GPIO.output(self.pin_F, GPIO.LOW)
            self.pwm.set_pwm(self.pwm_E, 0, duty)
        elif duty < 0:
            GPIO.output(self.pin_E, GPIO.LOW)
            GPIO.output(self.pin_F, GPIO.HIGH)
            self.pwm.set_pwm(self.pwm_F, 0, -duty)
        else:
            GPIO.output(self.pin_E, GPIO.LOW)
            GPIO.output(self.pin_F, GPIO.LOW)
            self.pwm.set_pwm(self.pwm_E, 0, 0)
            self.pwm.set_pwm(self.pwm_F, 0, 0)
    
    def right_lower_wheel(self, duty):
        if self.simulation_mode:
            print(f"SIM: Right lower wheel set to {duty}")
            return
            
        import RPi.GPIO as GPIO
        if duty > 0:
            GPIO.output(self.pin_G, GPIO.HIGH)
            GPIO.output(self.pin_H, GPIO.LOW)
            self.pwm.set_pwm(self.pwm_G, 0, duty)
        elif duty < 0:
            GPIO.output(self.pin_G, GPIO.LOW)
            GPIO.output(self.pin_H, GPIO.HIGH)
            self.pwm.set_pwm(self.pwm_H, 0, -duty)
        else:
            GPIO.output(self.pin_G, GPIO.LOW)
            GPIO.output(self.pin_H, GPIO.LOW)
            self.pwm.set_pwm(self.pwm_G, 0, 0)
            self.pwm.set_pwm(self.pwm_H, 0, 0)
    
    def set_motor_model(self, duty1, duty2, duty3, duty4):
        duty1, duty2, duty3, duty4 = self.duty_range(duty1, duty2, duty3, duty4)
        
        if self.simulation_mode:
            print(f"SIM: Motor set to [{duty1}, {duty2}, {duty3}, {duty4}]")
            return
            
        self.left_upper_wheel(duty1)
        self.left_lower_wheel(duty2)
        self.right_upper_wheel(duty3)
        self.right_lower_wheel(duty4)
    
    def close(self):
        self.set_motor_model(0, 0, 0, 0)
        
        if not self.simulation_mode:
            import RPi.GPIO as GPIO
            GPIO.cleanup()