import requests
import time
from .config import CONTROLLER_HOST, ACTOR_ID
from .stress import run_stress

def log_to_controller(log_data: dict):
    """Sends a log entry to the controller, adding the actor ID."""
    try:
        payload = log_data.copy()
        payload['actor_id'] = ACTOR_ID
        requests.post(f"{CONTROLLER_HOST}/log", json=payload, timeout=2)
    except Exception as e:
        # If logging to the controller fails, print locally as a fallback.
        print(f"[ACTOR {ACTOR_ID}] FAILED TO LOG TO CONTROLLER: {e}")
        print(f"[ACTOR {ACTOR_ID}] Original Log: {log_data.get('message')}")


def actor_loop():
    while True:
        try:
            r = requests.get(f"{CONTROLLER_HOST}/task?actor_id={ACTOR_ID}", timeout=10)
            if r.status_code == 200:
                task = r.json()
                mode = task.get("mode", "idle")

                if mode == "idle":
                    time.sleep(5)
                    continue
                
                mod_data = task.get("mod_data")
                
                run_stress(
                    ip=task['host'],
                    port=task['port'],
                    threads=task['threads'],
                    duration=task['duration'],
                    mode=mode,
                    mod_data=mod_data,
                    log_callback=log_to_controller
                )

            else:
                print(f"[ACTOR {ACTOR_ID}] Error fetching task: {r.status_code}")
                time.sleep(5)
        except Exception as e:
            print(f"[ACTOR {ACTOR_ID}] Exception in main loop: {e}")
            try:
                log_to_controller({"level": "ERROR", "message": f"Actor main loop error: {e}"})
            except:
                pass # Suppress errors if controller is unreachable
            time.sleep(5)
