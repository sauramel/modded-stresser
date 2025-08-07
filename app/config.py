import os
import socket
import uuid

# --- General Config ---
MODE = os.getenv("MODE", "controller") # 'controller' or 'actor'

# --- Controller Config ---
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = int(os.getenv("LISTEN_PORT", 8000))
API_KEY = os.getenv("API_KEY", "you-should-really-change-this")

# --- Actor Config ---
# Use the container's hostname for a predictable, unique ID.
# Falls back to a random UUID if hostname is not available.
try:
    ACTOR_ID = os.getenv("ACTOR_ID", socket.gethostname())
except Exception:
    ACTOR_ID = os.getenv("ACTOR_ID", f"actor-{uuid.uuid4().hex[:8]}")

CONTROLLER_HOST = os.getenv("CONTROLLER_HOST", "http://localhost:8000")
POLL_INTERVAL = 5 # Seconds between polling the controller for tasks

# --- Default Task Config ---
TARGET_HOST = os.getenv("TARGET_HOST", "localhost")
TARGET_PORT = int(os.getenv("TARGET_PORT", 25565))
THREADS = int(os.getenv("THREADS", 100))
DURATION = int(os.getenv("DURATION", 30))
