import os, json, time

AGENT_STATUS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent_data", "agent_status.json"))

def show_dashboard(top_n=10):
    if not os.path.exists(AGENT_STATUS_PATH):
        print("[Dashboard] No agent stats found. Run scoring first.")
        return
    with open(AGENT_STATUS_PATH) as f:
        stats = json.load(f)
    sorted_agents = sorted(stats.items(), key=lambda kv: kv[1].get("score",0), reverse=True)[:top_n]
    print("=== PhoneArena Agent Dashboard ===")
    for name, info in sorted_agents:
        print(f"{name} | Score: {info.get('score')} | Success: {info.get('success')} | Last RC: {info.get('rc', 'N/A')}")
