import asyncio
from .agent_runtime import get_agents, cmd_repair_agent, Agent
from .sandbox import run_agent_file, safe_write_json
import time, os, json

AGENT_STATUS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent_data", "agent_status.json"))

async def run_agent(agent: Agent, timeout=8):
    rc, out, err = await asyncio.get_event_loop().run_in_executor(None, run_agent_file, agent.path, timeout)
    agent.last_rc = rc
    agent.last_out = out
    agent.last_err = err
    agent.score = 100 if rc == 0 else 10
    if rc != 0:
        cmd_repair_agent(agent)
    return agent.name, agent.score

async def ecosystem_cycle(agent_list, timeout=8):
    statuses = {}
    for agent in agent_list:
        name, score = await run_agent(agent, timeout)
        statuses[name] = {
            "success": agent.last_rc==0,
            "score": agent.score,
            "out": agent.last_out[:200],
            "err": agent.last_err[:500],
            "path": agent.path
        }
        print(f"[Ecosystem] Agent: {name} | rc={agent.last_rc} | score={agent.score}")
    safe_write_json(AGENT_STATUS_PATH, statuses)
    print("[Ecosystem] Cycle complete; statuses saved.")

def run_ecosystem(max_agents=None):
    agents = get_agents()
    if max_agents:
        agents = agents[:max_agents]
    asyncio.get_event_loop().run_until_complete(ecosystem_cycle(agents))
