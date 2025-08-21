import os, time, shutil, json
from .agent_runtime import get_agents, Agent

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AGENTS_DIR = os.path.join(BASE, "agents")
LINEAGE_FILE = os.path.join(BASE, "agent_data", "lineage.json")

def _load_lineage():
    if os.path.exists(LINEAGE_FILE):
        with open(LINEAGE_FILE) as f:
            return json.load(f)
    return {}

def _save_lineage(lineage):
    os.makedirs(os.path.dirname(LINEAGE_FILE), exist_ok=True)
    with open(LINEAGE_FILE, "w") as f:
        json.dump(lineage, f, indent=2)

def beast_mode_evolve(top_n=3):
    agents = sorted(get_agents(), key=lambda a: a.score, reverse=True)[:top_n]
    lineage = _load_lineage()

    for agent in agents:
        ts = int(time.time())
        new_name = f"{os.path.splitext(agent.name)[0]}_beast_{ts}.py"
        dst_path = os.path.join(AGENTS_DIR, new_name)

        # Copy agent source
        shutil.copy(agent.path, dst_path)

        # Append evolution signature
        with open(dst_path, "a") as f:
            f.write(f"\n# === Beast DNA signature ===\n")
            f.write(f"def beast_generation():\n    return {ts}\n")

        print(f"[BeastMode] Created evolved agent: {new_name}")

        # Track lineage
        lineage[new_name] = {
            "parent": agent.name,
            "score": agent.score,
            "created_at": ts
        }

    _save_lineage(lineage)
    print("[BeastMode] Lineage updated.")
