#!/usr/bin/env python3
from core.phonearena_core import discover_agents, run_agent_best_effort
def run(index: int = None):
    agents = discover_agents()
    if not agents:
        return False, "No agents"
    if index is None:
        return True, [p for p,_ in agents]
    try:
        path,module = agents[index]
        ok,out = run_agent_best_effort(path, module)
        return ok, out
    except Exception as e:
        return False, str(e)
