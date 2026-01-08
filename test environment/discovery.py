import socket
import struct
import threading
import json
import time

class AES67Discovery:
    def __init__ (self, manual_config_path=None):
        self.discovered.devices = {}
        sekf.running = False
        self.manual_config = None

        if manual_config_path: # check to see if manual config path is provided
            self.load_manual_config(manual_config_path)

    def load_manual_config(self, config_path): # load manual configuration from config.json
        try: 
            with open(config_path, 'r') as f:
                self.manual_config = json.load(f)
                print(f"Manual configuration loaded with {len(self.manual_config['devices'])} devices.")
        except Exception as e:
            print(f"Error loading manual configuration: {e}")

    def start_SAP_discovery(self): # start listening for SAP announcements from AES67 devices
        self.running = True
        sap_thread = threading.Thread(target=self._SAP_listener)
        sap_thread.start()
        print ("SAP discovery started")

    def _SAP_listener(self): # listens for SAP announcements
        MCAST_GRP = "224.2.127.254"
        MCAST_PORT = 9875
            try: 
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("", MCAST_PORT))

                # Join multicast group
                mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

                sock.settimeout(5)  # 5 second timeout for clean shutdown

                print (f"Listening for SAP announcements on {MCAST_GRP}:{MCAST_PORT}...")

           while self.running:
                try:
                    data, addr = sock.recvfrom(10240)
                    self._parse_sap_packet(data, addr)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"Error receiving SAP packet: {e}")