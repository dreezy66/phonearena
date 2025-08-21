import asyncio
from .agent_runtime import get_agents
from .marketplace_auto import auto_list_agents

async def ecosystem_cycle_auto_market(top_n_agents=5):
    """
    Runs the ecosystem cycle and automatically lists top agents in marketplace.
    """
    agents = get_agents()
    print(f"[Ecosystem] Running cycle for {len(agents)} agents...")
    
    # Auto-list top scoring agents
    auto_list_agents(top_n=top_n_agents)
    
    # Print summary of top agents
    top_agents = sorted(agents, key=lambda a: a.score, reverse=True)[:top_n_agents]
    print("[Ecosystem] Top agents this cycle:")
    for a in top_agents:
        print(f"  {a.name} | score={a.score}")
    
    # Optional: return top agents for further hooks/plugins
    return top_agents
