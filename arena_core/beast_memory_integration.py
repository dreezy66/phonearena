# beast_memory_integration.py — smarter Beast Mode with memory & patterns
from arena_core.agent_runtime import get_agents, save_agents
from arena_core.agent_utils import create_mutated_agent
from arena_core.agent_memory import extract_top_snippets, write_memory, read_memory
from arena_core.lineage_tracker import record_lineage
import random, time, os

def beast_mode_smart(top_n=3):
    agents = get_agents()
    # Sort top agents by score
    top_agents = sorted(agents, key=lambda a: getattr(a, "score",0), reverse=True)[:top_n]
    if not top_agents:
        print("[Beast Mode Smart] No top agents found.")
        return []

    new_agents = []
    for a in top_agents:
        # Pull learned code snippets
        snippets = extract_top_snippets(a.name)
        new_agent = create_mutated_agent(a, type(a))
        if new_agent:
            # Inject learned snippets into new agent
            try:
                with open(new_agent.path, "a") as f:
                    for s in snippets:
                        f.write("\n# === Injected snippet ===\n")
                        f.write(s + "\n")
                new_agent.mutation_desc = "beast_smart_cycle"
                record_lineage(new_agent.name, parent=a.name, mutation_desc=new_agent.mutation_desc)
                # Remember in memory
                write_memory(new_agent.name, "injected_snippets", snippets)
            except Exception as e:
                print("[BeastModeSmart] Failed injecting snippets:", e)
            new_agents.append(new_agent)
            print(f"[Beast Mode Smart] Created smarter agent: {new_agent.name}")

    # Persist statuses
    save_agents(agents + new_agents)
    return [n.name for n in new_agents]
