#!/usr/bin/env python3
"""MLLP Echo Server for testing."""

import socket
from datetime import datetime

VT = b'\x0b'
FS = b'\x1c'
CR = b'\x0d'

def create_ack(msg):
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    return VT + f'MSH|^~\\&|ECHO|HIE|TEST|TEST|{ts}||ACK|1|P|2.5\rMSA|AA|1|Message Accepted\r'.encode() + FS + CR

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('0.0.0.0', 2575))
server.listen(5)
print('MLLP Echo Server listening on port 2575', flush=True)

while True:
    conn, addr = server.accept()
    print(f'[{datetime.now()}] Connection from {addr}', flush=True)
    try:
        data = b''
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
            if FS in data:
                break
        if data:
            print(f'[{datetime.now()}] Received {len(data)} bytes', flush=True)
            conn.sendall(create_ack(data))
            print(f'[{datetime.now()}] Sent ACK', flush=True)
    except Exception as e:
        print(f'[{datetime.now()}] Error: {e}', flush=True)
    finally:
        conn.close()
