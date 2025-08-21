import os, time
from arena_core.agent_runtime import get_agents, cmd_score_agents
from arena_core.marketplace import list_marketplace

def dashboard():
    while True:
        os.system("clear")
        agents = get_agents()
        top_agents = sorted(agents, key=lambda a: a.score, reverse=True)[:5]
        print("=== PhoneArena AI Dev Dashboard ===")
        print(f"Total Agents: {len(agents)}")
        print("\n--- Top Agents ---")
        for a in top_agents:
            print(f"{a.name} | Score: {a.score} | Last rc: {a.last_rc}")
        print("\n--- Marketplace Preview ---")
        list_marketplace()
        print("\nOptions: ")
        print("1) Score all agents")
        print("2) Run ecosystem cycle")
        print("3) Refresh dashboard")
        print("0) Exit dashboard")
        choice = input("> ").strip()
        if choice == "0":
            break
        elif choice == "1":
            cmd_score_agents()
            input("Scoring complete. Press Enter to continue...")
        elif choice == "2":
            from arena_core.ecosystem import ecosystem_cycle
            import asyncio
            asyncio.get_event_loop().run_until_complete(ecosystem_cycle(agents))
            input("Ecosystem cycle complete. Press Enter to continue...")
        elif choice == "3":
            continue
        else:
            print("Invalid choice.")
            time.sleep(1)

