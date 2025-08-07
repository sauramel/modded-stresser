import os

MODE = os.getenv("MODE", "actor")  # 'controller' or 'actor'
CONTROLLER_HOST = os.getenv("CONTROLLER_HOST", "http://localhost:8000")
LISTEN_PORT = int(os.getenv("LISTEN_PORT", "8000"))
TARGET_HOST = os.getenv("TARGET_HOST", "127.0.0.1")
TARGET_PORT = int(os.getenv("TARGET_PORT", "25565"))
THREADS = int(os.getenv("THREADS", "200"))
DURATION = int(os.getenv("DURATION", "30"))
ACTOR_ID = os.getenv("ACTOR_ID", f"actor-{os.urandom(3).hex()}")
API_KEY = os.getenv("API_KEY", "supersecretkey")
