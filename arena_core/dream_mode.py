from .agent_runtime import get_agents

def dream_mode_simulation():
    print("[DreamMode] Running offline agent experiments...")
    agents = get_agents()
    for a in agents:
        print(f"[DreamMode] Simulated run: {a.name} score +5")
        a.score += 5
