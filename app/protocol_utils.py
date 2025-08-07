import struct

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
