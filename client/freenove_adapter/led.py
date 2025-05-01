import time
from rpi_ws281x import Color, PixelStrip

class Led:
    def __init__(self):
        # Detectar versão da placa de conexão
        self.pcb_version = self._detect_pcb_version()
        
        # Configuração dos LEDs WS2812
        LED_COUNT = 8        # Número de LEDs
        LED_PIN = 18 if self.pcb_version == 1 else 10  # GPIO para o SPI MOSI
        LED_FREQ_HZ = 800000 # Frequência do sinal
        LED_DMA = 10         # Canal DMA 
        LED_BRIGHTNESS = 255 # Brilho (0-255)
        LED_INVERT = False   # Sinal invertido
        LED_CHANNEL = 0      # Canal PWM (0 ou 1)
        
        # Ordenação dos LEDs
        self.ORDER = "GRB"   # Ordem das cores (GRB ou RGB)
        
        # Inicializar tira de LEDs
        self.strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
        self.strip.begin()
    
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
    
    def ledIndex(self, index, R, G, B):
        """Controlar LEDs individualmente por índice
        index: 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80 (binário)
        R, G, B: Valores RGB (0-255)
        """
        # Mapeamento binário para índice
        # 0x01 = LED 0, 0x02 = LED 1, etc.
        
        for i in range(8):
            if index & (1 << i):
                if self.ORDER == "GRB":
                    color = Color(G, R, B)
                else:
                    color = Color(R, G, B)
                self.strip.setPixelColor(i, color)
        
        self.strip.show()
    
    def colorWipe(self, color, wait_ms=50):
        """Preencher todos os LEDs com uma cor"""
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, color)
            self.strip.show()
            time.sleep(wait_ms / 1000.0)
    
    def colorBlink(self, state, wait_ms=300):
        """Piscar LEDs em modo arco-íris"""
        if state == 0:
            # Desligar todos os LEDs
            for i in range(self.strip.numPixels()):
                self.strip.setPixelColor(i, Color(0, 0, 0))
            self.strip.show()
        else:
            # Efeito arco-íris
            for j in range(256):
                for i in range(self.strip.numPixels()):
                    self.strip.setPixelColor(i, self.wheel((i + j) & 255))
                self.strip.show()
                time.sleep(wait_ms / 1000.0)
    
    def wheel(self, pos):
        """Gerar cor para efeito arco-íris"""
        if pos < 85:
            if self.ORDER == "GRB":
                return Color(pos * 3, 255 - pos * 3, 0)
            else:
                return Color(255 - pos * 3, pos * 3, 0)
        elif pos < 170:
            pos -= 85
            if self.ORDER == "GRB":
                return Color(255 - pos * 3, 0, pos * 3)
            else:
                return Color(0, 255 - pos * 3, pos * 3)
        else:
            pos -= 170
            if self.ORDER == "GRB":
                return Color(0, pos * 3, 255 - pos * 3)
            else:
                return Color(pos * 3, 0, 255 - pos * 3)