from pathlib import Path
from datetime import datetime
import base64
import hashlib
import tempfile
from models import db, FileHash, URL, PacketLog


class PacketHandler:
    def __init__(self, target, connection_id, app):
        self.target = target
        self.connection_id = connection_id
        self.app = app
        self.max_memory_buffer = 100 * 1024 * 1024
        self.logs_dir = Path("LOGS")
        self.logs_dir.mkdir(exist_ok=True)
    
    def decode_base64_chunked(self, base64_data, output_file):
        chunk_size = 4 * 1024 * 1024
        padding_needed = (4 - len(base64_data) % 4) % 4
        base64_data += '=' * padding_needed
        
        for i in range(0, len(base64_data), chunk_size):
            chunk = base64_data[i:i + chunk_size]
            decoded_chunk = base64.b64decode(chunk)
            output_file.write(decoded_chunk)
    
    def handle_dw(self, filename, base64_data):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            if len(base64_data) > self.max_memory_buffer:
                self.decode_base64_chunked(base64_data, tmp_file)
            else:
                decoded = base64.b64decode(base64_data)
                tmp_file.write(decoded)
            tmp_path = tmp_file.name
        
        with open(tmp_path, 'rb') as f:
            hasher = hashlib.sha256()
            file_size = 0
            while chunk := f.read(8192):
                hasher.update(chunk)
                file_size += len(chunk)
            file_hash = hasher.hexdigest()
        
        file_name = f"{self.target.ip}_DW_{timestamp}_{file_hash[:8]}.bin"
        file_path = self.logs_dir / file_name
        Path(tmp_path).rename(file_path)
        
        with self.app.app_context():
            fh = FileHash(
                connection_id=self.connection_id,
                filename=filename,
                file_hash=file_hash
            )
            db.session.add(fh)
        
        content = f"Downloaded File: {filename}\nSize: {file_size} bytes"
        return file_path, file_hash, content
    
    def handle_pe(self, base64_runpe, target_path, base64_payload):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            if len(base64_payload) > self.max_memory_buffer:
                self.decode_base64_chunked(base64_payload, tmp_file)
            else:
                payload_data = base64.b64decode(base64_payload)
                tmp_file.write(payload_data)
            tmp_path = tmp_file.name
        
        with open(tmp_path, 'rb') as f:
            hasher = hashlib.sha256()
            file_size = 0
            while chunk := f.read(8192):
                hasher.update(chunk)
                file_size += len(chunk)
            file_hash = hasher.hexdigest()
        
        file_name = f"{self.target.ip}_PE_{timestamp}_{file_hash[:8]}.bin"
        file_path = self.logs_dir / file_name
        Path(tmp_path).rename(file_path)
        
        content = f"Process Injection\nTarget: {target_path}\nPayload Size: {file_size} bytes"
        return file_path, file_hash, content
    
    def handle_script(self, base64_script, script_code, script_type):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        script_content = script_code.encode()
        file_hash = hashlib.sha256(script_content).hexdigest()
        
        file_name = f"{self.target.ip}_script_{timestamp}_{file_hash[:8]}.bin"
        file_path = self.logs_dir / file_name
        
        with open(file_path, 'wb') as f:
            f.write(script_content)
        
        content = f"Script Execution\nType: {script_type}\nSize: {len(script_content)} bytes\n\nScript Content:\n{script_code[:1000]}"
        return file_path, file_hash, content
    
    def handle_ln(self, filename, url):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_hash = None
        
        try:
            import requests
            response = requests.get(url, timeout=10, stream=True)
            if response.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    hasher = hashlib.sha256()
                    file_size = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            tmp_file.write(chunk)
                            hasher.update(chunk)
                            file_size += len(chunk)
                    tmp_path = tmp_file.name
                    file_hash = hasher.hexdigest()
                
                file_name = f"{self.target.ip}_LN_{timestamp}_{file_hash[:8]}.bin"
                file_path = self.logs_dir / file_name
                Path(tmp_path).rename(file_path)
                
                content = f"Downloaded from URL\nFile: {filename}\nURL: {url}\nSize: {file_size} bytes"
            else:
                file_name = f"{self.target.ip}_LN_{timestamp}.txt"
                file_path = self.logs_dir / file_name
                
                info = f"Filename: {filename}\nURL: {url}".encode()
                with open(file_path, 'wb') as f:
                    f.write(info)
                
                content = f"Download Link\nFile: {filename}\nURL: {url}"
        except:
            file_name = f"{self.target.ip}_LN_{timestamp}.txt"
            file_path = self.logs_dir / file_name
            
            info = f"Filename: {filename}\nURL: {url}".encode()
            with open(file_path, 'wb') as f:
                f.write(info)
            
            content = f"Download Link\nFile: {filename}\nURL: {url}"
        
        with self.app.app_context():
            url_entry = URL(
                connection_id=self.connection_id,
                url=url
            )
            db.session.add(url_entry)
        
        return file_path, file_hash, content


def process_packet(command, parts, handler, app):
    file_path = None
    file_hash = None
    content = None
    
    try:
        if command == "DW" and len(parts) >= 3:
            file_path, file_hash, content = handler.handle_dw(parts[1], parts[2])
        
        elif command == "PE" and len(parts) >= 4:
            file_path, file_hash, content = handler.handle_pe(parts[1], parts[2], parts[3])
        
        elif command == "script" and len(parts) >= 4:
            file_path, file_hash, content = handler.handle_script(parts[1], parts[2], parts[3])
        
        elif command == "LN" and len(parts) >= 3:
            file_path, file_hash, content = handler.handle_ln(parts[1], parts[2])
        
        else:
            return
        
        with app.app_context():
            log = PacketLog(
                target_id=handler.target.id,
                connection_id=handler.connection_id,
                ip=handler.target.ip,
                command=command,
                content=content,
                file_hash=file_hash,
                file_path=str(file_path) if file_path else None
            )
            db.session.add(log)
            db.session.commit()
    
    except Exception:
        pass