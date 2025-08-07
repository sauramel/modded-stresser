import requests
import time
from .config import CONTROLLER_HOST, ACTOR_ID
from .stress import run_exploit

def log_to_controller(log_data: dict):
    """Sends a log entry to the controller, adding the actor ID."""
    try:
        payload = log_data.copy()
        payload['actor_id'] = ACTOR_ID
        requests.post(f"{CONTROLLER_HOST}/log", json=payload, timeout=2)
    except Exception as e:
        print(f"[ACTOR {ACTOR_ID}] FAILED TO LOG TO CONTROLLER: {e}")
        print(f"[ACTOR {ACTOR_ID}] Original Log: {log_data.get('message')}")


def actor_loop():
    while True:
        try:
            r = requests.get(f"{CONTROLLER_HOST}/task?actor_id={ACTOR_ID}", timeout=10)
            if r.status_code == 200:
                task = r.json()
                exploit_id = task.get("exploit", "idle")

                if exploit_id == "idle":
                    time.sleep(5)
                    continue
                
                # The new run_exploit function takes the whole task dictionary
                run_exploit(
                    task=task,
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
                pass
            time.sleep(5)
