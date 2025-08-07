import socket
import struct
import json
import asyncio
from typing import Dict, Any

# Custom exception for clearer error handling in the controller
class ConnectionError(Exception):
    pass

# --- Asynchronous Protocol Utilities ---

async def read_varint(stream: asyncio.StreamReader) -> int:
    """Reads a VarInt from an asyncio stream."""
    number = 0
    shift = 0
    for i in range(5): # Max 5 bytes for a 32-bit VarInt
        byte = await stream.read(1)
        if not byte:
            raise asyncio.IncompleteReadError("Socket closed while reading VarInt", None)
        byte = ord(byte)
        number |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return number
        shift += 7
    raise ValueError("VarInt is too big")

async def read_string(stream: asyncio.StreamReader) -> bytes:
    """Reads a length-prefixed string from an asyncio stream."""
    length = await read_varint(stream)
    if length < 0:
        raise ValueError("Negative string length received")
    if length == 0:
        return b''
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
    encoded_value = value.encode('utf-8')
    return pack_varint(len(encoded_value)) + encoded_value

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
        # Use a timeout for the connection itself
        future = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(future, timeout=timeout)
    except asyncio.TimeoutError:
        raise ConnectionError(f"Connection to {host}:{port} timed out after {timeout}s.")
    except ConnectionRefusedError:
        raise ConnectionError(f"Connection refused by {host}:{port}.")
    except OSError as e:
        raise ConnectionError(f"Could not connect to {host}:{port}: {e.strerror}")
    except Exception as e:
        raise ConnectionError(f"An unexpected error occurred while connecting: {e}")

    try:
        # 1. Handshake
        # Protocol version -1 indicates status request
        handshake_data = pack_varint(-1) + pack_string(host) + struct.pack(">H", port) + pack_varint(1)
        writer.write(pack_packet(0x00, handshake_data))
        await writer.drain()

        # 2. Status Request
        writer.write(pack_packet(0x00, b''))
        await writer.drain()

        # 3. Read Response
        # Set a timeout for reading the response
        async def read_data():
            _packet_length = await read_varint(reader)
            packet_id = await read_varint(reader)

            if packet_id != 0x00:
                raise ConnectionError(f"Invalid status response packet ID: {packet_id}")

            json_response_bytes = await read_string(reader)
            return json.loads(json_response_bytes)

        data = await asyncio.wait_for(read_data(), timeout=timeout)

        # 4. Analyze and Format Response
        profile = {
            "online": True,
            "host": host,
            "port": port,
            "version": data.get("version", {}),
            "players": data.get("players", {}),
            "motd": data.get("description", {}).get("text", "") or str(data.get("description", "")),
            "favicon": data.get("favicon"),
            "type": "Vanilla",
            "mods": []
        }

        # Check for Forge mod list
        if 'modinfo' in data and data['modinfo'].get('type') == 'FML':
            profile['type'] = 'Forge'
            profile['mods'] = data['modinfo'].get('modList', [])
        # Check for Fabric mod list (based on common practice)
        elif 'fabric' in data.get('version', {}).get('name', '').lower():
            profile['type'] = 'Fabric'
        
        return profile

    except (asyncio.IncompleteReadError, ValueError, struct.error) as e:
        raise ConnectionError(f"Failed to parse server response: {e}")
    except asyncio.TimeoutError:
        raise ConnectionError(f"Server did not respond in time.")
    except Exception as e:
        raise ConnectionError(f"An unknown error occurred during profiling: {e}")
    finally:
        if writer:
            writer.close()
            await writer.wait_closed()
