#!/usr/bin/env python3
"""
Simple reporter: reads latest agent run metadata and writes to metrics store.
"""
import os, json
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB = os.path.join(BASE, "data", "agents_meta.json")
def report(agent_name, record):
    try:
        d = json.load(open(DB,"r",encoding="utf-8"))
    except:
        d = {}
    if agent_name not in d: d[agent_name] = {"runs": [], "best_score": None}
    d[agent_name]["runs"].append(record)
    sc = record.get("score")
    if sc is not None and (d[agent_name]["best_score"] is None or sc > d[agent_name]["best_score"]):
        d[agent_name]["best_score"] = sc
    with open(DB,"w",encoding="utf-8") as f:
        json.dump(d, f, indent=2)
    return True
if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 3:
        print("usage: reporter_agent.py agent_name json_record")
        sys.exit(1)
    name = sys.argv[1]
    rec = json.loads(sys.argv[2])
    print(report(name, rec))
