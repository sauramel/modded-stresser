import threading
import time
from collections import defaultdict
from .exploits import get_exploit_by_id

# --- Statistics and Reporting ---

class StressStats:
    """A thread-safe class to hold statistics for a stress test run."""
    def __init__(self):
        self.lock = threading.Lock()
        self.counters = defaultdict(int)
        self.start_time = time.time()

    def increment(self, key, value=1):
        with self.lock:
            self.counters[key] += value

    def get_stats(self):
        with self.lock:
            stats_copy = self.counters.copy()
        return stats_copy

def reporter_thread(stats, log_callback, stop_time, exploit_name):
    """Periodically reports stats using the provided callback."""
    if not log_callback:
        return
        
    last_reported_stats = stats.get_stats()
    
    while time.time() < stop_time:
        time.sleep(2)
        if time.time() >= stop_time:
            break

        current_stats = stats.get_stats()
        
        # Generic reporting based on common keys
        summary_parts = []
        rate_keys = {
            'packets_sent': 'Packets',
            'joins_succeeded': 'Joins',
            'messages_sent': 'Messages',
            'connections_made': 'Connections'
        }

        for key, name in rate_keys.items():
            if key in current_stats:
                interval_count = current_stats.get(key, 0) - last_reported_stats.get(key, 0)
                rate = round(interval_count / 2, 1)
                summary_parts.append(f"{name}: {current_stats[key]} (~{rate}/s)")

        if 'joins_failed' in current_stats:
            summary_parts.append(f"Fails: {current_stats['joins_failed']}")
        if 'errors' in current_stats:
            summary_parts.append(f"Errors: {current_stats['errors']}")

        if summary_parts:
            log_callback({
                "level": "INFO",
                "message": f"Progress: {', '.join(summary_parts)}"
            })
        
        last_reported_stats = current_stats

# --- Main Orchestrator ---

def run_exploit(task: dict, log_callback=None):
    """
    Initializes and runs the specified exploit module.
    """
    exploit_id = task.get("exploit")
    exploit_module = get_exploit_by_id(exploit_id)

    if not exploit_module:
        if log_callback:
            log_callback({"level": "ERROR", "message": f"Unknown exploit ID '{exploit_id}' received."})
        return

    ip = task['host']
    port = task['port']
    threads = task['threads']
    duration = task['duration']
    exploit_args = task.get('exploit_args', {})

    stop_time = time.time() + duration
    stats = StressStats()
    
    if log_callback:
        log_callback({"level": "SYSTEM", "message": f"Starting exploit '{exploit_module.name}' on {ip}:{port} for {duration}s"})
    
    # Instantiate the exploit with all necessary context
    exploit_instance = exploit_module(
        host=ip,
        port=port,
        stop_time=stop_time,
        stats=stats,
        log_callback=log_callback,
        exploit_args=exploit_args
    )

    worker_threads = []
    for _ in range(threads):
        # The 'run' method of the exploit class contains the worker loop
        thread = threading.Thread(target=exploit_instance.run, daemon=True)
        worker_threads.append(thread)
        thread.start()

    reporter = None
    if log_callback:
        reporter = threading.Thread(target=reporter_thread, args=(stats, log_callback, stop_time, exploit_module.name), daemon=True)
        reporter.start()

    for thread in worker_threads:
        thread.join()

    if reporter:
        reporter.join(timeout=0.1)

    if log_callback:
        final_stats = stats.get_stats()
        elapsed = time.time() - stats.start_time
        
        summary_parts = []
        for key, value in final_stats.items():
            summary_parts.append(f"{key.replace('_', ' ').title()}: {value}")

        log_callback({
            "level": "SUCCESS",
            "message": f"Task finished. Final Stats: {', '.join(summary_parts)}"
        })
