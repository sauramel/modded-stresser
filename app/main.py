import os
import uvicorn
import sys
from pathlib import Path

# Add the project root to the path.
# This resolves "ImportError: attempted relative import with no known parent package"
# by allowing Python to find the 'app' package for absolute imports.
# The traceback shows the script is at /app/app/main.py, so we add /app to the path.
file_path = Path(__file__).resolve()
root_path = file_path.parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

# Use absolute imports now that the path is configured.
from app import controller
from app import actor

def main():
    mode = os.getenv("MODE", "controller").lower()
    
    if mode == "controller":
        print("Starting in CONTROLLER mode...")
        # Run uvicorn with the app object from the imported controller module.
        uvicorn.run(controller.app, host="0.0.0.0", port=8000)
    elif mode == "actor":
        print("Starting in ACTOR mode...")
        # Run the actor's main loop.
        actor.run()
    else:
        print(f"Unknown mode: {mode}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
