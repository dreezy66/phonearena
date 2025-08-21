import os, time, random
from .pattern_manager import get_all_patterns

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXAMPLES_DIR = os.path.join(BASE, "examples")

def inject_patterns(agent_path, agent_name, top_n_patterns=5):
    """
    Inject top patterns from patterns.json into agent source code.
    """
    patterns = get_all_patterns()
    agent_patterns = patterns.get(agent_name, [])
    if not agent_patterns:
        return

    selected_patterns = random.sample(agent_patterns, min(top_n_patterns, len(agent_patterns)))
    try:
        with open(agent_path, "a") as f:
            f.write("\n# === Injected Patterns ===\n")
            for p in selected_patterns:
                f.write(f"{p}\n")
        print(f"[BeastModePatterns] Injected {len(selected_patterns)} patterns into {agent_name}")
    except Exception as e:
        print(f"[BeastModePatterns] Failed to inject patterns into {agent_name}: {e}")

def beast_mode_evolve(agent_list, top_n=3):
    """
    For top N agents, duplicate source, inject patterns, and save as new evolved agent.
    """
    sorted_agents = sorted(agent_list, key=lambda a: a.score, reverse=True)[:top_n]
    for agent in sorted_agents:
        ts = int(time.time())
        new_name = f"{os.path.splitext(agent.name)[0]}_beastv_{ts}.py"
        new_path = os.path.join(EXAMPLES_DIR, new_name)
        try:
            with open(agent.path) as src, open(new_path, "w") as dst:
                dst.write(src.read())
            inject_patterns(new_path, agent.name)
            print(f"[BeastModePatterns] Created evolved agent: {new_name}")
        except Exception as e:
            print(f"[BeastModePatterns] Evolution failed for {agent.name}: {e}")
