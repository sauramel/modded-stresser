import socket
import struct
import random
import time

def query(host: str, port: int, timeout: int = 3):
    """
    Performs a full-stat query on a Minecraft server using the UDP query protocol.
    """
    session_id = random.randint(0, 0xFFFFFFFF) & 0x0F0F0F0F

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        
        # 1. Handshake
        handshake_packet = b'\xFE\xFD\x09' + struct.pack('>l', session_id)
        s.sendto(handshake_packet, (host, port))
        
        response, _ = s.recvfrom(2048)
        
        if response[0] != 0x09 or struct.unpack('>l', response[1:5])[0] != session_id:
            raise ConnectionError("Handshake response was invalid.")
            
        challenge_token_str = response[5:-1] # Null-terminated string
        challenge_token = int(challenge_token_str)

        # 2. Full Stat Request
        stat_packet = b'\xFE\xFD\x00' + struct.pack('>l', session_id) + struct.pack('>l', challenge_token) + b'\x00\x00\x00\x00'
        s.sendto(stat_packet, (host, port))
        
        response, _ = s.recvfrom(4096)

    # 3. Parse Response
    data = response[5:] # Skip magic and session ID
    
    # The data is a series of null-terminated key-value strings, followed by a player list.
    # It starts with 'splitnum' and some padding.
    data = data[11:] # Skip 'splitnum' and padding
    
    parts = data.split(b'\x00\x01player_\x00\x00')
    kvs_raw = parts[0].split(b'\x00')
    
    info = {}
    # The key-value pairs are sequential in the list
    for i in range(0, len(kvs_raw) -1, 2):
        key = kvs_raw[i].decode('utf-8', 'ignore')
        value = kvs_raw[i+1].decode('utf-8', 'ignore')
        if key: # Ensure key is not empty
            info[key] = value

    # Parse players if they exist
    players = []
    if len(parts) > 1 and parts[1]:
        player_raw = parts[1].split(b'\x00')
        for player_name in player_raw:
            if player_name:
                players.append(player_name.decode('utf-8', 'ignore'))
    
    info['players_list'] = players
    info['queried_at'] = time.time()
    
    # Clean up and standardize keys
    return {
        "motd": info.get("hostname", "N/A"),
        "gametype": info.get("gametype", "N/A"),
        "map": info.get("map", "N/A"),
        "num_players": int(info.get("numplayers", 0)),
        "max_players": int(info.get("maxplayers", 0)),
        "hostport": int(info.get("hostport", 0)),
        "version": info.get("version", "N/A"),
        "plugins": info.get("plugins", "N/A"),
        "players": info.get("players_list", [])
    }
