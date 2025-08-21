import os
from arena_core.agent_runtime import get_agents

def show_dashboard():
    agents = get_agents()
    print("=== Marketplace Dashboard ===")
    for a in agents:
        if getattr(a, "can_sell", False):
            print(f"{a.name} | score={a.score}")
    print("Use plugin hooks to mark agents for sale.")
