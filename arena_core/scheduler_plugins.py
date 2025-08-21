# scheduler_plugins.py — continuous multi-agent loop with dynamic plugin execution
import time
from arena_core.agent_runtime import get_agents, score_agents, beast_mode_sync
from arena_core.plugin_loader import plugin_mgr

def run_plugins(agents=None):
    """
    Execute all loaded plugins for the given agents.
    Each plugin must implement run(data) method.
    """
    if not plugin_mgr.plugins:
        print("[Plugins] No plugins loaded.")
        return

    print(f"[Plugins] Running {len(plugin_mgr.plugins)} plugins...")
    for plugin in plugin_mgr.plugins:
        try:
            plugin.run(agents)
            print(f"[Plugins] Executed: {plugin.name}")
        except Exception as e:
            print(f"[Plugins] Failed {plugin.name}: {e}")

def continuous_loop_plugins(interval=60, top_n=3, repair_on_fail=True):
    """
    interval: seconds between cycles
    top_n: number of top agents to mutate each cycle
    repair_on_fail: attempt repair on failed agents
    """
    print(f"[Scheduler+Plugins] Starting loop: interval={interval}s, top_n={top_n}")
    cycle = 1
    try:
        while True:
            print(f"\n[Scheduler+Plugins] Cycle {cycle} — scoring agents...")
            score_agents(attempt_repair=repair_on_fail)

            print(f"[Scheduler+Plugins] Cycle {cycle} — running Beast Mode on top {top_n} agents...")
            new_agents = beast_mode_sync(top_n=top_n)

            print(f"[Scheduler+Plugins] Cycle {cycle} — running plugins...")
            all_agents = get_agents()
            run_plugins(all_agents)

            if new_agents:
                print(f"[Scheduler+Plugins] New agents: {', '.join(new_agents)}")
            else:
                print("[Scheduler+Plugins] No new agents this cycle.")

            cycle += 1
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[Scheduler+Plugins] Stopped by user.")
    except Exception as e:
        print(f"[Scheduler+Plugins] Error: {e}")
        time.sleep(interval)
        continuous_loop_plugins(interval, top_n, repair_on_fail)

if __name__ == "__main__":
    # default: 60s interval, top 3 agents, auto-repair enabled
    continuous_loop_plugins()
