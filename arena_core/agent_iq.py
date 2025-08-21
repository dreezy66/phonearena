# agent_iq.py — computes a multi-dimensional IQ score for agents
from arena_core.agent_runtime import get_agents
from arena_core.agent_memory import load_memory

def compute_iq(agent):
    """
    Returns an IQ score (0-100) based on multiple factors
    """
    score = 0

    # Base runtime score
    score += getattr(agent, "score", 0) * 0.4

    # Memory usage and past learning
    mem = load_memory(agent.name)
    mem_bonus = min(len(mem.get("top_snippets", [])), 20)
    score += mem_bonus * 1.5

    # Error resilience (lower last_err improves IQ)
    err_penalty = 10 if getattr(agent, "last_err", "") else 0
    score += max(0, 20 - err_penalty)

    # Parent lineage bonus
    if getattr(agent, "parent", None):
        score += 5

    # Cap at 100
    return min(round(score), 100)

def analyze_agents(top_n=5):
    """
    Analyze all agents and return top N by IQ
    """
    agents = get_agents()
    for a in agents:
        a.iq = compute_iq(a)
    sorted_agents = sorted(agents, key=lambda x: getattr(x, "iq", 0), reverse=True)
    return sorted_agents[:top_n]
