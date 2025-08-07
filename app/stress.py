import threading
import time
from .exploits import get_exploit_by_id

def worker(exploit_instance, end_time, log_callback):
    """The function each thread will execute."""
    while time.time() < end_time:
        try:
            exploit_instance.run(log_callback)
        except Exception as e:
            log_callback({
                "level": "ERROR",
                "message": f"Exploit thread crashed: {e}"
            })
            # Optional: break the loop if a thread fails
            break
        # Optional: add a small delay between runs within a thread
        time.sleep(0.1)

def run_exploit(task: dict, log_callback):
    """
    Initializes and runs the specified exploit with multiple threads.
    """
    exploit_id = task.get("exploit")
    if not exploit_id:
        log_callback({"level": "FATAL", "message": "No exploit ID provided in task."})
        return

    exploit_class = get_exploit_by_id(exploit_id)
    if not exploit_class:
        log_callback({"level": "FATAL", "message": f"Could not find exploit class for ID: {exploit_id}"})
        return

    try:
        # Instantiate the exploit with all necessary parameters
        exploit_instance = exploit_class(
            target_host=task.get("host"),
            target_port=task.get("port"),
            duration=task.get("duration"),
            **task.get("exploit_args", {})
        )
    except Exception as e:
        log_callback({"level": "FATAL", "message": f"Failed to initialize exploit {exploit_id}: {e}"})
        return

    threads = []
    num_threads = task.get("threads", 1)
    duration = task.get("duration", 60)
    end_time = time.time() + duration

    log_callback({
        "level": "SYSTEM",
        "message": f"Starting {num_threads} threads for exploit '{exploit_instance.name}' for {duration} seconds."
    })

    for _ in range(num_threads):
        thread = threading.Thread(target=worker, args=(exploit_instance, end_time, log_callback))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    log_callback({
        "level": "SYSTEM",
        "message": f"Exploit '{exploit_instance.name}' has finished."
    })
