import asyncio
from .agent_async import run_agent_async
from .snapshot import save_snapshot
from .logger import log_event
from .agent_runtime import get_agents

async def run_all_agents():
    agents = get_agents()
    for agent in agents:
        name, rc = await run_agent_async(agent)
        log_event("agent_run", f"{name} executed with RC={rc}")
    save_snapshot()
