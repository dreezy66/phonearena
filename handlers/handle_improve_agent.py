#!/usr/bin/env python3
"""
handle_improve_agent: Run surgical developer on a target project, return candidate patch and tests result.
"""
from core.phonearena_core import discover_agents
import importlib, os, json

def run(target_project):
    # expect agents/surgical_developer.py to exist
    try:
        mod = importlib.import_module("agents.surgical_developer")
    except Exception as e:
        return False, f"Missing surgical_developer: {e}"
    try:
        agent_cls = getattr(mod, "SurgicalDeveloper", None)
        if agent_cls is None:
            return False, "SurgicalDeveloper class not found"
        agent = agent_cls()
        res = agent.act({"type":"improve", "target": target_project, "goal":"make tests pass"})
        return True, res
    except Exception as e:
        return False, str(e)
