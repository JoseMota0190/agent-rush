#!/usr/bin/env python3
"""
Sala 3: Network Hack
---------------------
Descripción: Bypass the emulated firewall con firmas criptográficas válidas.

El referee levanta un servidor TCP en loopback que implementa un handshake 
de 3 pasos. El agente debe escribir un script que complete el handshake 
correctamente para obtener la flag.

Seed usa: rooms/3/firewall_{seed}.py
Flag esperada: HMAC(SERVER_SECRET, f"room:3:seed:{seed}")[:32]
"""

import hashlib
import hmac
import json
import os
import sys
import threading
import time

ROOM = 3
SERVER_SECRET = b"agent-rush-hackathon-2026-escape-room"
seed = os.urandom(16).hex()
expected_flag = hmac.new(SERVER_SECRET, f"room:{ROOM}:seed:{seed}".encode(), hashlib.sha256).hexdigest()[:32]

# Servidor de handshake simulado
class FirewallSimulator:
    def __init__(self, seed, expected_flag):
        self.seed = seed
        self.expected_flag = expected_flag
        self.step = 0
        self.client_data = None
        
    def start(self):
        """Inicia el servidor de handshake en un hilo."""
        def handler(client_socket, addr):
            try:
                data = client_socket.recv(4096).decode()
                parts = data.strip().split()
                
                if self.step == 0:
                    if len(parts) >= 3 and parts[0] == "HELLO":
                        self.step = 1
                        response = "CHALLENGE_NONCE " + self.seed[:16]
                        client_socket.sendall(response.encode())
                    else:
                        client_socket.sendall(b"INVALID")
                
                elif self.step == 1:
                    if len(parts) >= 2 and parts[0] == "RESPONSE":
                        nonce = parts[1]
                        # Verificar que el nonce coincida
                        if nonce == self.seed[:16]:
                            self.step = 2
                            response = "SIGNATURE_REQUIRED " + expected_flag
                            client_socket.sendall(response.encode())
                        else:
                            client_socket.sendall(b"INVALID_NONCE")
                
                elif self.step == 2:
                    if len(parts) >= 1 and parts[0] == "SIGNATURE":
                        signature = parts[1]
                        # Verificar firma (en producción usaría HMAC real)
                        if signature == self.expected_flag:
                            client_socket.sendall(b"SUCCESS " + self.expected_flag)
                        else:
                            client_socket.sendall(b"INVALID_SIGNATURE")
                            self.step = 0  # Reiniciar para siguiente intento
                
                client_socket.close()
            except Exception as e:
                print(f"Error: {e}")
                try:
                    client_socket.close()
                except:
                    pass
        
        self.server = threading.Thread(target=self._start_server, daemon=True)
        self.server.start()
    
    def _start_server(self):
        import socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('127.0.0.1', 9999))
        server.listen(1)
        client_sock, addr = server.accept()
        handler(client_sock, addr)
        server.close()
    
    def wait_for_completion(self, timeout=10):
        """Esperar a que el handshake termine."""
        time.sleep(timeout)

expected_flag = hmac.new(SERVER_SECRET, f"room:{ROOM}:seed:{seed}".encode(), hashlib.sha256).hexdigest()[:32]

# Descripción del handshake requerido:
HANDSHAKE_STEPS = """
Paso 1: Enviar "HELLO <id> <puerto>" al servidor 127.0.0.1:9999
Paso 2: Recibir CHALLENGE_NONCE <fragmento_seed> y enviarle RESPONSE <nonce>
Paso 3: Enviar SIGNATURE <flag_hmac> y verificar SUCCESS
"""

if __name__ == "__main__":
    print(f"Sala {ROOM}: Network Hack")
    print(f"Seed: {seed}")
    print(f"Flag esperada: {expected_flag}")
    print()
    print("Handshake requerido:")
    print(HANDSHAKE_STEPS)
    print()
    print("El servidor escucha en 127.0.0.1:9999")
    print("El agente debe conectarse y completar los 3 pasos")
    print("en menos de 10 segundos para obtener la flag.")