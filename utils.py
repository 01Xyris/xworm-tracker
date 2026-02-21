import hashlib
import random
import string
from datetime import datetime, timedelta
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

def random_str(length=20):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def random_pc_name():
    prefixes = ["PC", "DESKTOP", "LAPTOP", "WORKSTATION"]
    suffixes = ["Work", "Home", "Office", "Admin", "User", "Dev", "Sales", "HR"]
    names = ["John", "Mike", "Sarah", "David", "Lisa", "Tom", "Anna", "Mark"]
    
    templates = [
        f"{random.choice(prefixes)}-{random.choice(suffixes)}",
        f"{random.choice(names)}-{random.choice(prefixes)}",
        f"{random.choice(prefixes)}{random.randint(1, 99)}",
        f"{random.choice(names)}{random.choice(suffixes)}"
    ]
    return random.choice(templates)

def random_os():
    return random.choice(["Windows 10 Pro", "Windows 11 Pro", "Windows 10 Home"])

def random_cpu():
    return random.choice([
        "Intel Core i5-10400",
        "Intel Core i7-10700K",
        "AMD Ryzen 5 3600",
        "AMD Ryzen 7 5800X"
    ])

def random_gpu():
    return random.choice([
        "NVIDIA GeForce GTX 1660",
        "NVIDIA GeForce RTX 3060",
        "AMD Radeon RX 580"
    ])

def random_ram():
    return random.choice(["8 GB", "16 GB", "32 GB"])

def random_antivirus():
    return random.choice([
        "Windows Defender",
        "Avast",
        "AVG",
        "Kaspersky",
        "Norton",
        "McAfee",
        "None"
    ])

def random_bool():
    return random.choice(["True", "False"])

def random_date():
    start_date = datetime.now() - timedelta(days=365)
    random_days = random.randint(0, 365)
    random_date = start_date + timedelta(days=random_days)
    return random_date.strftime("%m/%d/%Y")

def encrypt_data(data, key):
    hashed_key = hashlib.md5(key.encode()).digest()
    cipher = AES.new(hashed_key, AES.MODE_ECB)
    return cipher.encrypt(pad(data, AES.block_size))

def decrypt_data(data, key):
    try:
        hashed_key = hashlib.md5(key.encode()).digest()
        cipher = AES.new(hashed_key, AES.MODE_ECB)
        return unpad(cipher.decrypt(data), AES.block_size)
    except:
        return None

def add_metadata(encrypted_data):
    return f"{len(encrypted_data)}\0".encode() + encrypted_data

def parse_packet(buffer):
    try:
        null_pos = buffer.index(b'\0')
        length = int(buffer[:null_pos])
        if len(buffer) >= null_pos + 1 + length:
            encrypted = buffer[null_pos + 1:null_pos + 1 + length]
            remaining = buffer[null_pos + 1 + length:]
            return encrypted, remaining
        return None, buffer
    except:
        return None, buffer

def generate_info_packet(botid, delimiter):
    tool = delimiter.strip('<>')
    
    if tool == "Violet":
        return (
            f"INFO{delimiter}{random_str()}{delimiter}{random_pc_name()}{delimiter}"
            f"Windows{delimiter}{tool} v{random.choice(['4.5', '4.6', '4.7'])}{delimiter}{random_date()}{delimiter}"
            f"False{delimiter}False{delimiter}False{delimiter}{random_antivirus()}{delimiter}UPDATE NEDDED: System->Run File"
        )
    
    else:
        return (
            f"INFO{delimiter}{random_str()}{delimiter}{random_pc_name()}{delimiter}"
            f"{random_os()}UPDATE NEEDED: Run File{delimiter}{random_date()}{delimiter}"
            f"{random_bool()}{delimiter}{random_bool()}{delimiter}{random_bool()}{delimiter}{random_cpu()}{delimiter}"
            f"{random_gpu()}{delimiter}{random_ram()}{delimiter}{random_antivirus()}{delimiter}{delimiter}{delimiter}{delimiter}"
        )