import os, json, time, random
from .agent_runtime import get_agents

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PATTERN_FILE = os.path.join(BASE, "agent_data", "patterns.json")
EXAMPLES_DIR = os.path.join(BASE, "examples")

def load_patterns():
    if os.path.exists(PATTERN_FILE):
        with open(PATTERN_FILE) as f:
            return json.load(f)
    return {}

def save_new_agent(name, code):
    timestamp = int(time.time())
    filename = f"{name}_beastv_{timestamp}.py"
    path = os.path.join(EXAMPLES_DIR, filename)
    with open(path, "w") as f:
        f.write(code)
    print(f"[BeastMode] Created evolved agent: {filename}")
    return filename

def evolve_agents(top_n=3):
    agents = sorted(get_agents(), key=lambda a: a.score, reverse=True)[:top_n]
    patterns = load_patterns()
    for agent in agents:
        snippet = patterns.get(agent.name)
        if snippet:
            try:
                # Simple injection: append pattern to new agent code
                with open(agent.path) as f:
                    original_code = f.read()
                evolved_code = original_code + "\n# === Beast Pattern Injection ===\n" + snippet
                save_new_agent(agent.name, evolved_code)
            except Exception as e:
                print(f"[BeastMode] Failed evolution for {agent.name}: {e}")
