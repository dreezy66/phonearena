# Minimal safe sandbox runner wrapper used by runtime.
# This file expects a simple "run_agent_file(path, timeout)" function to exist.
# If you already have a more advanced sandbox, keep it — this one is safe fallback.

import subprocess, sys, shlex, threading, os, tempfile

def _run_subprocess(cmd, timeout):
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        try:
            out, err = proc.communicate(timeout=timeout)
        except Exception:
            proc.kill()
            out, err = proc.communicate()
        return proc.returncode, (out or b"").decode(errors="ignore"), (err or b"").decode(errors="ignore")
    except Exception as e:
        return 1, "", str(e)

def run_agent_file(path, timeout=8):
    """
    Run a python file in a subprocess and return (rc, out, err).
    Uses the system python in PATH.
    """
    if not os.path.exists(path):
        return 1, "", f"Agent file not found: {path}"
    # Use sys.executable if available; fallback to 'python3'
    py = sys.executable or "python3"
    cmd = f"{shlex.quote(py)} {shlex.quote(path)}"
    return _run_subprocess(cmd, timeout)

def safe_write_json(path, data):
    import json, os
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
