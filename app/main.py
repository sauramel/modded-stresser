import sys
from . import config

def run_controller():
    """Starts the FastAPI controller server."""
    import uvicorn
    from .controller import app  # Late import to avoid issues
    print(f"Starting controller server on {config.LISTEN_HOST}:{config.LISTEN_PORT}")
    uvicorn.run(app, host=config.LISTEN_HOST, port=config.LISTEN_PORT)

def run_actor():
    """Starts the actor process."""
    from .actor import actor_loop, log_to_controller # Late import
    print(f"Starting actor with ID: {config.ACTOR_ID}")
    print(f"Controller URL: {config.CONTROLLER_HOST}")
    
    # Redirect stdout/stderr to the controller's logging endpoint
    class ControllerLog:
        def write(self, message):
            if message.strip():
                log_to_controller({"level": "ACTOR_OUT", "message": message.strip()})
        
        def flush(self):
            pass

    sys.stdout = ControllerLog()
    sys.stderr = ControllerLog()

    try:
        actor_loop()
    except Exception as e:
        # Final attempt to log a critical failure
        try:
            log_to_controller({"level": "FATAL", "message": f"Actor {config.ACTOR_ID} crashed: {e}"})
        except:
            # If logging fails, print to original stderr
            print(f"Actor {config.ACTOR_ID} crashed and could not log to controller: {e}", file=sys.__stderr__)
        sys.exit(1)


if __name__ == "__main__":
    if config.MODE == "controller":
        run_controller()
    elif config.MODE == "actor":
        run_actor()
    else:
        print(f"Unknown mode: '{config.MODE}'. Must be 'controller' or 'actor'.", file=sys.stderr)
        sys.exit(1)
