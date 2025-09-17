#!/usr/bin/env python3
import json, os
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB = os.path.join(BASE, "data", "agents_meta.json")
def read():
    try:
        return json.load(open(DB,"r",encoding="utf-8"))
    except:
        return {}
def add_run(agent, record):
    d = read()
    if agent not in d: d[agent] = {"runs":[], "best_score": None}
    d[agent]["runs"].append(record)
    sc = record.get("score")
    if sc is not None:
        if d[agent]["best_score"] is None or sc > d[agent]["best_score"]:
            d[agent]["best_score"] = sc
    with open(DB,"w",encoding="utf-8") as f:
        json.dump(d,f,indent=2)
if __name__ == "__main__":
    print(read())
