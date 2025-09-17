#!/usr/bin/env python3
"""
Surgical Developer - small, safe, test-first agent.
Generates safe full-file replacement patches (heuristics), runs tests in tmp copy.
"""
from __future__ import annotations
import os, subprocess, tempfile, shutil, hashlib, time, json
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEST_CMD = ["python3", "-m", "unittest", "discover", "-v"]

def now_ts(): return time.strftime("%Y%m%dT%H%M%S")
def hash_text(t): import hashlib; return hashlib.sha1(t.encode()).hexdigest()[:8]

class SurgicalDeveloper:
    def __init__(self, name="surgical_developer"):
        self.name = name

    def _run_tests(self, project_path, timeout=30):
        try:
            proc = subprocess.Popen(TEST_CMD, cwd=project_path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            out, _ = proc.communicate(timeout=timeout)
            return (proc.returncode == 0), out
        except Exception as e:
            return False, f"Test runner error: {e}"

    def propose_patch(self, project_path, goal="fix tests"):
        patches = {}
        main_py = os.path.join(project_path, "main.py")
        if os.path.isfile(main_py):
            with open(main_py, "r", encoding="utf-8") as f:
                src = f.read()
            if "if __name__" not in src:
                new = src + "\\n\\nif __name__ == '__main__':\\n    run()\\n"
                patches["main.py"] = new
        # placeholder for patterns.json integration
        return patches

    def apply_patch_to_tmp(self, project_path, patches):
        tmp = tempfile.mkdtemp(prefix="surg_")
        base = os.path.basename(project_path.rstrip(os.sep))
        dst = os.path.join(tmp, base)
        shutil.copytree(project_path, dst)
        for rel, content in patches.items():
            dest = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(content)
        return dst

    def act(self, task):
        target = task.get("target")
        if not target: return {"ok":False,"error":"no target"}
        project = target if os.path.isabs(target) else os.path.join(BASE, target)
        if not os.path.isdir(project): return {"ok":False,"error":"not found"}
        baseline_ok, baseline_log = self._run_tests(project)
        patches = self.propose_patch(project, task.get("goal","fix tests"))
        result = {"timestamp": now_ts(), "baseline_ok": baseline_ok, "patch": patches}
        if patches:
            tmp = self.apply_patch_to_tmp(project, patches)
            tmp_proj = os.path.join(tmp, os.path.basename(project))
            passed, post_log = self._run_tests(tmp_proj)
            result.update({"post_passed": passed, "post_log": post_log})
            result["score"] = 90 if passed and not baseline_ok else (60 if passed else 10)
        else:
            result.update({"post_passed": False, "score": 0})
        return result

if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Usage: surgical_developer.py <project_rel_path>")
        sys.exit(1)
    agent = SurgicalDeveloper()
    print(json.dumps(agent.act({"type":"improve","target":sys.argv[1]}), indent=2))
