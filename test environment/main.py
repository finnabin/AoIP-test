import RXreceiver
import TXtransmitter
import discovery
import time
import PTPv2

def main():
    print("=== AudioOverIP Test Environment ===")

    # Start device discovery
    discoverer = discovery.AES67Discovery(manual_config_path="config.json")
    discoverer.start_sap_discovery()

    print("Discovering devices...")
    time.sleep(5)

    # List discovered devices
    discoverer.show_devices()

    # get discovered devices
    devices = discoverer.get_discovered_devices()
    
    if not devices:
        print("⚠ No devices discovered! Check that:")
        print("  - Devices are in AES67 mode")
        print("  - Devices are announcing via SAP")
        print("  - config.json has manual fallback devices")
        discoverer.stop()
        print("Exiting - no devices found.")
        return

    # Initialize the receiver
    receiver = RXreceiver.Receiver()
    print("Receiver started on port 5004")
    receiver.start()   
    time.sleep(1)

    # Create transmitters from discovered devices
    transmitters = {}
    device_list = list(devices.items())
    
    # Try to connect to first two discovered devices
    if len(device_list) >= 1:
        device_id, device_info = device_list[0]
        print(f"\nAttempting to connect to discovered device: {device_id}")
        tx1 = TXtransmitter.Transmitter(
            transmitter_id=device_id,
            receiver_ip=device_info['ip'],
            receiver_port=device_info.get('port', 5004)
        )
        if tx1.connect():
            print(f"✓ {device_id} connected successfully")
            transmitters['tx1'] = tx1
            receiver.show_connections()  # FIXED: method call
        else:
            print(f"✗ {device_id} failed to connect")

    time.sleep(2)

    if len(device_list) >= 2:
        device_id, device_info = device_list[1]
        print(f"\nAttempting to connect to discovered device: {device_id}")
        tx2 = TXtransmitter.Transmitter(
            transmitter_id=device_id,
            receiver_ip=device_info['ip'],
            receiver_port=device_info.get('port', 5004)
        )
        if tx2.connect():
            print(f"✓ {device_id} connected successfully")
            transmitters['tx2'] = tx2
            receiver.show_connections()  # FIXED: method call
        else:
            print(f"✗ {device_id} failed to connect")

    PTPv2.PTPMonitor().check_ptp_traffic()

    print("\nStreaming audio for 5 seconds...")

    PTPv2.PTPMonitor().verify_sync_before_streaming()


    time.sleep(5)

    # Disconnect discovered devices
    if 'tx1' in transmitters:
        device_id = transmitters['tx1'].transmitter_id
        print(f"\nDisconnecting {device_id}...")
        transmitters['tx1'].disconnect()
        time.sleep(1)
        receiver.show_connections()  # FIXED: method call

    if 'tx2' in transmitters:
        device_id = transmitters['tx2'].transmitter_id
        print(f"\nDisconnecting {device_id}...")
        transmitters['tx2'].disconnect()
        time.sleep(1)
        receiver.show_connections()  # FIXED: method call

    # Cleanup
    print("\n--- Shutting down ---")
    receiver.stop()
    discoverer.stop()
    print("Test complete!")

if __name__ == "__main__":
    main()


