# logic for monitoring clock synchronization using PTPv2 would go here
import socket
import struct

class PTPMonitor:

    def __init__(self): 
        self.ptp_detected = False
        self.master_clock_id = None


        #start monitoring ptp traffic (clock sync status) 
    def start_monitoring(self): 
        self.running = True
        monitor_thread = threading.Thread(target=self._monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()

    def check_ptp_traffic(self, timeout=5): # Check for PTPv2 traffic on the network to detect master clock
        PTP_EVENT_PORT = 319

        try: 
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", PTP_EVENT_PORT))
            sock.settimeout(timeout)
            
            mreq = struct.pack("4sl", socket.inet_aton("224.0.1.129"), socket.INADDR_ANY) # Join PTP multicast group
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            
            print(f"Listening for PTP packets for {timeout} seconds...")
            
            try:
                data, addr = sock.recvfrom(1024)
                self.ptp_detected = True
                print(f"✓ PTP traffic detected from {addr[0]}")
                return True
            except socket.timeout:
                self.ptp_detected = False
                print("✗ No PTP traffic detected")
                return False
                
        except PermissionError:
            print("⚠ Cannot bind to PTP port (requires admin/root)")
            return None
        except Exception as e:
            print(f"Error checking PTP: {e}")
            return None
        finally:
            sock.close()
    
    def verify_sync_before_streaming(self): # Verify PTP synchronization before starting audio streaming
        if self.check_ptp_traffic():
            print("Clock synchronized via PTPv2")
            return True
        else:
            print("  Ensure PTP master clock is running on network")
            return False



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