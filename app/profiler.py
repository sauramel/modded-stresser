import socket
import struct
import json
import asyncio
from typing import Dict, Any

# --- Asynchronous Protocol Utilities ---

async def read_varint(stream: asyncio.StreamReader) -> int:
    """Reads a VarInt from an asyncio stream."""
    number = 0
    shift = 0
    while True:
        byte = await stream.read(1)
        if not byte:
            raise asyncio.IncompleteReadError("Socket closed while reading VarInt", None)
        byte = ord(byte)
        number |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
        if shift >= 32: # Prevent infinite loops from malicious data
            raise ValueError("VarInt is too big")
    return number

async def read_string(stream: asyncio.StreamReader) -> bytes:
    """Reads a length-prefixed string from an asyncio stream."""
    length = await read_varint(stream)
    if length < 0:
        raise ValueError("Negative string length received")
    return await stream.readexactly(length)

def pack_varint(value: int) -> bytes:
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

def pack_string(value: str) -> bytes:
    """Packs a string into a VarInt-prefixed byte string."""
    return pack_varint(len(value)) + value.encode('utf-8')

def pack_packet(packet_id: int, data: bytes) -> bytes:
    """Packs data into a full Minecraft protocol packet."""
    data = pack_varint(packet_id) + data
    return pack_varint(len(data)) + data

# --- Main Profiler Logic ---

async def profile_server(host: str, port: int, timeout: int = 5) -> Dict[str, Any]:
    """
    Performs a comprehensive status ping to identify server type, version, and mods.
    """
    reader, writer = None, None
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
        raise ConnectionError(f"Could not connect to {host}:{port}: {e}")

    try:
        # 1. Handshake
        # Protocol version 758 is for 1.18.2, a common modern version.
        handshake_data = pack_varint(0) + pack_varint(758) + pack_string(host) + struct.pack(">H", port) + pack_varint(1)
        writer.write(pack_packet(0x00, handshake_data))
        await writer.drain()

        # 2. Status Request
        writer.write(pack_packet(0x00, b''))
        await writer.drain()

        # 3. Read Response
        _packet_length = await read_varint(reader)
        packet_id = await read_varint(reader)

        if packet_id != 0x00:
            raise ConnectionError(f"Invalid status response packet ID: {packet_id}")

        json_response_bytes = await read_string(reader)
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

        # Check for Forge mod list
        if 'modinfo' in data and data['modinfo'].get('type') == 'FML':
            profile['type'] = 'Forge'
            profile['mods'] = data['modinfo'].get('modList', [])
        # Hypothetical check for Fabric, would need a real server to confirm format
        elif 'fabric' in data:
            profile['type'] = 'Fabric'
            profile['mods'] = data.get('fabric', {}).get('mods', [])

        return profile

    except (asyncio.IncompleteReadError, ConnectionError, ValueError, struct.error, Exception) as e:
        raise ConnectionError(f"Failed during profiling: {e}")
    finally:
        if writer:
            writer.close()
            await writer.wait_closed()
