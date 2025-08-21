# beast_scheduler.py — asynchronous, continuous Beast Mode
import threading, time
from arena_core.beast_memory_integration import beast_mode_smart

_scheduler_thread = None
_stop_flag = False

def _scheduler_loop(interval=30, top_n=3):
    global _stop_flag
    while not _stop_flag:
        try:
            print("[BeastScheduler] Running scheduled Beast Mode cycle...")
            new_agents = beast_mode_smart(top_n=top_n)
            if new_agents:
                print(f"[BeastScheduler] New agents created: {', '.join(new_agents)}")
        except Exception as e:
            print("[BeastScheduler] Error during Beast Mode cycle:", e)
        time.sleep(interval)

def start_scheduler(interval=30, top_n=3):
    global _scheduler_thread, _stop_flag
    _stop_flag = False
    if _scheduler_thread and _scheduler_thread.is_alive():
        print("[BeastScheduler] Scheduler already running.")
        return
    _scheduler_thread = threading.Thread(target=_scheduler_loop, args=(interval, top_n), daemon=True)
    _scheduler_thread.start()
    print("[BeastScheduler] Scheduler started.")

def stop_scheduler():
    global _stop_flag
    _stop_flag = True
    print("[BeastScheduler] Scheduler stopped.")
