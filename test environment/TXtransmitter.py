import socket
import threading
import json
import time

# Transmitter class to manage connections to AudioOuts

class Transmitter:
    def __init__ (self, transmitter_id, receiver_ip, receiver_port=5004):
        self.transmitter_id = transmitter_id
        self.receiver_ip = receiver_ip
        self.receiver_port = receiver_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(5)  # 5 second timeout for socket operations
        self.connected = False

    def connect(self):
        message = {"type": "connect", "transmitter_id": self.transmitter_id}
        
        try:
            self.socket.sendto(json.dumps(message).encode(), (self.receiver_ip, self.receiver_port))

            data, addr = self.socket.recvfrom(1024)
            response = json.loads(data.decode())

            if response["type"] == "connect_ack" and response["status"] == "connected":
                self.connected = True
                print(f"Connected to receiver at {addr}")
                return True
            else: 
                print("Failed to connect to receiver")
                return False
            
        except socket.timeout:
            print("Connection timeout - receiver not responding")
            return False
        except Exception as e:
            print(f"Error during connection: {e}")
            return False
        
    def disconnect(self):
        if not self.connected:
            print("Not connected to any receiver")
            return
        
        message = {"type": "disconnect", "transmitter_id": self.transmitter_id}

        try: 
            self.socket.sendto(json.dumps(message).encode(), (self.receiver_ip, self.receiver_port))
            data, addr = self.socket.recvfrom(1024)
            response = json.loads(data.decode())

            if response["type"] == "disconnect_ack":
                self.connected = False
                print(f"Disconnected from receiver at {addr}")

        except Exception as e:
            print(f"Error during disconnection: {e}")

    
    # logig for passing audio data would go here
    # def send_audio_data(self, audio_data):
    #    if self.connected:
    #      pass