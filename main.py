import os
import uvicorn
from app.config import MODE, LISTEN_PORT
from app.actor import actor_loop

if __name__ == "__main__":
    if MODE == "controller":
        print(f"Starting in CONTROLLER mode, listening on port {LISTEN_PORT}...")
        # When running in Docker, it's crucial to bind to 0.0.0.0
        uvicorn.run("app.controller:app", host="0.0.0.0", port=LISTEN_PORT, reload=False)
    elif MODE == "actor":
        print("Starting in ACTOR mode...")
        actor_loop()
    else:
        print(f"Unknown MODE: '{MODE}'. Set MODE environment variable to 'controller' or 'actor'.")
