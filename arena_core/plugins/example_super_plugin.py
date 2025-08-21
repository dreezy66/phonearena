import asyncio
from arena_core.agent_runtime import get_agents

async def run(input_data=None):
    print("[example_super_plugin] Running plugin...")
    agents = get_agents()
    for a in agents:
        # Simple demonstration: mark top scoring agent as sellable
        if a.score >= 50:
            a.can_sell = True
            print(f"[example_super_plugin] Agent {a.name} marked as sellable")
    await asyncio.sleep(0.5)
    print("[example_super_plugin] Done")
