# logic for monitoring clock synchronization using PTPv2 would go here
import socket
import struct

class PTPMonitor:

    def __init__(self): 
        self.ptp_detected = False
        self.master_clock_id = None

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
