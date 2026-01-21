#!/usr/bin/env python3
"""HTTP Echo Server for testing."""

from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import json

class EchoHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        print(f'[{datetime.now()}] Received POST {self.path}', flush=True)
        print(f'[{datetime.now()}] Headers: {dict(self.headers)}', flush=True)
        print(f'[{datetime.now()}] Body ({len(body)} bytes): {body[:200]}...', flush=True)
        
        response = {
            'status': 'received',
            'timestamp': datetime.now().isoformat(),
            'path': self.path,
            'content_length': content_length,
        }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok', 'service': 'http-echo'}).encode())

if __name__ == '__main__':
    print('HTTP Echo Server listening on port 8082', flush=True)
    HTTPServer(('0.0.0.0', 8082), EchoHandler).serve_forever()
