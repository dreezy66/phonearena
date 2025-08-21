import time, os
from .agent_runtime import get_agents

def visualize_beast_cycle(top_n=5):
    agents = sorted(get_agents(), key=lambda a: a.score, reverse=True)[:top_n]
    print("=== Beast Mode Visual ===")
    for agent in agents:
        print(f"{agent.name} | Score: {agent.score} | Last Run: {agent.last_rc}")
        print("-"*40)
