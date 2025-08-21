# lineage_tracker.py — simple lineage file store with safe I/O and logging
import os
from .io_utils import safe_read_json, safe_write_json

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LINEAGE_FILE = os.path.join(BASE, "agent_data", "lineage.json")

def read_lineage():
    data = safe_read_json(LINEAGE_FILE)
    # normalize to dict
    if isinstance(data, dict):
        return data
    return {}

def record_lineage(name, parent=None, mutation_desc=None):
    lineage = read_lineage()
    lineage[name] = {"parent": parent, "mutation_desc": mutation_desc}
    safe_write_json(LINEAGE_FILE, lineage)
    return True
