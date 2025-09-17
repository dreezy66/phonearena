#!/usr/bin/env python3
from core.phonearena_core import discover_agents, try_repair_agent
from core.phonearena_core import run_agent_in_process
import os
def run(index:int):
    agents = discover_agents()
    if not agents or index < 0 or index >= len(agents):
        return False, "Invalid index"
    path, module = agents[index]
    # Try in-process run for diagnostics
    ok, out = run_agent_in_process(module)
    repair_ok, repair_msg = try_repair_agent(os.path.splitext(os.path.basename(path))[0])
    return True, {"run_ok": ok, "run_out": out, "repair": (repair_ok, repair_msg)}
