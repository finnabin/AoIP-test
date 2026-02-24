import RXreceiver
import TXtransmitter
import discovery
import PTPv2
import time

"""
This is the main script for my AudioOverIP test environment with PTP protection.
Currently, the JSON config file is set to locate other devices manually.
"""



def main():
    print("="*60)
    print("=== AudioOverIP Test Environment with PTP Protection ===")
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

    # STEP 2: Discover AES67 devices on the network
    print("\nSTEP 2: Discovering AES67 devices...")
    print("-" * 60)
    
    # Start device discovery (SAP + manual config fallback)
    discoverer = discovery.AES67Discovery(manual_config_path="config.json")
    discoverer.start_sap_discovery()

    print("Scanning for SAP announcements...")
    time.sleep(5)  # Wait for SAP devices to announce themselves

    # Show what we found
    discoverer.show_devices()

    # Get all discovered devices (SAP + manual config)
    devices = discoverer.get_discovered_devices()
    
    if not devices:
        print("⚠ No devices discovered! Check that:")
        print("  - Devices are in AES67 mode")
        print("  - Devices are announcing via SAP")
        print("  - config.json has manual fallback devices")
        
        # Clean shutdown
        discoverer.stop()
        ptp_monitor.stop()
        return

    # STEP 3: Start the receiver
    print("\nSTEP 3: Starting audio receiver...")
    print("-" * 60)
    
    receiver = RXreceiver.Receiver()
    receiver.start()
    print("✓ Receiver started on port 5004")
    time.sleep(1)

    # STEP 4: Create transmitters from discovered devices
    print("\nSTEP 4: Connecting to discovered devices...")
    print("-" * 60)
    
    transmitters = {}  # Dictionary to store our transmitter objects
    device_list = list(devices.items())
    
    # Try to connect to first discovered device
    if len(device_list) >= 1:
        device_id, device_info = device_list[0]
        print(f"\nConnecting to: {device_id}")
        print(f"  IP: {device_info['ip']}")
        print(f"  Port: {device_info.get('port', 5004)}")
        
        # Create transmitter object
        tx1 = TXtransmitter.Transmitter(
            transmitter_id=device_id,
            receiver_ip=device_info['ip'],
            receiver_port=device_info.get('port', 5004)
        )
        
        # Attempt connection
        if tx1.connect():
            print(f"✓ {device_id} connected successfully")
            transmitters['tx1'] = tx1
            
            # IMPORTANT: Add this transmitter to safety monitoring
            # Now if PTP is lost, this transmitter will be safely muted
            safety_controller.add_transmitter('tx1', tx1)
            
            receiver.show_connections()
        else:
            print(f"✗ {device_id} failed to connect")

    time.sleep(2)

    # Try to connect to second discovered device
    if len(device_list) >= 2:
        device_id, device_info = device_list[1]
        print(f"\nConnecting to: {device_id}")
        print(f"  IP: {device_info['ip']}")
        print(f"  Port: {device_info.get('port', 5004)}")
        
        tx2 = TXtransmitter.Transmitter(
            transmitter_id=device_id,
            receiver_ip=device_info['ip'],
            receiver_port=device_info.get('port', 5004)
        )
        
        if tx2.connect():
            print(f"✓ {device_id} connected successfully")
            transmitters['tx2'] = tx2
            
            # Add to safety monitoring
            safety_controller.add_transmitter('tx2', tx2)
            
            receiver.show_connections()
        else:
            print(f"✗ {device_id} failed to connect")

    # STEP 5: Start audio streams
    print("\nSTEP 5: Starting audio streams...")
    print("-" * 60)
    
    # Start receiver audio playback (listening for incoming audio)
    receiver.start_audio_playback()
    time.sleep(1)
    
    # Start transmitter audio capture
    for tx_name, tx in transmitters.items():
        tx.start_audio_stream()
        time.sleep(0.5)

    # STEP 6: Simulate streaming (PTP monitor running in background)
    print("\n" + "="*60)
    print("STEP 6: Audio streaming active")
    print("="*60)
    print("\nAudio is being transmitted and received...")
    print("PTP monitoring active in background")
    print("  - If PTP sync is lost, audio will fade out automatically")
    print("  - If PTP sync returns, audio will fade in automatically")
    print("\nStreaming for 10 seconds...")
    print("(Try disabling PTP master clock to test protection)\n")
    
    # Stream for 10 seconds while PTP monitor watches in background
    for i in range(10):
        time.sleep(1)
        
        # Check and display PTP status
        is_synced = ptp_monitor.is_synced()
        safety_status = safety_controller.get_status()
        
        if is_synced:
            sync_indicator = "✓ SYNCED"
        else:
            sync_indicator = "✗ NOT SYNCED"
        
        mute_indicator = "🔇 MUTED" if safety_status['muted'] else "🔊 ACTIVE"
        
        print(f"  [{i+1}/10s] PTP: {sync_indicator} | Audio: {mute_indicator}")

    # STEP 7: Stop audio streams
    print("\nSTEP 7: Stopping audio streams...")
    print("-" * 60)
    
    for tx_name, tx in transmitters.items():
        tx.stop_audio_stream()
        time.sleep(0.3)
    
    receiver.stop_audio_playback()

    # STEP 8: Clean disconnection
    print("\nSTEP 8: Clean shutdown sequence")
    print("="*60 + "\n")
    
    # Disconnect transmitters gracefully
    if 'tx1' in transmitters:
        device_id = transmitters['tx1'].transmitter_id
        print(f"Disconnecting {device_id}...")
        
        # Remove from safety monitoring first
        safety_controller.remove_transmitter('tx1')
        
        # Then disconnect
        transmitters['tx1'].disconnect()
        time.sleep(1)
        receiver.show_connections()

    if 'tx2' in transmitters:
        device_id = transmitters['tx2'].transmitter_id
        print(f"Disconnecting {device_id}...")
        
        safety_controller.remove_transmitter('tx2')
        transmitters['tx2'].disconnect()
        time.sleep(1)
        receiver.show_connections()

    # STEP 9: Stop all services
    print("\nStopping all services...")
    receiver.stop()
    print("  ✓ Receiver stopped")
    
    discoverer.stop()
    print("  ✓ Discovery stopped")
    
    ptp_monitor.stop()
    print("  ✓ PTP monitor stopped")
    
    print("\n" + "="*60)
    print("Test complete! All systems shut down safely.")
    print("="*60 + "\n")


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
 