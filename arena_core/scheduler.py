# scheduler.py — continuous multi-agent management & evolution
import time
from arena_core.agent_runtime import get_agents, score_agents, beast_mode_sync

def continuous_loop(interval=60, top_n=3, repair_on_fail=True):
    """
    interval: seconds between cycles
    top_n: number of top agents to mutate each cycle
    repair_on_fail: attempt repair on failed agents
    """
    print(f"[Scheduler] Starting continuous loop: interval={interval}s, top_n={top_n}")
    cycle = 1
    try:
        while True:
            print(f"\n[Scheduler] Cycle {cycle} — scoring agents...")
            score_agents(attempt_repair=repair_on_fail)
            print(f"[Scheduler] Cycle {cycle} — running Beast Mode on top {top_n} agents...")
            new_agents = beast_mode_sync(top_n=top_n)
            if new_agents:
                print(f"[Scheduler] New agents generated: {', '.join(new_agents)}")
            else:
                print("[Scheduler] No new agents this cycle.")
            cycle += 1
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[Scheduler] Stopped by user.")
    except Exception as e:
        print(f"[Scheduler] Error: {e}")
        time.sleep(interval)
        continuous_loop(interval, top_n, repair_on_fail)

if __name__ == "__main__":
    # default: 60s interval, top 3 agents, auto-repair enabled
    continuous_loop()
