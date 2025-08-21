import os, time
from .agent_runtime import get_agents
from .agent_lineage import record_lineage
from .marketplace_auto import auto_list_agents
from .sandbox import run_agent_file

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXAMPLES_DIR = os.path.join(BASE_DIR, "examples")

def beast_generate(top_n=3, auto_list=True):
    agents = sorted(get_agents(), key=lambda a: a.score, reverse=True)[:top_n]
    for agent in agents:
        ts = int(time.time())
        new_name = f"{os.path.splitext(agent.name)[0]}_beast_{ts}.py"
        dst = os.path.join(EXAMPLES_DIR, new_name)
        try:
            with open(agent.path) as f_src, open(dst, "w") as f_dst:
                code = f_src.read()
                f_dst.write(code)
                f_dst.write(f"\n# === Beast Signature ===\n")
                f_dst.write(f"def beast_generation():\n    return {ts}\n")
            print(f"[BeastMode] Created {new_name} from {agent.name}")
            # Record lineage
            record_lineage(agent.name, new_name)
        except Exception as e:
            print(f"[BeastMode] Failed for {agent.name}: {e}")
    # Auto-list new beast agents
    if auto_list:
        auto_list_agents(top_n=top_n)
