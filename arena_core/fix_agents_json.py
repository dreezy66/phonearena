import os, json, time

AGENT_DIR = "/storage/emulated/0/PhoneArena/agents"
STATUS_FILE = "/storage/emulated/0/PhoneArena/agent_data/agent_status.json"

agents = []
for f in os.listdir(AGENT_DIR):
    if f.endswith(".py"):
        name = f[:-3]
        agents.append({
            "name": name,
            "score": 100,
            "parent": None,
            "mutation": None,
            "path": os.path.join(AGENT_DIR, f)
        })

with open(STATUS_FILE, "w") as f:
    json.dump(agents, f, indent=2)

print(f"[Fix] {len(agents)} agents written to agent_status.json")
