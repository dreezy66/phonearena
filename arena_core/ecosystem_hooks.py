import asyncio
from .agent_runtime import get_agents, cmd_repair_agent, cmd_score_agents
from .plugin_loader import plugin_mgr

async def run_agent_hooks(agent):
    # Run all plugins for the agent
    for plugin in plugin_mgr.plugins:
        await plugin.run(agent.name)

async def ecosystem_autocycle(top_n=5):
    agents = get_agents()
    for agent in agents[:top_n]:
        # Run plugin hooks
        await run_agent_hooks(agent)
        # Auto-score agent
        await asyncio.get_event_loop().run_in_executor(None, cmd_score_agents)
        # Attempt repair if failed
        if agent.last_rc != 0:
            cmd_repair_agent(agent)
    print("[Ecosystem] Auto-cycle complete.")
