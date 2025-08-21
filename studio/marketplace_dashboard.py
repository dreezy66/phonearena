import os, json, time
from arena_core.agent_runtime import get_agents, AGENT_STATUS_PATH

def display_marketplace_dashboard():
    if not os.path.exists(AGENT_STATUS_PATH):
        print("[Marketplace] No agent statuses found. Run scoring first.")
        return

    with open(AGENT_STATUS_PATH) as f:
        stats = json.load(f)

    print("=== Marketplace Dashboard ===")
    top_agents = sorted(stats.items(), key=lambda kv: kv[1].get("score",0), reverse=True)
    for name, info in top_agents:
        score = info.get("score", 0)
        potential_value = score * 2  # Simplified value estimation
        status = "Ready" if score >= 50 else "Weak"
        print(f"{name} | Score: {score} | Status: {status} | Estimated Value: ${potential_value}")
    print("==============================")

if __name__=="__main__":
    display_marketplace_dashboard()
