#!/usr/bin/env python3
import importlib
def run():
    try:
        ar = importlib.import_module("arena_core.agent_runtime")
        if hasattr(ar, "cmd_score_agents"):
            ar.cmd_score_agents()
            return True, "Scoring executed"
        return False, "cmd_score_agents missing"
    except Exception as e:
        return False, str(e)
