import asyncio, time
from arena_core.agent_runtime import get_agents, cmd_repair_agent
from arena_core.ecosystem import ecosystem_cycle

AUTO_CYCLE_INTERVAL = 300  # seconds (5 minutes)

async def auto_beast_mode(top_n=3, interval=AUTO_CYCLE_INTERVAL):
    print(f"[BeastMode] Starting auto-cycle every {interval} seconds...")
    while True:
        agents = get_agents()
        print("[BeastMode] Running ecosystem cycle...")
        await ecosystem_cycle(agents[:top_n])
        print(f"[BeastMode] Cycle complete. Next cycle in {interval} seconds.")
        await asyncio.sleep(interval)

def start_auto_beast():
    try:
        asyncio.get_event_loop().run_until_complete(auto_beast_mode())
    except KeyboardInterrupt:
        print("[BeastMode] Auto-beast terminated by user.")
