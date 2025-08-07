import asyncio
from typing import Dict, Any

from . import mcquery

# Custom exception for clearer error handling in the controller
class ConnectionError(Exception):
    pass

# --- Main Profiler Logic ---

async def profile_server(host: str, port: int, timeout: int = 5) -> Dict[str, Any]:
    """
    Performs a comprehensive status ping using the UDP query protocol.
    Note: This method may not work if the server does not have 'enable-query' set to true.
    """
    try:
        # mcquery is synchronous, so we run it in a thread pool to avoid blocking asyncio event loop
        query_data = await asyncio.to_thread(mcquery.query, host, port, timeout)

        # Transform the data to a format consistent with the UI's expectations
        return {
            "online": True,
            "host": host,
            "port": port,
            "version": {"name": query_data.get("version", "N/A")},
            "players": {
                "online": query_data.get("num_players", 0),
                "max": query_data.get("max_players", 0),
                "list": query_data.get("players", [])
            },
            "motd": query_data.get("motd", "N/A"),
            "type": query_data.get("plugins", "N/A") != "N/A" and "Plugin Host" or "Vanilla/Unknown",
            "raw": query_data
        }
    except Exception as e:
        # Catch any exception from the query (e.g., socket.timeout) and wrap it
        raise ConnectionError(f"Failed to query {host}:{port}. Is 'enable-query' set to true in server.properties? Error: {e}")
