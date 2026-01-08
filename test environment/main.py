import RXreceiver
import TXtransmitter
import discovery
import time

def main():
    print("=== AudioOverIP Test Environment ===")

    # Initialize the receiver and transmitter
    receiver = RXreceiver.Receiver()
    transmitter = TXtransmitter.Transmitter(transmitter_id="TX1", receiver_ip="127.0.0.1") 
    print("Receiver started on port 5004")

    # Start device discovery
    discoverer = discovery.AES67Discovery(manual_config_path="config.json")
    discoverer.start_SAP_discovery()

    print("Discovering devices...")
    time.sleep(5)

    # List discovered devices
    discoverer.show_devices()

    # Start the receiver
    receiver.start()   
    time.sleep(1) # Give the receiver a moment to start

    tx1 = TXtransmitter.Transmitter(transmitter_id="MICROPHONE", receiver_ip="127.0.0.1")
    tx2 = TXtransmitter.Transmitter(transmitter_id="SPEAKER", receiver_ip="127.0.0.1")

    print("Attempting to connect transmitter TX1...") # first transmitter test
    if tx1.connect():
            print("TX1 connected successfully.")
            receiver.connections()
    else:
            print("TX1 failed to connect.")

    time.sleep(2)
    print("Attempting to connect transmitter TX2...") # second transmitter test
    if tx2.connect():
            print("TX2 connected successfully.")
            receiver.connections()
    else:
            print("TX2 failed to connect.")

    time.sleep(2)

    print ("Disconnecting transmitter TX1...") # disconnect first transmitter test
    tx1.disconnect()
    time.sleep(1)
    receiver.connections()

    print ("Disconnecting transmitter TX2...") # disconnect second transmitter test
    tx2.disconnect() 
    time.sleep(1)
    receiver.connections()

    # Connect the transmitter to the receiver
    if transmitter.connect():
        time.sleep(5) # Keep the connection for 5 seconds

        transmitter.disconnect() # Disconnect the transmitter




    
    # Stop the receiver
    receiver.stop() 

if __name__ == "__main__":
        main()