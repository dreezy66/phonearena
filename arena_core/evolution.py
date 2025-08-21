import os, time, json
from .agent_runtime import cmd_score_agents, cmd_beast_mode_single_cycle, EXAMPLES_DIR, AGENTS_DIR, AGENT_STATUS_PATH, _list_py_files
from .sandbox import run_agent_file, safe_write_json
from .repair_agent import attempt_repair
PATTERNS_PATH = os.path.join(os.path.dirname(__file__), "patterns.json")

def load_patterns():
    try:
        with open(PATTERNS_PATH) as f:
            return json.load(f)
    except:
        return []

def save_pattern(entry):
    patterns = load_patterns()
    patterns.append(entry)
    tmp = PATTERNS_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(patterns, f, indent=2)
    os.replace(tmp, PATTERNS_PATH)

def attempt_repairs_on_failures(timeout=6):
    # Run all agents and attempt repair for failing ones
    repaired = []
    statuses = {}
    for d in (EXAMPLES_DIR, AGENTS_DIR):
        if not os.path.isdir(d):
            continue
        for f in _list_py_files(d):
            path = os.path.join(d, f)
            rc, out, err = run_agent_file(path, timeout=timeout)
            statuses[f] = {"success": rc==0, "score": 100 if rc==0 else 10, "out": out[:200], "err": err[:500], "path": path}
            if rc != 0:
                try:
                    with open(path, "r") as fh:
                        src = fh.read()
                    newsrc = attempt_repair(src, err or out)
                    if newsrc and newsrc != src:
                        ts = int(time.time())
                        name = os.path.splitext(f)[0] + f"_repaired_{ts}.py"
                        dst = os.path.join(AGENTS_DIR if d==AGENTS_DIR else d, name)
                        with open(dst, "w") as fh:
                            fh.write(newsrc)
                        print(f"[evolution] Repaired {f} -> {name}")
                        save_pattern({"agent": f, "repaired_into": name, "ts": ts, "sample": newsrc[:400]})
                        repaired.append(name)
                except Exception as e:
                    print(f"[evolution] repair error for {f}: {e}")
    # write statuses
    try:
        safe_write_json(AGENT_STATUS_PATH, statuses)
    except Exception as e:
        print("[evolution] failed to write statuses:", e)
    return repaired

def run_beast_loop(delay_seconds=10, max_cycles=None):
    print("[evolution] Starting continuous Beast Loop...")
    cycles = 0
    try:
        while True:
            cycles += 1
            print(f"[evolution] cycle {cycles} - scoring + repair pass")
            # scoring + repairs
            repaired = attempt_repairs_on_failures(timeout=8)
            print(f"[evolution] repaired: {repaired}")
            # then run beast single cycle to spawn improvements from best agent
            try:
                cmd_beast_mode_single_cycle()
            except Exception as e:
                print("[evolution] beast cycle error:", e)
            if max_cycles and cycles >= int(max_cycles):
                print("[evolution] reached max cycles:", max_cycles)
                break
            time.sleep(delay_seconds)
    except KeyboardInterrupt:
        print("[evolution] interrupted by user")
    print("[evolution] Beast Loop ended.")
