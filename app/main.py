import os
    import sys
    import time
    import requests
    import uvicorn
    from . import config, stress

def run_actor():
    """Main loop for the actor process."""
    print(f"Starting actor with ID: {config.ACTOR_ID}")
    print(f"Controller URL: {config.CONTROLLER_HOST}")

    while True:
        try:
            # Poll controller for a task
            response = requests.get(f"{config.CONTROLLER_HOST}/task", params={"actor_id": config.ACTOR_ID}, timeout=5)
            response.raise_for_status()
            task = response.json()

            if task.get("mode") != "idle":
                print(f"Received task: {task}")
                log_to_controller("INFO", f"Starting task: {task['mode']} on {task['host']}:{task['port']} for {task['duration']}s")
                
                stress.run_stress(
                    ip=task['host'],
                    port=task['port'],
                    threads=task['threads'],
                    duration=task['duration'],
                    mode=task['mode']
                )
                
                log_to_controller("INFO", "Task finished.")
            else:
                # print("No active task. Idling...")
                pass

        except requests.exceptions.RequestException as e:
            print(f"Could not connect to controller: {e}", file=sys.stderr)
        except Exception as e:
            print(f"An error occurred: {e}", file=sys.stderr)
            log_to_controller("ERROR", f"An unexpected error occurred: {e}")

        time.sleep(config.POLL_INTERVAL)

def log_to_controller(level, message):
    """Sends a log message to the controller."""
    try:
        payload = {
            "actor_id": config.ACTOR_ID,
            "level": level,
            "message": str(message)
        }
        requests.post(f"{config.CONTROLLER_HOST}/log", json=payload, timeout=2)
    except requests.exceptions.RequestException:
        # If we can't log to the controller, just print locally
        print(f"[LOG-FAIL] {level}: {message}", file=sys.stderr)

# Redirect print statements in the actor to the controller log
class ControllerLog:
    def write(self, message):
        if message.strip(): # Avoid sending empty lines
            log_to_controller("ACTOR_LOG", message.strip())
    
    def flush(self):
        pass # Required for file-like objects

def run_controller():
    """Starts the FastAPI controller server."""
    print(f"Starting controller server on {config.LISTEN_HOST}:{config.LISTEN_PORT}")
    # Import the app instance late to avoid circular dependencies
    from .controller import app
    uvicorn.run(app, host=config.LISTEN_HOST, port=config.LISTEN_PORT)

if __name__ == "__main__":
    if config.MODE == "actor":
        # In actor mode, redirect stdout to our custom logger
        sys.stdout = ControllerLog()
        sys.stderr = ControllerLog()
        run_actor()
    elif config.MODE == "controller":
        run_controller()
    else:
        print(f"Unknown mode: {config.MODE}", file=sys.stderr)
        sys.exit(1)
