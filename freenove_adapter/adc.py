import smbus
import time
import platform
import os

def is_raspberry_pi():
    """Check if running on a Raspberry Pi"""
    return platform.machine().startswith('arm') or os.path.exists('/sys/class/gpio')
class ADC:
    def __init__(self):
        # Detectar versão da placa de conexão
        self.pcb_version = self._detect_pcb_version()
        
        # Configurar I2C
        self.bus = smbus.SMBus(1)
        self.address = 0x48  # Endereço do PCF8591
    
    def _detect_pcb_version(self):
        """Detector de versão da placa de conexão"""
        try:
            with open('/proc/device-tree/model', 'r') as f:
                model = f.read()
            if 'Raspberry Pi 5' in model:
                return 2  # Placa V2.0 para Raspberry Pi 5
            return 1  # Placa V1.0 para outros modelos
        except:
            return 1  # Fallback para V1.0
    
    def read_adc(self, channel):
        """Ler valor do canal ADC (0-2)
        0: Fotoresistor esquerdo
        1: Fotoresistor direito
        2: Tensão da bateria
        """
        if channel < 0 or channel > 3:
            return -1
            
        try:
            self.bus.write_byte(self.address, 0x40 | channel)
            self.bus.read_byte(self.address)  # Leitura dummy
            value = self.bus.read_byte(self.address)
            
            # Converter para voltagem
            voltage = value / 255.0 * 3.3
            return voltage
        except Exception as e:
            print(f"Erro ao ler ADC: {e}")
            return 0.0