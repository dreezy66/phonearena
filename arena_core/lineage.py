import os, json, time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LINEAGE_DIR = os.path.join(BASE_DIR, "agent_data", "lineage")
if not os.path.exists(LINEAGE_DIR):
    os.makedirs(LINEAGE_DIR)

def record_lineage(agent_name, parent=None, mutation_desc=""):
    ts = int(time.time())
    entry = {
        "timestamp": ts,
        "agent_name": agent_name,
        "parent": parent,
        "mutation": mutation_desc
    }
    lineage_file = os.path.join(LINEAGE_DIR, f"{agent_name}_lineage.json")
    data = []
    if os.path.exists(lineage_file):
        with open(lineage_file) as f:
            data = json.load(f)
    data.append(entry)
    with open(lineage_file, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[Lineage] Recorded lineage for {agent_name}")

def get_lineage(agent_name):
    lineage_file = os.path.join(LINEAGE_DIR, f"{agent_name}_lineage.json")
    if not os.path.exists(lineage_file):
        return []
    with open(lineage_file) as f:
        return json.load(f)
