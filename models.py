# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Target(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    key = db.Column(db.String(255), nullable=False)
    delimiter = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='offline')
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime)

class Connection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('target.id'), nullable=False)
    bot_id = db.Column(db.String(50))
    ip = db.Column(db.String(50), nullable=False)
    country = db.Column(db.String(2))
    connected_at = db.Column(db.DateTime, default=datetime.utcnow)
    disconnected_at = db.Column(db.DateTime)

class FileHash(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    connection_id = db.Column(db.Integer, db.ForeignKey('connection.id'), nullable=False)
    filename = db.Column(db.String(255))
    file_hash = db.Column(db.String(64), nullable=False)
    captured_at = db.Column(db.DateTime, default=datetime.utcnow)

class URL(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    connection_id = db.Column(db.Integer, db.ForeignKey('connection.id'), nullable=False)
    url = db.Column(db.Text, nullable=False)
    captured_at = db.Column(db.DateTime, default=datetime.utcnow)

class PacketLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('target.id'), nullable=False)
    connection_id = db.Column(db.Integer, db.ForeignKey('connection.id'))
    ip = db.Column(db.String(50), nullable=False)
    command = db.Column(db.String(50))
    content = db.Column(db.Text)
    file_hash = db.Column(db.String(64))
    file_path = db.Column(db.String(500))
    captured_at = db.Column(db.DateTime, default=datetime.utcnow)

class ConnectionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('target.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class IPGeolocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), unique=True, nullable=False, index=True)
    country_code = db.Column(db.String(2))
    country = db.Column(db.String(100))
    continent_code = db.Column(db.String(2))
    continent = db.Column(db.String(50))
    asn = db.Column(db.String(50))
    as_name = db.Column(db.String(255))
    cached_at = db.Column(db.DateTime, default=datetime.utcnow)