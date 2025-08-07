import socket
import struct
import json
import asyncio
from typing import Dict, Any

# --- Protocol Utilities (from former stress.py) ---

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

def pack_string(value):
    return pack_varint(len(value)) + value.encode('utf-8')

def pack_packet(packet_id, data):
    data = pack_varint(packet_id) + data
    return pack_varint(len(data)) + data

def read_varint_from_stream(stream):
    number = 0
    shift = 0
    while True:
        byte = stream.read(1)
        if not byte:
            raise ConnectionError("Socket closed while reading VarInt")
        byte = ord(byte)
        number |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return number

def read_string_from_stream(stream):
    length = read_varint_from_stream(stream)
    return stream.read(length)

# --- Main Profiler Logic ---

async def profile_server(host: str, port: int, timeout: int = 5) -> Dict[str, Any]:
    """
    Performs a comprehensive status ping to identify server type, version, and mods.
    """
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
        raise ConnectionError(f"Could not connect to {host}:{port}: {e}")

    try:
        # 1. Handshake
        handshake_data = pack_varint(0) + pack_varint(758) + pack_string(host) + struct.pack(">H", port) + pack_varint(1)
        writer.write(pack_packet(0x00, handshake_data))
        await writer.drain()

        # 2. Status Request
        writer.write(pack_packet(0x00, b''))
        await writer.drain()

        # 3. Read Response
        # Use a buffered reader to handle the data stream properly
        buffered_reader = asyncio.StreamReader()
        while True:
            data = await reader.read(4096)
            if not data:
                break
            buffered_reader.feed_data(data)
        
        # Create a file-like object for our VarInt/String readers
        response_stream = buffered_reader
        
        packet_length = read_varint_from_stream(response_stream)
        packet_id = read_varint_from_stream(response_stream)

        if packet_id != 0x00:
            raise ConnectionError(f"Invalid status response packet ID: {packet_id}")

        json_response_bytes = read_string_from_stream(response_stream)
        data = json.loads(json_response_bytes)

        # 4. Analyze and Format Response
        profile = {
            "online": True,
            "host": host,
            "port": port,
            "version": data.get("version", {}),
            "players": data.get("players", {}),
            "motd": data.get("description", {}).get("text", ""),
            "favicon": data.get("favicon"),
            "type": "Vanilla",
            "mods": []
        }

        if 'modinfo' in data and data['modinfo'].get('type') == 'FML':
            profile['type'] = 'Forge'
            profile['mods'] = data['modinfo'].get('modList', [])
        elif 'fabric' in data: # Hypothetical check for Fabric
            profile['type'] = 'Fabric'
            profile['mods'] = data.get('fabric', {}).get('mods', [])

        return profile

    except (ConnectionError, IncompleteReadError, Exception) as e:
        raise ConnectionError(f"Failed during profiling: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

class IncompleteReadError(Exception):
    pass
