#!/usr/bin/env python3
import argparse
import time
import signal
import sys
from mqtt_client import MQTTClient

# Tratamento de interrupção para encerramento limpo
def signal_handler(sig, frame):
    print("Encerrando cliente MQTT...")
    if client:
        client.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cliente MQTT para Raspberry Pi")
    parser.add_argument("--broker", help="Endereço do broker MQTT", default="localhost")
    parser.add_argument("--port", help="Porta do broker MQTT", type=int, default=1883)
    args = parser.parse_args()
    
    # Iniciar cliente MQTT
    client = MQTTClient(args.broker, args.port)
    connected = client.start()
    
    if connected:
        print(f"Cliente MQTT conectado ao broker {args.broker}:{args.port}")
        
        # Manter programa em execução
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            client.stop()
    else:
        print("Falha ao conectar ao broker MQTT. Verifique se o broker está em execução.")
        sys.exit(1)