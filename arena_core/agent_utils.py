# agent_utils.py — helper utilities for agent selection & mutation
import os, time
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXAMPLES_DIR = os.path.join(BASE, "examples")

def get_top_agents(agent_list, top_n=3):
    try:
        sorted_agents = sorted(agent_list, key=lambda a: getattr(a, "score", 0), reverse=True)
        return sorted_agents[:top_n]
    except Exception:
        return []

def create_mutated_agent(agent, AgentClass):
    """
    Create a mutated copy of agent, return an instance of AgentClass.
    AgentClass is expected to match arena_core.agent_runtime.Agent
    """
    try:
        ts = int(time.time())
        base = os.path.splitext(agent.name)[0]
        new_name = f"{base}_beastv_{ts}.py"
        dst = os.path.join(EXAMPLES_DIR, new_name)
        with open(agent.path, "r") as fh:
            content = fh.read()
        # write safe python (append newline then signature)
        with open(dst, "w") as fh:
            fh.write(content.rstrip() + "\n\n# === Beast signature ===\n")
            fh.write("def beast_generation():\n")
            fh.write(f"    return {ts}\n")
        new_agent = AgentClass(new_name, dst, score=0, parent=agent.name)
        new_agent.mutation_desc = "beast_cycle"
        return new_agent
    except Exception as e:
        print("[agent_utils] failed to create mutated agent:", e)
        return None
