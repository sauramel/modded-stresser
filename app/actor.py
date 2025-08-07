import requests
import time
from .config import CONTROLLER_HOST, ACTOR_ID
from .stress import run_stress

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
                
                print(f"[ACTOR {ACTOR_ID}] Received task: {mode}")

                # The controller now handles probing, actor just receives data
                mod_data = task.get("mod_data")
                
                run_stress(
                    ip=task['host'],
                    port=task['port'],
                    threads=task['threads'],
                    duration=task['duration'],
                    mode=mode,
                    mod_data=mod_data
                )

                log_payload = {
                    "actor_id": ACTOR_ID,
                    "level": "INFO",
                    "message": f"Finished task: {mode}"
                }
                requests.post(f"{CONTROLLER_HOST}/log", json=log_payload, timeout=5)
            else:
                print(f"[ACTOR {ACTOR_ID}] Error fetching task: {r.status_code}")
                time.sleep(5)
        except Exception as e:
            print(f"[ACTOR {ACTOR_ID}] Exception: {e}")
            try:
                requests.post(f"{CONTROLLER_HOST}/log", json={"actor_id": ACTOR_ID, "level": "ERROR", "message": str(e)}, timeout=5)
            except:
                pass # Suppress errors if controller is unreachable
            time.sleep(5)
