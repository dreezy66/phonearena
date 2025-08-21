import os, json, shutil, time

SNAP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent_data", "snapshots"))
AGENT_STATUS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent_data", "agent_status.json"))

def save_snapshot():
    os.makedirs(SNAP_DIR, exist_ok=True)
    ts = int(time.time())
    dst = os.path.join(SNAP_DIR, f"snapshot_{ts}.json")
    if os.path.exists(AGENT_STATUS_PATH):
        shutil.copy(AGENT_STATUS_PATH, dst)
        print(f"[Snapshot] Saved snapshot {dst}")

def restore_latest_snapshot():
    if not os.path.exists(SNAP_DIR): return
    snapshots = sorted(os.listdir(SNAP_DIR))
    if snapshots:
        latest = snapshots[-1]
        src = os.path.join(SNAP_DIR, latest)
        shutil.copy(src, AGENT_STATUS_PATH)
        print(f"[Snapshot] Restored {latest}")
