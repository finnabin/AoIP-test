import socket
import threading
import json
import time

# Receiver class to handle incoming connections from AudioIns 

class Receiver:
    def __init__(self, listen_port=5004):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("0.0.0.0", listen_port))
        self.connections = {} # dictionary to connections between transmitters and receivers
        self.running = False

    def start(self):
        self.running = True
        listen_thread = threading.Thread(target=self.listen)
        listen_thread.start()

    def listen(self):
        print("Receiver scanning for connections...")
        while self.running:
            try:
                data, addr = self.socket.recvfrom(1024)  # buffer size is 1024 bytes
                message = json.loads(data.decode()) 

                if message["type"] == "connect":
                    self.handle_connect(message, addr)
                elif message["type"] == "disconnect":
                    self.handle_disconnect(message, addr)
                elif message["type"] == "ping":
                    self.handle_ping(addr)

            except Exception as e:
                print(f"Error receiving data: {e}")

    def handle_connect(self, message, addr):
        transmitter_id = message["transmitter_id"]
        self.connections[transmitter_id] = {
            "ip": addr[0],
            "port": addr[1],
            "Connected_at": time.time()
        }
        response = {"type": "connect_ack", "status": "connected"}
        self.socket.sendto(json.dumps(response).encode(), addr)
        print(f"Transmitter {transmitter_id} connected to {addr}")

    def handle_disconnect(self, message, addr):
        transmitter_id = message["transmitter_id"]
        if transmitter_id in self.connections:
            del self.connections[transmitter_id]
            response = {"type: disconnect_ack", "status: disconnected"}
            self.socket.sendto(json.dumps(response).encode(), addr)
            print(f"Disconnected transmitter {transmitter_id}")

    def handle_ping(self, addr):
        response = {"type": "pong"}
        self.socket.sendto(json.dumps(response).encode(), addr)
        print(f"Ping received from {addr}, pong sent back")

    def stop(self):
        self.running = False
        self.socket.close()


