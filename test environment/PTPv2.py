# logic for monitoring clock synchronization using PTPv2 would go here
import socket
import struct
import time
import threading
import math

class PTPMonitor:

    def __init__(self, callback_on_sync_loss=None, callback_on_sync_restore=None):
 
        self.ptp_detected = False
        self.last_ptp_time = 0
        self.sync_timeout = 2.0
        self.callback_loss = callback_on_sync_loss
        self.callback_restrore = callback_on_sync_restore
        self.running = False
        self.consecutive_failures = 0
        self.failure_threshold = 3  # Number of consecutive failures before triggering loss
        self.was_synced = False
        

    def start_monitoring(self): # Start background thread to monitor PTP traffic
        self.running = True
        monitor_thread = threading.Thread(target=self._monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        print("PTP monitoring started")

    def _monitor_loop(self): # Internal loop to check for PTP traffic periodically

        PTP_EVENT_PORT = 319
        PTP_MULTICAST_ADDR = "224.0.1.129" # Standard PTPv2 multicast address

        try:
            sock = socket.socket(AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) # Create UDP socket
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            sock.bind(('', PTP_EVENT_PORT)) # bind to PTP port
            sock.settimeout(1.0)

            # Join the multicast group to recieve PTP packets
            mreq = struct.pack("4sl", socket.inet_aton(PTP_MULTICAST_ADDR), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            print(f"listening for PTP packets on port {PTP_EVENT_PORT}...")

            while self.running:
                try:
                    data, addr = sock.recvfrom(1024) # Receive PTP packet
                    self.last_ptp_time = time.time() # Packet received, clock sync now active

                    if not self.was_synced:
                        print(f"✓ PTPv2 traffic detected from {addr[0]}, clock synchronized")
                        self.was_synced = True

                        if self.callback_restore and self.consecutive_failures > 0:
                            self.callback_restore()
                    
                    self.consecutive_failures = 0 # Reset failure count on successful packet receipt
                    self.ptp_detected = True

                except socket.timeout: 
                    # Check if sync is lost
                    time_since_last_ptp = time.time() - self.last_ptp_time
                    
                    if time_since_last_ptp > self.sync_timeout:
                        self.consecutive_failures += 1

                        if self.consecutive_failures >= self.failure_threshold:
                            if self.ptp_detected: # Only prints statement if state changed
                                print(f" PTP sync lost - no PTPv2 traffic for {time_since_last_ptp:.1f} seconds")
                            self.was_synced = False
                            self.ptp_detected = False

                            # trigger callback to initiate audio mute
                            if self.callback_loss:
                                self.callback_loss("PTP_TIMEOUT")

        except PermissionError:
            print("Permission denied: Unable to open socket for PTP monitoring. Try running as administrator/root.")
            print("PTP monitoring disabled.")

        except Exception as e:
            print(f"Error in PTP monitoring: {e}")

        finally:
            sock.close()
            print("PTP monitoring stopped")

class AudioSafetyController:
    
    def __init__(self, transmitters):
        self.transmitters = transmitters  # List of your TX objects
        self.muted = False
        
    def handle_sync_loss(self, reason):
        if not self.muted:
            print(f"⚠⚠⚠ CLOCK SYNC FAILURE: {reason}")
            print("Initiating safe audio shutdown...")
            
            # In real implementation with actual audio:
            # 1. Apply fade-out over 500ms
            # 2. Then mute completely
            # 3. Maintain connection for quick recovery
            
            # For now, just disconnect
            for tx_name, tx in self.transmitters.items():
                print(f"  Muting {tx_name} for speaker protection")
                # tx.apply_fade_out()  # Future implementation
                # tx.mute()  # Future implementation
                
            self.muted = True
            
    def handle_sync_restored(self):
        if self.muted:
            print("✓ Clock sync restored")
            print("  Waiting 2 seconds for stability...")
            time.sleep(2)
            
            # Gradual fade back in
            for tx_name, tx in self.transmitters.items():
                print(f"  Unmuting {tx_name}")
                # tx.apply_fade_in()  # Future implementation
                # tx.unmute()
                
            self.muted = False