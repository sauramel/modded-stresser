import os
import socket
import uuid

# --- General Config ---
MODE = os.getenv("MODE", "controller") # 'controller' or 'actor'

# --- Controller Config ---
LISTEN_HOST = os.getenv("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.getenv("LISTEN_PORT", 8000))
API_KEY = os.getenv("API_KEY", "you-should-really-change-this")

# --- Actor Config ---
def _get_actor_id():
    """
    Determines the actor ID with the following priority:
    1. Environment variable `ACTOR_ID` (for manual execution).
    2. Container hostname (for Docker).
    3. A randomly generated ID as a fallback.
    """
    # 1. Prioritize the environment variable for manual overrides.
    env_id = os.getenv("ACTOR_ID")
    if env_id:
        return env_id

    # 2. Use hostname for automatic ID in containerized environments.
    try:
        hostname = socket.gethostname()
        # Basic check to avoid using a generic hostname like 'localhost'
        if hostname and 'localhost' not in hostname and '127.0.0.1' not in hostname:
            return hostname
    except Exception:
        # Could fail in some restricted environments, so we pass.
        pass

    # 3. Fallback to a random ID if no other identifier is found.
    return f"actor-{uuid.uuid4().hex[:8]}"

ACTOR_ID = _get_actor_id()
CONTROLLER_HOST = os.getenv("CONTROLLER_HOST", "http://localhost:8000")
POLL_INTERVAL = 5 # Seconds between polling the controller for tasks

# --- Default Task Config ---
TARGET_HOST = os.getenv("TARGET_HOST", "localhost")
TARGET_PORT = int(os.getenv("TARGET_PORT", 25565))
THREADS = int(os.getenv("THREADS", 100))
DURATION = int(os.getenv("DURATION", 30))
