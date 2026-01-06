import RXreceiver
import TXtransmitter
import socket
import threading
import json
import time

def main():
    # Initialize the receiver and transmitter
    receiver = RXreceiver.Receiver()
    transmitter = TXtransmitter.Transmitter(transmitter_id="TX1", receiver_ip="127.0.0.1") 

    # Start the receiver
    receiver.start()   
    time.sleep(1) # Give the receiver a moment to start

    # Connect the transmitter to the receiver
    if transmitter.connect():
        time.sleep(5) # Keep the connection for 5 seconds

        transmitter.disconnect() # Disconnect the transmitter



    
    # Stop the receiver
    receiver.stop() 