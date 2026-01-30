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
        sock = None

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) # Create UDP socket
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
            if sock is not None:
                sock.close()
            print("PTP monitoring stopped")

    def is_synced(self): # returns true if recent PTP traffic is detected
        return self.ptp_detected and (time.time() - self.last_ptp_time) <= self.sync_timeout

    def get_sync_status(self): # Get current sync status as string
        return "Synchronized" if self.is_synced() else "Not Synchronized"
    
    def stop (self):
        self.running = False

class AudioFader:

    def __init__(self, fade_duration_ms=500):

        self.fade_duration_ms = fade_duration_ms
        self.step_ms = 10
        self.num_steps = fade_duration_ms // self.step_ms

    def generate_fade_out_curve(self):
        curve = []
        for i in range(self.num.steps):
            progress = i / (self.num_steps -1)

            db_reduction = -60 * progress
            gain = 10 ** (db_reduction / 20)

            curve.append(gain)

        return curve
    
    def generate_fade_in_curve(self):

        return list(reversed(self.generate_fade_out_curve()))
    
    def apply_fade_out(self, audio_source, callback=None):
        curve = self.generate_fade_out_curve()

        for i, gain in enumerate(curve):
            # audio_source.set_gain(gain)  
            # # Placeholder for actual audio gain adjustment
            # Show progress every 10 steps
            if i % 10 == 0:
                db = 20 * math.log10(gain) if gain > 0.001 else -60
                print(f"    Fade progress: {int(100*i/len(curve))}% (gain: {gain:.3f}, {db:.1f}dB)")
            
            time.sleep(self.step_ms / 1000.0) #convert ms to seconds

        if callback:
            callback() 

    def apply_fade_in(self, audio_source, callback=None):

        curve = self.generate_fade_in_curve()

        for i, gain in enumerate(curve):

            if i % 10 == 0:
                db = 20 * math.log10(gain) if gain > 0.001 else -60
                print(f"    Fade progress: {int(100*i/len(curve))}% (gain: {gain:.3f}, {db:.1f}dB)")
            
            time.sleep(self.step_ms / 1000.0)

        if callback:
            callback()

class AudioSafetyController:
    
    def __init__(self, transmitters_dict=None):
        self.transmitters = transmitters_dict  # List of your TX objects
        self.muted = False
        self.fader = AudioFader(fade_duration_ms=500)
        self.mute_reason = None

    def add_transmitter(self, name, transmitter):
        self.transmitters[name] = transmitter

    def remove_transmitter(self, name):
        if name in self.transmitters:
            del self.transmitters[name]
            print(f"  Removed transmitter {name} from clock monitoring")
        
    def handle_sync_loss(self, reason):
        if self.muted:
            return  # Already muted
        
        print(f"✗ Clock sync lost ({reason})")
        print("  Muting audio outputs with fade-out...")
        
        self.mute_reason = reason

        for tx_name, tx in self.transmitters.items():
            print(f"  Muting {tx_name}")
            # self.fader.apply_fade_out(tx.audio_source)  # Future implementation
            # tx.mute()  # Placeholder for actual mute method
            self.fader.apply_fade_out(tx)

            print(f"  {tx_name} muted")

        self.muted = True

        print("  ✓ All audio outputs muted. Waiting for clock sync to return...")

    def handle_sync_restored(self):
        if not self.muted:
            print("✓ Clock sync restored")
            print("  Waiting 2 seconds for stability...")
            time.sleep(2)
            
            # Gradual fade back in
            for tx_name, tx in self.transmitters.items():
                print(f"  Unmuting {tx_name}")
                self.fader.apply_fade_in(tx)

                print(f"[{tx_name}] Unmuted")

            self.muted = False
            self.muted_reason = None

            print("All audio outputs unmuted.")

    def get_status(self):

        return {
            "muted": self.muted,
            "reason": self.mute_reason,
            "protected_transmitters": list(self,transmitters.keys())
            }
    
    def emergency_mute_all(self):

        print("Emergency mute activated")

        for tx_name, tx in self.transmitters.items():
            print(f"  Muting {tx_name}")
            self.muted = True
            self.muted_reason = "EMERGENCY"


#example usage and integration test
if __name__ == "__main__":
    print("=== PTP Monitor & Audio Safety Test ===\n")
    
    # Create mock transmitter objects for testing
    class MockTransmitter:
        def __init__(self, name):
            self.name = name
            self.gain = 1.0
        
        def set_gain(self, gain):
            self.gain = gain
    
    # Create transmitters
    transmitters = {
        'Studio_A': MockTransmitter('Studio_A'),
        'Studio_B': MockTransmitter('Studio_B')
    }
    
    # Create safety controller
    safety = AudioSafetyController(transmitters)
    
    # Create and start PTP monitor with callbacks
    ptp = PTPMonitor(
        callback_on_sync_loss=safety.handle_sync_loss,
        callback_on_sync_restore=safety.handle_sync_restored
    )
    ptp.start_monitoring()
    
    # Check initial sync
    print("Checking for PTP sync...\n")
    time.sleep(3)
    
    if ptp.is_synced():
        print("✓ PTP sync confirmed - safe to stream audio\n")
    else:
        print("⚠ No PTP sync detected")
        print("  For testing purposes, continuing anyway...")
        print("  In production, you should abort here\n")
    
    # Simulate running for a while
    print("Monitoring PTP sync (press Ctrl+C to stop)...")
    print("Tip: Disable your PTP master to test sync loss behavior\n")
    
    try:
        while True:
            time.sleep(5)
            status = ptp.get_sync_status()
            if ptp.is_synced():
                time_since_ptp = time.time() - ptp.last_ptp_time
                print(f"Status: {status} (last packet {time_since_ptp:.1f}s ago)")
            else:
                print(f"Status: {status} (failures: {ptp.consecutive_failures})")
    
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        ptp.stop()
        print("Test complete!")