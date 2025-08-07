import requests
import time
from .config import CONTROLLER_HOST, ACTOR_ID
from .stress import run_stress, probe_modlist

def actor_loop():
    while True:
        try:
            r = requests.get(f"{CONTROLLER_HOST}/task?actor_id={ACTOR_ID}")
            if r.status_code == 200:
                task = r.json()
                print(f"[ACTOR {ACTOR_ID}] Task: {task}")
                mode = task.get("mode", "login_flood")

                if mode == "idle":
                    print(f"[ACTOR {ACTOR_ID}] Received idle task. Sleeping.")
                    time.sleep(10)
                    continue

                if mode == "modded_probe":
                    probe_modlist(task['host'], task['port'])
                elif mode in ("modded_replay", "login_flood"):
                    run_stress(task['host'], task['port'], task['threads'], task['duration'], use_modlist=(mode=="modded_replay"))

                log_payload = {
                    "actor_id": ACTOR_ID,
                    "event": f"Finished {mode}"
                }
                requests.post(f"{CONTROLLER_HOST}/log", json=log_payload)
            else:
                print(f"[ACTOR {ACTOR_ID}] Error fetching task: {r.status_code}")
                time.sleep(5)
        except Exception as e:
            print(f"[ACTOR {ACTOR_ID}] Exception: {e}")
            try:
                requests.post(f"{CONTROLLER_HOST}/log", json={"actor_id": ACTOR_ID, "error": str(e)})
            except:
                pass
            time.sleep(5)
