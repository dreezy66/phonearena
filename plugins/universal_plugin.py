DESCRIPTION = "Universal plugin for agent improvement."

import asyncio, time
from arena_core.agent_runtime import get_agents

async def run_plugin(input_data=None):
    print("[universal_plugin] Improving all agents...")
    agents = get_agents()
    for agent in agents:
        print(f"[universal_plugin] Agent: {agent.name}, Score: {agent.score}")
        # Example: append timestamp to agent file
        try:
            with open(agent.path, "a") as f:
                f.write(f"\n# Improved by universal_plugin at {int(time.time())}\n")
        except Exception as e:
            print(f"[universal_plugin] Failed to modify {agent.name}: {e}")
    await asyncio.sleep(1)
    print("[universal_plugin] All agents processed.")
