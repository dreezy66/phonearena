import os, json, time
from concurrent.futures import ThreadPoolExecutor
from arena_core.sandbox import run_agent_file, safe_write_json
from arena_core.repair_agent import attempt_repair
from arena_core.pattern_manager import save_pattern, extract_top_snippets

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AGENTS_DIR = os.path.join(BASE, "agents")
EXAMPLES_DIR = os.path.join(BASE, "examples")
AGENT_STATUS_PATH = os.path.join(BASE, "agent_data", "agent_status.json")

executor = ThreadPoolExecutor(max_workers=4)

try:
    from arena_core.agent_utils import get_top_agents, create_mutated_agent
except Exception:
    pass

class Agent:
    def __init__(self, name, path, score=0, parent=None):
        self.name = name
        self.path = path
        self.score = score
        self.last_rc = None
        self.last_out = ""
        self.last_err = ""
        self.parent = parent
        self.mutation_desc = None
    def __repr__(self):
        return f"<Agent {self.name} score={self.score}>"

def _load_statuses():
    if not os.path.exists(AGENT_STATUS_PATH):
        return {}
    try:
        with open(AGENT_STATUS_PATH) as f:
            data = json.load(f)
        if isinstance(data, list):
            out = {}
            for i, item in enumerate(data):
                name = item.get("name") or f"agent_{i}"
                out[name] = item
            return out
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}

def get_agents():
    statuses = _load_statuses()
    agents = []
    for d in (EXAMPLES_DIR, AGENTS_DIR):
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(d, fn)
            a = Agent(fn, path)
            st = statuses.get(fn, {})
            a.score = st.get("score", 0)
            a.last_rc = 0 if st.get("success") else 1
            a.last_out = st.get("out", "")
            a.last_err = st.get("err", "")
            agents.append(a)
    return agents

def save_agents(agent_list):
    out = {}
    for a in agent_list:
        out[a.name] = {
            "name": a.name,
            "score": getattr(a, "score", 0),
            "success": getattr(a, "last_rc", 1) == 0,
            "out": getattr(a, "last_out", ""),
            "err": getattr(a, "last_err", ""),
            "path": getattr(a, "path", ""),
            "parent": getattr(a, "parent", None),
            "mutation_desc": getattr(a, "mutation_desc", None)
        }
    safe_write_json(AGENT_STATUS_PATH, out)

def score_agents(timeout=8, attempt_repair=False):
    agents = get_agents()
    for a in agents:
        try:
            rc, out, err = run_agent_file(a.path, timeout)
            a.last_rc = rc
            a.last_out = (out or "")[:200]
            a.last_err = (err or "")[:500]
            a.score = 100 if rc == 0 else 10
            if attempt_repair and rc != 0:
                try:
                    newsrc = attempt_repair(open(a.path).read(), err or out or "")
                    if newsrc and newsrc != open(a.path).read():
                        ts = int(time.time())
                        newname = os.path.splitext(a.name)[0] + f"_repaired_{ts}.py"
                        dst = os.path.join(os.path.dirname(a.path), newname)
                        with open(dst, "w") as fh:
                            fh.write(newsrc)
                        print(f"[agent_runtime] Repaired {a.name} -> {newname}")
                except Exception as e:
                    print("[agent_runtime] repair error:", e)
            if a.last_rc == 0:
                try:
                    snippet = extract_top_snippets(a.path)
                    if snippet:
                        save_pattern(a.name, snippet)
                except Exception:
                    pass
        except Exception as e:
            print(f"[agent_runtime] run failed {a.name}: {e}")
    save_agents(agents)
    try:
        from arena_core.marketplace_auto import auto_list_agents
        auto_list_agents(agents=agents, top_n=5)
    except Exception:
        pass
    print("Scoring complete; statuses written to", AGENT_STATUS_PATH)

def beast_mode_sync(top_n=3):
    try:
        from arena_core.agent_utils import get_top_agents, create_mutated_agent
    except Exception as e:
        print("[agent_runtime] Missing agent_utils:", e)
        return []

    agents = get_agents()
    top_agents = get_top_agents(agents, top_n)
    if not top_agents:
        print("[Beast Mode] No top agents found.")
        return []

    new_agents = []
    for ag in top_agents:
        new = create_mutated_agent(ag, Agent)
        if new:
            try:
                from arena_core.lineage_tracker import record_lineage
                record_lineage(new.name, parent=ag.name, mutation_desc=getattr(new, "mutation_desc", "beast_cycle"))
            except Exception:
                pass
            new_agents.append(new)
            print(f"[Beast Mode] New agent created: {new.name}")

    save_agents(agents + new_agents)

    try:
        from arena_core.marketplace_auto import auto_list_agents
        auto_list_agents(agents=new_agents, top_n=top_n)
    except Exception:
        pass
    return [n.name for n in new_agents]
