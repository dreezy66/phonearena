# agent_memory.py — persistent memory for agents
import os, json
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MEMORY_DIR = os.path.join(BASE, "agent_data", "memory")
os.makedirs(MEMORY_DIR, exist_ok=True)

def _memory_file(agent_name):
    return os.path.join(MEMORY_DIR, f"{agent_name}.json")

def save_memory(agent_name, data):
    """
    Save agent memory (dict) to JSON file
    """
    try:
        path = _memory_file(agent_name)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[AgentMemory] Failed to save memory for {agent_name}:", e)

def load_memory(agent_name):
    """
    Load agent memory (dict) from JSON file
    """
    path = _memory_file(agent_name)
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        print(f"[AgentMemory] Failed to load memory for {agent_name}:", e)
        return {}

def append_to_memory(agent_name, key, value):
    """
    Append value to list under key
    """
    mem = load_memory(agent_name)
    if key not in mem:
        mem[key] = []
    mem[key].append(value)
    save_memory(agent_name, mem)
