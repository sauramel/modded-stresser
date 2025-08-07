import time
import requests
import random
import threading
import os
import socket
from datetime import datetime
from typing import Dict, Any, List

from .exploits import get_exploit_by_id

# --- Configuration ---
CONTROLLER_HOST = os.getenv("CONTROLLER_HOST", "http://localhost:8000")
ACTOR_ID = os.getenv("ACTOR_ID") or socket.gethostname()
LOG_BATCH_INTERVAL = 2.0  # seconds
LOG_BATCH_SIZE = 20

# --- State ---
log_batch: List[Dict[str, Any]] = []
log_batch_lock = threading.Lock()
stop_event = threading.Event()

# --- Logging ---
def send_log_batch():
    """Sends the current log batch to the controller."""
    global log_batch
    with log_batch_lock:
        if not log_batch:
            return
        try:
            requests.post(f"{CONTROLLER_HOST}/log", json=log_batch)
            log_batch = [] # Clear batch on success
        except requests.RequestException as e:
            print(f"[{datetime.utcnow().isoformat()}] [ERROR] Could not send logs to controller: {e}")

def log_to_controller(level: str, message: str):
    """Adds a log entry to the batch."""
    log_entry = {
        "actor_id": ACTOR_ID,
        "level": level.upper(),
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    with log_batch_lock:
        log_batch.append(log_entry)
        if len(log_batch) >= LOG_BATCH_SIZE:
            # To avoid holding the lock for too long, we send in a new thread
            threading.Thread(target=send_log_batch, daemon=True).start()

def periodic_log_sender():
    """Periodically sends log batches regardless of size."""
    while not stop_event.is_set():
        stop_event.wait(LOG_BATCH_INTERVAL)
        send_log_batch()

# --- Task Execution ---
def run_task_thread(task_config: Dict[str, Any]):
    """The function executed by each attack thread."""
    exploit_id = task_config.get("exploit")
    exploit_class = get_exploit_by_id(exploit_id)
    
    if not exploit_class:
        log_to_controller("error", f"Exploit '{exploit_id}' not found on this actor.")
        return

    def log_callback(log_data: Dict[str, Any]):
        log_to_controller(log_data.get("level", "info"), log_data.get("message", ""))

    try:
        exploit_instance = exploit_class(
            target_host=task_config["host"],
            target_port=task_config["port"],
            duration=task_config["duration"],
            **task_config.get("exploit_args", {})
        )
        exploit_instance.run(log_callback)
    except Exception as e:
        log_to_controller("error", f"Thread crashed: {e}")

def execute_task(task_config: Dict[str, Any]):
    """Starts and manages the attack threads for a given task."""
    threads = []
    num_threads = task_config.get("threads", 1)
    duration = task_config.get("duration", 60)
    exploit_name = task_config.get("exploit", "unknown")

    log_to_controller("system", f"Starting task '{exploit_name}' with {num_threads} threads for {duration}s.")
    
    start_time = time.time()
    
    while time.time() - start_time < duration:
        # Clean up finished threads
        threads = [t for t in threads if t.is_alive()]

        # Start new threads if below the limit
        if len(threads) < num_threads:
            thread = threading.Thread(target=run_task_thread, args=(task_config,), daemon=True)
            thread.start()
            threads.append(thread)
        
        time.sleep(0.01) # Small sleep to prevent busy-waiting

    log_to_controller("system", "Task duration finished. Waiting for threads to complete...")
    for thread in threads:
        thread.join(timeout=5.0) # Give threads a moment to finish gracefully
    log_to_controller("success", "Task complete.")


# --- Main Actor Loop ---
def run():
    """The main entry point for the actor."""
    log_to_controller("system", f"Actor {ACTOR_ID} starting up.")
    
    # Start the periodic log sender thread
    log_sender_thread = threading.Thread(target=periodic_log_sender, daemon=True)
    log_sender_thread.start()

    while True:
        try:
            # Jitter: Add a random delay (e.g., 0-2 seconds) to the polling interval
            # to prevent all actors from hitting the controller at the exact same time.
            jitter = random.uniform(0, 2)
            time.sleep(3 + jitter)

            response = requests.get(f"{CONTROLLER_HOST}/task", params={"actor_id": ACTOR_ID}, timeout=5)
            response.raise_for_status()
            task = response.json()

            if task.get("exploit") != "idle":
                execute_task(task)

        except requests.RequestException as e:
            log_to_controller("error", f"Cannot reach controller: {e}")
        except Exception as e:
            log_to_controller("error", f"An unexpected error occurred in main loop: {e}")
        finally:
            # Ensure any remaining logs are sent after a task or error
            send_log_batch()
