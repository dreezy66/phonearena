from .repair_agent import repair_agent_file
from .agent_runtime import get_agents

def repair_all_agents():
    agents = get_agents()
    for a in agents:
        success = repair_agent_file(a.path)
        print(f"[Repair] {a.name}: {'Fixed' if success else 'Skipped'}")
