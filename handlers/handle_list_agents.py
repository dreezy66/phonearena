#!/usr/bin/env python3
from core.phonearena_core import discover_agents
def run():
    agents = discover_agents()
    if not agents: return "(no agents)"
    return "\n".join([f"[{i+1}] {p} -> {m}" for i,(p,m) in enumerate(agents)])
