import socket
import threading
import json
import time
import pyaudio
import struct
import queue

# Receiver class to handle incoming connections from AudioIns 

class Receiver:
    def __init__(self, listen_port=5004):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("0.0.0.0", listen_port))
        self.connections = {} # dictionary to connections between transmitters and receivers
        self.running = False
        
        # Audio parameters
        self.SAMPLE_RATE = 16000
        self.CHUNK_SIZE = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        
        self.audio_queue = queue.Queue(maxsize=50)  # Buffer for incoming audio
        self.audio_stream = None
        self.audio_playing = False

    def start(self):
        self.running = True
        listen_thread = threading.Thread(target=self.listen)
        listen_thread.start()

    def listen(self):
        print("Receiver scanning for connections...")
        while self.running:
            try:
                data, addr = self.socket.recvfrom(10240)  # Larger buffer for audio chunks
                
                # Check packet type
                if len(data) > 0 and data[0] == ord('{'):
                    # Control message
                    try:
                        message = json.loads(data.decode())
                        
                        if message["type"] == "connect":
                            self.handle_connect(message, addr)
                        elif message["type"] == "disconnect":
                            self.handle_disconnect(message, addr)
                        elif message["type"] == "ping":
                            self.handle_ping(addr)
                    except json.JSONDecodeError:
                        pass  # Not a valid JSON message, skip
                else:
                    # Assume RTP audio packet
                    self.handle_rtp_packet(data, addr)

            except Exception as e:
                if self.running:
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
        if self.audio_playing:
            self.stop_audio_playback()

    def handle_rtp_packet(self, data, addr):
        """Parse RTP packet and queue audio payload"""
        if len(data) < 12:
            return
        
        # Check RTP version (should be 2)
        version = (data[0] >> 6) & 0x03
        if version != 2:
            return
        
        # Extract RTP header fields (for reference)
        seq_num = struct.unpack('!H', data[2:4])[0]
        timestamp = struct.unpack('!I', data[4:8])[0]
        ssrc = struct.unpack('!I', data[8:12])[0]
        
        # Payload starts after 12-byte header
        payload = data[12:]
        
        # Assume PCM 16-bit mono audio payload
        audio_data = payload
        
        # Track connection
        addr_str = f"{addr[0]}:{addr[1]}"
        if addr_str not in self.connections:
            self.connections[addr_str] = {
                "ip": addr[0],
                "port": addr[1],
                "connected_at": time.time()
            }
            print(f"RTP stream connected from {addr}")
        
        # Queue audio for playback
        try:
            self.audio_queue.put_nowait(audio_data)
        except queue.Full:
            pass  # Drop if buffer full

    def start_audio_playback(self):
        """Initialize and start audio playback"""
        try:
            self.audio_playing = True
            playback_thread = threading.Thread(target=self._audio_playback_loop)
            playback_thread.daemon = True
            playback_thread.start()
            print(f"Audio playback started - playing to speaker at {self.SAMPLE_RATE}Hz")
            return True
        except Exception as e:
            print(f"Error starting audio playback: {e}")
            self.audio_playing = False
            return False

    def _audio_playback_loop(self):
        """Continuously play audio from queue to speaker"""
        p = pyaudio.PyAudio()
        
        try:
            # Open audio output stream to speaker
            self.audio_stream = p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                output=True,
                frames_per_buffer=self.CHUNK_SIZE
            )
            
            print(f"Speaker output opened: {self.CHANNELS} channel(s), {self.SAMPLE_RATE}Hz")
            
            while self.audio_playing:
                try:
                    # Get audio from queue with timeout
                    audio_data = self.audio_queue.get(timeout=1.0)
                    
                    # Play audio
                    self.audio_stream.write(audio_data)
                    
                except queue.Empty:
                    # No data available, play silence
                    silence = b'\x00' * (self.CHUNK_SIZE * 2)  # 2 bytes per sample (16-bit)
                    self.audio_stream.write(silence)
        
        except Exception as e:
            print(f"Error in audio playback loop: {e}")
        
        finally:
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            p.terminate()
            print("Speaker output closed")

    def stop_audio_playback(self):
        """Stop audio playback"""
        if self.audio_playing:
            print("Stopping audio playback...")
            self.audio_playing = False
            time.sleep(0.5)  # Give thread time to close cleanly
            print("Audio playback stopped")


