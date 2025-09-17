#!/usr/bin/env python3
"""
handle_apply_patch: apply a full-file replacement patch map to a project (with snapshot)
Patch format: {"rel/path.py": "new content", ...}
"""
import os, shutil, time, json
def run(project_path, patch_map):
    project_abs = project_path if os.path.isabs(project_path) else os.path.join(os.getcwd(), project_path)
    if not os.path.isdir(project_abs):
        return False, "Project path not found"
    # snapshot
    snapshot = f"{project_abs}_snapshot_{int(time.time())}"
    shutil.copytree(project_abs, snapshot)
    # apply
    try:
        for rel, content in patch_map.items():
            dest = os.path.join(project_abs, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(content)
        return True, f"Applied patch; snapshot at {snapshot}"
    except Exception as e:
        # rollback
        if os.path.isdir(snapshot):
            shutil.rmtree(project_abs)
            shutil.move(snapshot, project_abs)
        return False, f"Apply failed, rolled back: {e}"
