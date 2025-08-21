import os, json, time
from pathlib import Path

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LINEAGE_FILE = os.path.join(BASE_DIR, "agent_data", "lineage.json")

if not os.path.exists(os.path.dirname(LINEAGE_FILE)):
    os.makedirs(os.path.dirname(LINEAGE_FILE))

def _load_lineage():
    if os.path.exists(LINEAGE_FILE):
        with open(LINEAGE_FILE, "r") as f:
            return json.load(f)
    return {}

def _save_lineage(data):
    with open(LINEAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def record_lineage(parent_name, child_name):
    data = _load_lineage()
    ts = int(time.time())
    entry = {
        "parent": parent_name,
        "child": child_name,
        "timestamp": ts
    }
    data.setdefault(parent_name, []).append(entry)
    _save_lineage(data)
    print(f"[Lineage] Recorded: {parent_name} -> {child_name}")

def show_lineage(agent_name=None):
    data = _load_lineage()
    if agent_name:
        lineage = data.get(agent_name, [])
        if not lineage:
            print(f"No lineage found for {agent_name}")
            return
        print(f"=== Lineage for {agent_name} ===")
        for entry in lineage:
            print(f"{entry['parent']} -> {entry['child']} @ {time.ctime(entry['timestamp'])}")
    else:
        print("=== Full Agent Lineage ===")
        for parent, entries in data.items():
            for entry in entries:
                print(f"{entry['parent']} -> {entry['child']} @ {time.ctime(entry['timestamp'])}")
