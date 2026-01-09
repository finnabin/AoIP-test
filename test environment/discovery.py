import socket
import struct
import threading
import json
import time

class AES67Discovery:
    def __init__ (self, manual_config_path=None):
        self.discovered_devices = {}
        self.running = False
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

    def start_sap_discovery(self): # start listening for SAP announcements from AES67 devices
        self.running = True
        sap_thread = threading.Thread(target=self._sap_listener)
        sap_thread.start()
        print ("SAP discovery started")

    def _sap_listener(self): # listens for SAP announcements
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
        except Exception as e:
            print(f"Error in SAP listener: {e}")
        finally:
            sock.close()

    def _parse_sap_packet(self, data, addr): # parse SAP packets and extract device info
            try:
                if len(data) <8:
                    return # Not a valid SAP packet
                #skip SAP header (first 8 bytes)
                sdp_offset = 8
                auth_len=data[1] & 0x0F
                sdp_offset += auth_len *4

                sdp_data = data[sdp_offset:].decode("utf-8", errors="ignore")

                if device_info:
                    device_id = device_info.get("session_name", f"device_{addr[0]}")
                    self.discovered_devices[device_id] = device_info
                    print(f"Discovered device {device_id} at {device_info["ip"]}:{device_info["port"]}")

            except Exception as e:
                print(f"Error parsing SAP packet from {addr}: {e}")

    def _parse_sdp(self, sdp_data, addr): # extract relevant info from SDP data
            device_info = {
                "ip": addr[0],
                "port": None,
                "session_name": None,
                "media_type": None,
                "discovered_at": time.time()
            }

            try:
                for line in sdp_data.split("\n"):
                    line = line.strip()

                    # session name
                    if line.startswith ("s="):
                        device_info["session_name"] = line[2:].strip()

                    # connection data
                    elif line.startswith("c="):
                        parts = line.split()
                        if len(parts) >=3:
                            device_info["ip"] = parts[2].split("/")[0]

                    # media description
                    elif line.startswith("m="):
                        parts = line.split()
                        if len(parts) >=3:
                            device_info["media_type"] = parts[0][2:] # "audio" or "video"
                            device_info["port"] = int(parts[1])

                return device_info if device_info["port"] else None
            
            except Exception as e:
                print(f"Error parsing SDP data from {addr}: {e}")
                return None
            
    def get_discovered_devices(self): # return list of discovered devices
            all_devices = dict(self.discovered_devices)

            # include manual config devices if available
            if self.manual_config:
                for device in self.manual.config.get("devices", []):
                    device_id = device.get("device id")
                    if device_id and device_id not in all_devices:
                        all_devices[device_id] = device

            return all_devices
    
    def get_device_by_id(self, device_id): # get specific device by ID
            devices = self.get_discovered_devices()
            return devices.get(device_id)
        
    def show_devices(self): # print discovered devices
            devices = self.get_discovered_devices()
            if not devices:
                print("No devices discovered.")
                return
            
            print("Discovered AES67 Devices:")
            for device_id, info in devices.items():
                print(f"- ID: {device_id}, IP: {info['ip']}, Port: {info['port']}, Media: {info['media_type']}")

    def stop(self): # stop discovery process
            self.running = False
            print("SAP discovery stopped")


      