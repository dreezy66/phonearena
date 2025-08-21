#!/usr/bin/env python3
# studio/main.py — Synchronous Studio CLI (patched)

import sys, os, json, time

# Ensure parent path is on sys.path so `arena_core` is importable
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Defensive imports (core runtime functions are synchronous)
try:
    from arena_core.agent_runtime import get_agents, cmd_score_agents, beast_mode_cycle, repair_agent_by_name
except Exception as e:
    get_agents = None
    cmd_score_agents = None
    beast_mode_cycle = None
    repair_agent_by_name = None
    _AR_RUNTIME_ERR = e

try:
    from arena_core.plugin_loader import plugin_mgr
except Exception:
    plugin_mgr = None

try:
    from arena_core.lineage_tracker import read_lineage
except Exception:
    read_lineage = None

try:
    from arena_core.marketplace_auto import auto_list_agents
except Exception:
    auto_list_agents = None

try:
    from arena_core.sandbox import run_agent_file
except Exception:
    run_agent_file = None

AGENT_DATA_DIR = os.path.join(BASE_DIR, "agent_data")
os.makedirs(AGENT_DATA_DIR, exist_ok=True)

def check_runtime():
    if get_agents is None:
        print("ERROR: arena_core.agent_runtime not available:", getattr(globals(), "_AR_RUNTIME_ERR", "unknown"))
        return False
    return True

def list_agents():
    if not check_runtime():
        return
    agents = get_agents()
    if not agents:
        print("No agents found.")
        return
    for i, a in enumerate(agents, start=1):
        print(f"{i}) {a.name} | Score: {getattr(a,'score',0)}")

def run_agent():
    if run_agent_file is None:
        print("Sandbox runner (arena_core.sandbox) not available.")
        return
    if not check_runtime():
        return
    agents = get_agents()
    if not agents:
        print("No agents found.")
        return
    list_agents()
    try:
        sel = int(input("Select agent # to run: ").strip())
        if sel < 1 or sel > len(agents):
            print("Invalid selection.")
            return
        agent = agents[sel-1]
        # run synchronously (blocking) with a short timeout
        rc, out, err = run_agent_file(agent.path, 6)
        print("\n[Output]")
        if out:
            print(out)
        if err:
            print("\n[Errors]")
            print(err)
        print("")
    except ValueError:
        print("Invalid input.")
    except Exception as e:
        print("Error running agent:", e)

def score_agents():
    if not check_runtime():
        return
    r = input("Attempt auto-repair on failed agents? (y/n) ").strip().lower() == "y"
    try:
        # cmd_score_agents is a compatibility wrapper calling synchronous score_agents
        cmd_score_agents(attempt_repair=r)
    except Exception as e:
        print("Scoring failed:", e)

def beast_mode():
    if not check_runtime():
        return
    try:
        n = input("Number of top agents to enhance (default 3): ").strip()
        top_n = int(n) if n else 3
    except ValueError:
        top_n = 3
    try:
        new = beast_mode_cycle(top_n=top_n)
        if new:
            print("New agents created:")
            for nm in new:
                print(" -", nm)
        else:
            print("No new agents created.")
    except Exception as e:
        print("Beast Mode failed:", e)

def show_plugins():
    if plugin_mgr is None:
        print("Plugin manager not available.")
        return
    print("Loaded plugins:")
    for p in getattr(plugin_mgr, "plugins", []):
        try:
            print(f"- {p.name}")
        except Exception:
            print("- (unnamed plugin)")

def marketplace_dashboard():
    if auto_list_agents is None:
        print("Marketplace auto-list function not available.")
        return
    try:
        auto_list_agents()
    except Exception as e:
        print("Marketplace auto-list failed:", e)

def display_lineage():
    if read_lineage is None:
        print("Lineage tracker not available.")
        return
    lineage = read_lineage()
    if not lineage:
        print("No lineage data.")
        return
    for agent, data in lineage.items():
        mutation = data.get("mutation_desc", "N/A")
        print(f"{agent} <- Parent: {data.get('parent')} | Mutation: {mutation}")

def repair_agent():
    if not check_runtime():
        return
    name = input("Agent filename to repair (e.g. example_agent.py): ").strip()
    if not name:
        print("No name provided.")
        return
    try:
        repair_agent_by_name(name)
    except Exception as e:
        print("Repair failed:", e)

def main_menu():
    menu = """\n=== PhoneArena Studio ===
1) List agents
2) Run agent
3) Score agents
4) Beast Mode
5) Plugin manager
6) Marketplace dashboard
7) Display lineage
8) Repair agent by name
0) Exit"""
    while True:
        print(menu)
        c = input("> ").strip()
        if c == "1": list_agents()
        elif c == "2": run_agent()
        elif c == "3": score_agents()
        elif c == "4": beast_mode()
        elif c == "5": show_plugins()
        elif c == "6": marketplace_dashboard()
        elif c == "7": display_lineage()
        elif c == "8": repair_agent()
        elif c == "0": break
        else:
            print("Invalid option.")

if __name__ == "__main__":
    print(time.strftime("%Y-%m-%d | PhoneArena Studio initialized."))
    main_menu()
