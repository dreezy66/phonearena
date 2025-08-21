import asyncio
import time
from .agent_runtime import get_agents, cmd_repair_agent
from .beast_mode_auto import beast_generate
from .marketplace_auto import auto_list_agents

async def continuous_beast_mode(cycle_delay=30, top_n=3):
    """
    Continuously runs Beast Mode, repairs, and auto-lists agents.
    cycle_delay: seconds between cycles
    top_n: number of top agents to evolve each cycle
    """
    while True:
        print(f"[Scheduler] Starting Beast Mode cycle at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        agents = get_agents()
        # Repair failed agents
        for agent in agents:
            if agent.last_rc != 0:
                cmd_repair_agent(agent)
        # Run Beast Mode generation
        beast_generate(top_n=top_n, auto_list=True)
        print(f"[Scheduler] Cycle complete. Waiting {cycle_delay}s before next cycle...\n")
        await asyncio.sleep(cycle_delay)

def run_scheduler(cycle_delay=30, top_n=3):
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(continuous_beast_mode(cycle_delay, top_n))
    except KeyboardInterrupt:
        print("[Scheduler] Scheduler stopped manually.")
