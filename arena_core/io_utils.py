# io_utils.py — safe JSON helpers
import json
import os
import tempfile

def safe_read_json(path):
    """Return parsed JSON from path, or a reasonable default ({} or [])."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        # best-effort fallback
        try:
            s = open(path, "r", encoding="utf-8").read().strip()
            if s.startswith("["):
                return []
            return {}
        except Exception:
            return {}

def safe_write_json(path, obj):
    """Atomically write JSON to path (creates dir if needed)."""
    try:
        d = os.path.dirname(path)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
        # atomic write
        fd, tmp = tempfile.mkstemp(dir=d, text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        return True
    except Exception:
        return False
