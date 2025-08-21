import asyncio
from .agent_runtime import run_agent_file, Agent

async def run_agent_async(agent: Agent, timeout=8):
    loop = asyncio.get_event_loop()
    rc, out, err = await loop.run_in_executor(None, run_agent_file, agent.path, timeout)
    agent.last_rc = rc
    agent.last_out = out
    agent.last_err = err
    return agent.name, rc
