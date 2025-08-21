import os, json, time, shutil
from .agent_runtime import get_agents, Agent
from pathlib import Path

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PATTERNS_FILE = os.path.join(BASE, "agent_data", "patterns.json")
AGENTS_DIR = os.path.join(BASE, "agents")

# Ensure patterns.json exists
if not os.path.exists(PATTERNS_FILE):
    with open(PATTERNS_FILE, "w") as f:
        json.dump({}, f)

def load_patterns():
    with open(PATTERNS_FILE) as f:
        return json.load(f)

def save_patterns(patterns):
    with open(PATTERNS_FILE, "w") as f:
        json.dump(patterns, f, indent=2)

def evolve_agent(agent: Agent):
    """
    Generate a new version of the agent using learned patterns
    """
    patterns = load_patterns()
    parent_name = agent.name
    ts = int(time.time())
    child_name = f"{parent_name}_beast_{ts}.py"
    child_path = os.path.join(AGENTS_DIR, child_name)
    
    try:
        with open(agent.path) as f:
            src = f.read()
        
        # Inject patterns if any
        for pat_name, pat_code in patterns.items():
            src += f"\n# Pattern: {pat_name}\n{pat_code}\n"
        
        # Save new child agent
        with open(child_path, "w") as f:
            f.write(src)
        
        # Track lineage
        lineage_file = os.path.join(AGENTS_DIR, "lineage.json")
        lineage = {}
        if os.path.exists(lineage_file):
            with open(lineage_file) as f:
                lineage = json.load(f)
        lineage[child_name] = {"parent": parent_name, "created": ts}
        with open(lineage_file, "w") as f:
            json.dump(lineage, f, indent=2)
        
        print(f"[BeastMode] Evolved {parent_name} -> {child_name}")
        return child_name
    except Exception as e:
        print(f"[BeastMode] Evolution failed for {agent.name}: {e}")
        return None

def beast_mode_cycle(top_n=3):
    agents = sorted(get_agents(), key=lambda a: a.score, reverse=True)[:top_n]
    new_agents = []
    for agent in agents:
        child = evolve_agent(agent)
        if child:
            new_agents.append(child)
    return new_agents

def learn_pattern(agent: Agent, pattern_name: str, code_snippet: str):
    """
    Save high-scoring code patterns from successful agents
    """
    patterns = load_patterns()
    patterns[pattern_name] = code_snippet
    save_patterns(patterns)
    print(f"[BeastMode] Learned new pattern: {pattern_name}")
