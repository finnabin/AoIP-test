import socket
import threading
import json
import time
import pyaudio
import struct

# Transmitter class to manage connections to AudioOuts

class Transmitter:
    def __init__ (self, transmitter_id, receiver_ip, receiver_port=5004):
        self.transmitter_id = transmitter_id
        self.receiver_ip = receiver_ip
        self.receiver_port = receiver_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(5)  # 5 second timeout for socket operations
        self.connected = False
        
        # Audio parameters
        self.SAMPLE_RATE = 16000  # 16 kHz
        self.CHUNK_SIZE = 1024    # Samples per chunk
        self.FORMAT = pyaudio.paInt16  # 16-bit PCM
        self.CHANNELS = 1  # Mono
        
        self.audio_stream = None
        self.audio_running = False
        self.sequence_number = 0

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

    def start_audio_stream(self):
        """Initialize and start audio capture from microphone"""
        if not self.connected:
            print("Cannot start audio: not connected to receiver")
            return False
        
        try:
            self.audio_running = True
            audio_thread = threading.Thread(target=self._audio_capture_loop)
            audio_thread.daemon = True
            audio_thread.start()
            print(f"Audio stream started - capturing from microphone at {self.SAMPLE_RATE}Hz")
            return True
        except Exception as e:
            print(f"Error starting audio stream: {e}")
            self.audio_running = False
            return False

    def _audio_capture_loop(self):
        """Continuously capture audio and send to receiver"""
        p = pyaudio.PyAudio()
        
        try:
            # Open audio input stream from microphone
            self.audio_stream = p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                input=True,
                frames_per_buffer=self.CHUNK_SIZE
            )
            
            print(f"Microphone input opened: {self.CHANNELS} channel(s), {self.SAMPLE_RATE}Hz, {self.CHUNK_SIZE} samples/chunk")
            
            while self.audio_running:
                try:
                    # Read audio data from microphone
                    audio_data = self.audio_stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                    
                    # Create audio packet with header
                    packet = self._create_audio_packet(audio_data)
                    
                    # Send to receiver
                    self.socket.sendto(packet, (self.receiver_ip, self.receiver_port))
                    
                    self.sequence_number += 1
                    
                except Exception as e:
                    if self.audio_running:
                        print(f"Error capturing/sending audio: {e}")
        
        except Exception as e:
            print(f"Error in audio capture loop: {e}")
        
        finally:
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            p.terminate()
            print("Audio stream closed")

    def _create_audio_packet(self, audio_data):
        """Create audio packet with header: [type(1)][seq_num(4)][sample_rate(4)][data]"""
        packet_type = b'A'  # 'A' for audio
        seq_header = struct.pack('I', self.sequence_number)
        sample_rate_header = struct.pack('I', self.SAMPLE_RATE)
        
        return packet_type + seq_header + sample_rate_header + audio_data

    def stop_audio_stream(self):
        """Stop audio capture"""
        if self.audio_running:
            print("Stopping audio stream...")
            self.audio_running = False
            time.sleep(0.5)  # Give thread time to close cleanly
            print("Audio stream stopped")