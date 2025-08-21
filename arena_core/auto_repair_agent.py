# auto_repair_agent.py — proactively repairs agents using IQ, memory, and error history
import os, time
from arena_core.agent_runtime import get_agents, save_agents
from arena_core.repair_agent import attempt_repair
from arena_core.agent_iq import compute_iq

def auto_repair_cycle():
    agents = get_agents()
    repaired_agents = []

    for a in agents:
        try:
            # Only target agents with low IQ or recent errors
            iq = getattr(a, "iq", compute_iq(a))
            if iq >= 90 and not getattr(a, "last_err", ""):
                continue

            # Read source
            with open(a.path, "r") as fh:
                src = fh.read()

            # Attempt repair
            newsrc = attempt_repair(src, a.last_err or "")
            if newsrc and newsrc != src:
                ts = int(time.time())
                newname = f"{os.path.splitext(a.name)[0]}_auto_repaired_{ts}.py"
                dst = os.path.join(os.path.dirname(a.path), newname)
                with open(dst, "w") as fh:
                    fh.write(newsrc)
                repaired_agents.append(newname)
                print(f"[AutoRepair] {a.name} repaired -> {newname}")
        except Exception as e:
            print(f"[AutoRepair] Failed for {a.name}: {e}")

    # Persist agent statuses
    save_agents(get_agents())

    return repaired_agents
