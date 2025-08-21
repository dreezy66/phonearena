import os, time
from .agent_runtime import get_agents
from .agent_lineage import register_new_agent
from .marketplace_auto import auto_list_agents

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXAMPLES_DIR = os.path.join(BASE, "examples")

def beast_mode_cycle(top_n=3):
    agents = sorted(get_agents(), key=lambda a: a.score, reverse=True)[:top_n]
    for agent in agents:
        ts = int(time.time())
        new_name = f"{os.path.splitext(agent.name)[0]}_beastv_{ts}.py"
        dst_path = os.path.join(EXAMPLES_DIR, new_name)
        try:
            with open(agent.path) as src, open(dst_path, "w") as dst:
                dst.write(src.read())
                dst.write(f"\n# === Beast Signature ===\n")
                dst.write(f"def beast_generation():\n    return {ts}\n")
            print(f"[BeastMode] Created evolved agent: {new_name}")
            # Register new agent in lineage
            register_new_agent(new_name, parent_name=agent.name, score=agent.score)
        except Exception as e:
            print(f"[BeastMode] Failed to evolve {agent.name}: {e}")
    # Optionally auto-list top N agents
    auto_list_agents(top_n)
