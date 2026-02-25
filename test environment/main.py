import RXreceiver
import TXtransmitter
import discovery
import PTPv2
import time
import argparse
import json

"""
This is the main script for my AudioOverIP test environment with PTP protection.
Each device can be configured as either a transmitter (source) or receiver (sink).
Configuration can be set in config.json or overridden via CLI arguments.
"""


def load_config_and_role():
    """Load config.json and parse CLI arguments to determine device role"""
    # Load config file
    config = {}
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Warning: config.json not found, using defaults")
        config = {
            "device_role": "receiver",
            "receiver_ip": "192.168.1.101",
            "receiver_port": 5004,
            "streaming_duration_seconds": 10
        }
    except json.JSONDecodeError as e:
        print(f"Error parsing config.json: {e}")
        return None, None

    # Parse CLI arguments
    parser = argparse.ArgumentParser(
        description="AudioOverIP test environment with PTP protection"
    )
    parser.add_argument(
        '--role',
        choices=['transmitter', 'receiver'],
        help='Device role: transmitter (source) or receiver (sink). Overrides config.json'
    )
    parser.add_argument(
        '--receiver-ip',
        help='Receiver IP address (for transmitter mode). Overrides config.json'
    )
    parser.add_argument(
        '--duration',
        type=int,
        help='Streaming duration in seconds (for transmitter mode). Overrides config.json'
    )
    
    args = parser.parse_args()
    
    # Apply CLI overrides
    if args.role:
        config['device_role'] = args.role
    if args.receiver_ip:
        config['receiver_ip'] = args.receiver_ip
    if args.duration:
        config['streaming_duration_seconds'] = args.duration
    
    role = config.get('device_role', 'receiver')
    return config, role


def main():
    # Load configuration
    config, device_role = load_config_and_role()
    
    if config is None:
        print("Failed to load configuration")
        return
    
    print("="*60)
    print("=== AudioOverIP Test Environment with PTP Protection ===")
    print(f"=== Device Role: {device_role.upper()} ===")
    print("="*60 + "\n")

    # STEP 1: Initialize PTP monitoring FIRST
    # This is critical - we need to verify clock sync before any audio streaming
    print("STEP 1: Initializing clock sync monitoring...")
    print("-" * 60)
    
    # We'll create the safety controller first, then add transmitters to it later
    safety_controller = PTPv2.AudioSafetyController()
    
    # Create PTP monitor with callbacks to the safety controller
    # When PTP is lost: safety_controller.handle_sync_loss() is called
    # When PTP returns: safety_controller.handle_sync_restored() is called
    ptp_monitor = PTPv2.PTPMonitor(
        callback_on_sync_loss=safety_controller.handle_sync_loss,
        callback_on_sync_restore=safety_controller.handle_sync_restored
    )
    
    # Start monitoring in background thread
    ptp_monitor.start_monitoring()
    
    # Give it a few seconds to detect PTP packets
    print("\nWaiting for PTP sync detection...")
    time.sleep(3)
    
    # Check if we have PTP sync
    if ptp_monitor.is_synced():
        print("✓ PTP clock sync confirmed - safe to proceed")
        print(f"  Sync status: {ptp_monitor.get_sync_status()}\n")
    else:
        print("⚠ WARNING: No PTP sync detected!")
        time.sleep(2)

    # Branch based on device role
    if device_role == "receiver":
        run_receiver_mode(ptp_monitor, safety_controller)
    else:  # transmitter
        run_transmitter_mode(config, ptp_monitor, safety_controller)
    
    # Shutdown PTP monitor
    ptp_monitor.stop()
    print("  ✓ PTP monitor stopped")
    
    print("\n" + "="*60)
    print("Test complete! All systems shut down safely.")
    print("="*60 + "\n")


def run_receiver_mode(ptp_monitor, safety_controller):
    """Run as audio receiver (sink) - listen for incoming streams"""
    print("\nSTEP 2: Starting Audio Receiver (listening mode)...")
    print("-" * 60)
    
    receiver = RXreceiver.Receiver()
    receiver.start()
    print("✓ Receiver started on port 5004")
    print("  Waiting for transmitters to connect...\n")
    time.sleep(1)
    
    # Start audio playback
    receiver.start_audio_playback()
    
    print("\n" + "="*60)
    print("RECEIVER ACTIVE - Listening for audio streams")
    print("="*60)
    print("\nPTP monitoring active in background")
    print("  - If PTP sync is lost, audio will fade out automatically")
    print("  - If PTP sync returns, audio will fade in automatically")
    print("\nPress Ctrl+C to stop listening...\n")
    
    try:
        # Run indefinitely until interrupted
        while True:
            time.sleep(5)
            
            # Periodically check and display PTP status
            is_synced = ptp_monitor.is_synced()
            safety_status = safety_controller.get_status()
            
            if is_synced:
                sync_indicator = "✓ SYNCED"
            else:
                sync_indicator = "✗ NOT SYNCED"
            
            mute_indicator = "🔇 MUTED" if safety_status['muted'] else "🔊 ACTIVE"
            connected_count = len(receiver.connections)
            
            print(f"Status: PTP: {sync_indicator} | Audio: {mute_indicator} | Connections: {connected_count}")
    
    except KeyboardInterrupt:
        print("\n\nReceiver shutdown initiated...")
    
    finally:
        print("\nShutting down receiver...")
        receiver.stop_audio_playback()
        receiver.stop()
        print("  ✓ Receiver stopped")


def run_transmitter_mode(config, ptp_monitor, safety_controller):
    """Run as audio transmitter (source) - capture and send audio"""
    print("\nSTEP 2: Starting Audio Transmitter (capture mode)...")
    print("-" * 60)
    
    receiver_ip = config.get('receiver_ip')
    receiver_port = config.get('receiver_port', 5004)
    duration = config.get('streaming_duration_seconds', 10)
    
    if not receiver_ip:
        print("✗ Error: receiver_ip not configured")
        print("  Set receiver_ip in config.json or use --receiver-ip argument")
        return
    
    print(f"Receiver: {receiver_ip}:{receiver_port}")
    print(f"Duration: {duration} seconds\n")
    
    # STEP 3: Create transmitter
    print("STEP 3: Connecting to receiver...")
    print("-" * 60)
    
    transmitter = TXtransmitter.Transmitter(
        transmitter_id="local_transmitter",
        receiver_ip=receiver_ip,
        receiver_port=receiver_port
    )
    
    # Attempt connection
    if not transmitter.connect():
        print("✗ Failed to connect to receiver")
        print("  Ensure receiver is running at the specified IP address")
        return
    
    print("✓ Connected to receiver successfully\n")
    
    # Add to safety monitoring
    safety_controller.add_transmitter('tx', transmitter)
    
    # STEP 4: Start audio capture
    print("STEP 4: Starting audio capture...")
    print("-" * 60)
    
    if not transmitter.start_audio_stream():
        print("✗ Failed to start audio stream")
        transmitter.disconnect()
        safety_controller.remove_transmitter('tx')
        return
    
    time.sleep(1)
    
    # STEP 5: Stream audio
    print("\n" + "="*60)
    print("TRANSMITTER ACTIVE - Streaming audio")
    print("="*60)
    print("\nAudio is being captured and transmitted...")
    print("PTP monitoring active in background")
    print("  - If PTP sync is lost, audio will fade out automatically")
    print("  - If PTP sync returns, audio will fade in automatically")
    print(f"\nStreaming for {duration} seconds...")
    print("(Try disabling PTP master clock to test protection)\n")
    
    # Stream for specified duration while PTP monitor watches in background
    for i in range(duration):
        time.sleep(1)
        
        # Check and display PTP status
        is_synced = ptp_monitor.is_synced()
        safety_status = safety_controller.get_status()
        
        if is_synced:
            sync_indicator = "✓ SYNCED"
        else:
            sync_indicator = "✗ NOT SYNCED"
        
        mute_indicator = "🔇 MUTED" if safety_status['muted'] else "🔊 ACTIVE"
        
        print(f"  [{i+1}/{duration}s] PTP: {sync_indicator} | Audio: {mute_indicator}")
    
    # STEP 6: Stop audio stream
    print("\nSTEP 6: Stopping audio capture...")
    print("-" * 60)
    
    transmitter.stop_audio_stream()
    time.sleep(0.5)
    
    # STEP 7: Disconnect
    print("\nSTEP 7: Disconnecting from receiver...")
    print("-" * 60)
    
    safety_controller.remove_transmitter('tx')
    transmitter.disconnect()
    
    print("  ✓ Disconnected")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user (Ctrl+C)")
        print("Emergency shutdown...")
        # In a real system, you'd call emergency_mute_all() here
    except Exception as e:
        print(f"\n\n🚨 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
 