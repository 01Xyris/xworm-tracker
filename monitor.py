from datetime import datetime, timezone
import threading
import socket
from models import db, Target, Connection, ConnectionLog, IPGeolocation
import ipaddress
import time
from utils import decrypt_data, parse_packet, random_str
from packets import PacketHandler, process_packet
from server import Server
from events import emit_network_event
import requests

IPINFO_TOKEN = "8d42e90b08f01c"

class Monitor:
    def __init__(self, target, app):
        self.target = target
        self.app = app
        self.running = False
        self.thread = None
        self.connection_id = None
        self.server = None
        self.reconnect_delay = 120
        self.last_logged_event = None
        self.packet_handler = None
        self.country = None
    
    def get_country(self, ip):
        # Check if IP is private/loopback/reserved first (outside app context)
        is_private = False
        try:
            ip_obj = ipaddress.ip_address(ip)
            is_private = ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved
        except:
            return 'US'
        
        # Use a single app_context for all database operations
        with self.app.app_context():
            # Check cache first
            cached = IPGeolocation.query.filter_by(ip=ip).first()
            if cached:
                return cached.country_code or 'US'
            
            # Handle private IPs
            if is_private:
                try:
                    geo = IPGeolocation(
                        ip=ip,
                        country_code='US',
                        country='United States',
                        continent_code='NA',
                        continent='North America',
                        asn=None,
                        as_name='Private Network'
                    )
                    db.session.add(geo)
                    db.session.commit()
                except:
                    db.session.rollback()
                return 'US'
            
            # Handle public IPs
            try:
                response = requests.get(
                    f'https://api.ipinfo.io/lite/{ip}?token={IPINFO_TOKEN}',
                    timeout=2
                )
                if response.status_code == 200:
                    data = response.json()
                    
                    geo = IPGeolocation(
                        ip=ip,
                        country_code=data.get('country_code'),
                        country=data.get('country'),
                        continent_code=data.get('continent_code'),
                        continent=data.get('continent'),
                        asn=data.get('asn'),
                        as_name=data.get('as_name')
                    )
                    db.session.add(geo)
                    db.session.commit()
                    
                    return data.get('country_code') or 'US'
            except:
                db.session.rollback()
        
        return 'US'
    
    def log_connection_event(self, event_type, message):
        try:
            with self.app.app_context():
                last_log = ConnectionLog.query.filter_by(
                    target_id=self.target.id
                ).order_by(ConnectionLog.created_at.desc()).first()
                
                if last_log and last_log.event_type == event_type:
                    last_log.created_at = datetime.now(timezone.utc)
                    last_log.message = message
                    db.session.commit()
                else:
                    log = ConnectionLog(
                        target_id=self.target.id,
                        event_type=event_type,
                        message=message
                    )
                    db.session.add(log)
                    db.session.commit()
        except:
            pass
    
    def process_received_packet(self, decrypted_str, delimiter):
        parts = decrypted_str.split(delimiter)
        
        if len(parts) < 1:
            return
        
        command = parts[0].strip()
        
        if not command or len(command) < 2 or command == delimiter.strip():
            return
        
        process_packet(command, parts, self.packet_handler, self.app)
    
    def run(self):
        while self.running:
            botid = random_str(20)
            handshake_verified = False
            self.server = Server(self.target)
            
            try:
                with self.app.app_context():
                    target = Target.query.get(self.target.id)
                    if not target:
                        break
                    target.status = 'connecting'
                    db.session.commit()
                
                if not self.server.connect():
                    with self.app.app_context():
                        target = Target.query.get(self.target.id)
                        if target:
                            target.status = 'offline'
                            db.session.commit()
                    
                    self.log_connection_event('failed', f'Connection failed to {self.target.ip}:{self.target.port}')
                    self.server.close()
                    time.sleep(self.reconnect_delay)
                    continue
                
                handshake_verified, buffer = self.server.verify_handshake(botid)
                
                if not handshake_verified:
                    with self.app.app_context():
                        target = Target.query.get(self.target.id)
                        if target:
                            target.status = 'offline'
                            db.session.commit()
                    
                    self.log_connection_event('failed', f'Handshake failed with {self.target.ip}:{self.target.port}')
                    self.server.close()
                    time.sleep(self.reconnect_delay)
                    continue
                
                self.country = self.get_country(self.target.ip)
                
                with self.app.app_context():
                    target = Target.query.get(self.target.id)
                    if not target:
                        break
                    target.status = 'online'
                    target.last_seen = datetime.now(timezone.utc)
                    db.session.commit()
                    
                    connection = Connection(
                        target_id=self.target.id,
                        bot_id=botid,
                        ip=self.target.ip,
                        country=self.country
                    )
                    db.session.add(connection)
                    db.session.commit()
                    self.connection_id = connection.id
                
                emit_network_event('connection_online', self.country, self.target.ip)
                time.sleep(0.1)
                emit_network_event('request', self.country, self.target.ip)
                time.sleep(0.1)
                emit_network_event('response', self.country, self.target.ip)
                
                self.packet_handler = PacketHandler(self.target, self.connection_id, self.app)
                self.log_connection_event('success', f'Connected to {self.target.ip}:{self.target.port}')
                
                while self.running:
                    try:
                        data = self.server.receive()
                        if not data:
                            break
                        
                        buffer += data
                        
                        while True:
                            encrypted, buffer = parse_packet(buffer)
                            if not encrypted:
                                break
                            
                            decrypted = decrypt_data(encrypted, self.target.key)
                            if decrypted:
                                decrypted_str = decrypted.decode('utf-8', errors='ignore')
                                
                                if decrypted_str == "PING!":
                                    emit_network_event('ping_request', self.country, self.target.ip)
                                    emit_network_event('ping_response', self.country, self.target.ip)
                                    self.server.send_ping()
                                else:
                                    self.process_received_packet(decrypted_str, self.target.delimiter)
                                
                                with self.app.app_context():
                                    target = Target.query.get(self.target.id)
                                    if target:
                                        target.last_seen = datetime.now(timezone.utc)
                                        db.session.commit()
                    
                    except socket.timeout:
                        continue
                    except Exception:
                        break
                            
            except Exception:
                pass
            finally:
                with self.app.app_context():
                    target = Target.query.get(self.target.id)
                    if target:
                        target.status = 'offline'
                        if self.connection_id:
                            connection = Connection.query.get(self.connection_id)
                            if connection:
                                connection.disconnected_at = datetime.now(timezone.utc)
                                emit_network_event('connection_offline', self.country, self.target.ip)
                        db.session.commit()
                
                if handshake_verified:
                    self.log_connection_event('disconnected', f'Disconnected from {self.target.ip}:{self.target.port}')
                
                if self.server:
                    self.server.close()
                
                if self.running:
                    time.sleep(self.reconnect_delay)
    
    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
    
    def stop(self):
        self.running = False
        if self.server:
            self.server.close()
        if self.thread:
            self.thread.join(timeout=2)


monitors = {}
monitors_lock = threading.Lock()


def start_monitor(target, app):
    with monitors_lock:
        key = target.id
        if key in monitors:
            return monitors[key]
        monitor = Monitor(target, app)
        monitor.start()
        monitors[key] = monitor
        return monitor


def stop_monitor(target_id):
    with monitors_lock:
        if target_id in monitors:
            monitors[target_id].stop()
            del monitors[target_id]
    
    from flask import current_app
    with current_app.app_context():
        target = Target.query.get(target_id)
        if target:
            target.status = 'offline'
            db.session.commit()


def start_all_monitors(app):
    with app.app_context():
        targets = Target.query.all()
        for target in targets:
            start_monitor(target, app)