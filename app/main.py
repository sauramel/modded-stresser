import os
import uvicorn
import sys

def main():
    mode = os.getenv("MODE", "controller").lower()
    
    if mode == "controller":
        print("Starting in CONTROLLER mode...")
        # Ensure the controller module can be found
        from . import controller
        uvicorn.run(controller.app, host="0.0.0.0", port=8000)
    elif mode == "actor":
        print("Starting in ACTOR mode...")
        # Ensure the actor module can be found
        from . import actor
        actor.run()
    else:
        print(f"Unknown mode: {mode}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
