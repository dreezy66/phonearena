#!/usr/bin/env python3
"""
Aponi Explorer API - lightweight Flask app
Serve file tree and basic file ops for the HTML dashboard.

Security notes:
 - Path traversal prevented by resolving realpath and enforcing BASE_PATH prefix.
 - Limits: MAX_READ_BYTES and MAX_WRITE_BYTES to avoid huge memory usage.
 - Not production hardened: add auth, HTTPS, rate-limiting, CSRF for internet-facing installs.
"""

import os
import sys
import tempfile
import shutil
import fnmatch
import json
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, abort, send_file
from werkzeug.utils import secure_filename

# ===== Configuration =====
BASE_PATH = os.environ.get("APONI_BASE_PATH", "/storage/emulated/0/ADAAD/Aponi")
MAX_READ_BYTES = 512 * 1024     # 512 KB max read for editor
MAX_WRITE_BYTES = 1024 * 1024   # 1 MB max write
EXCLUDE_DIR_PATTERNS = [
    "__pycache__", ".pytest_cache", "*.backup*", "*backups*", "patch_backups",
    ".git", ".idea", ".vscode"
]
EXCLUDE_FILE_PATTERNS = [
    "*.bak*", "*.tmp", "*.swp", "*.log", "*.pyc", "*.pyo",
]

# Performance: only return children list when requested (lazy loading)
# Default flask app
app = Flask(__name__)


# ===== Helpers =====
def is_excluded(name, patterns):
    name_lower = name.lower()
    return any(fnmatch.fnmatch(name_lower, pat.lower()) for pat in patterns)

def safe_resolve(user_path: str) -> Path:
    """Resolve and ensure path is within BASE_PATH."""
    base = Path(BASE_PATH).resolve()
    # Interpret relative user_path relative to base
    candidate = (base / user_path).resolve()
    if not str(candidate).startswith(str(base)):
        raise ValueError("Path outside of base")
    return candidate

def stat_item(p: Path):
    """Return JSON-friendly stat info."""
    s = p.stat()
    return {
        "name": p.name,
        "path": str(p.relative_to(Path(BASE_PATH).resolve())),
        "is_dir": p.is_dir(),
        "size": s.st_size,
        "mtime": int(s.st_mtime),
        "mtime_iso": datetime.utcfromtimestamp(s.st_mtime).isoformat() + "Z"
    }

def list_children(dir_path: Path, include_children=False):
    try:
        entries = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    except PermissionError:
        return {"error": "permission denied"}

    out = []
    for e in entries:
        if e.is_dir():
            if is_excluded(e.name, EXCLUDE_DIR_PATTERNS):
                continue
            item = stat_item(e)
            item["child_count"] = sum(1 for _ in e.iterdir() if not is_excluded(_.name, EXCLUDE_DIR_PATTERNS))
            if include_children:
                item["children"] = [stat_item(c) for c in sorted(e.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())) if not is_excluded(c.name, EXCLUDE_FILE_PATTERNS)]
        else:
            if is_excluded(e.name, EXCLUDE_FILE_PATTERNS):
                continue
            item = stat_item(e)
        out.append(item)
    return out

def ensure_parent_dir(path: Path):
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)

# ===== API endpoints =====

@app.route("/api/explorer", methods=["GET"])
def api_explorer():
    """
    GET /api/explorer?path=relative/path&children=true
    - path is relative to BASE_PATH. default = ""
    - children=true will include immediate children for the requested folder
    """
    rel = request.args.get("path", "").strip("/")
    include_children = request.args.get("children", "false").lower() == "true"
    try:
        target = safe_resolve(rel)
    except ValueError:
        return jsonify({"error":"invalid path"}), 400

    if not target.exists():
        return jsonify({"error":"not found"}), 404
    if not target.is_dir():
        return jsonify({"error":"not a directory"}), 400

    data = list_children(target, include_children=include_children)
    return jsonify({"base": str(Path(BASE_PATH).resolve()), "path": rel, "items": data})

@app.route("/api/file", methods=["GET"])
def api_read_file():
    """
    GET /api/file?path=relative/path/to/file
    Reads up to MAX_READ_BYTES and returns text (utf-8).
    """
    rel = request.args.get("path")
    if not rel:
        return jsonify({"error":"missing path"}), 400
    try:
        target = safe_resolve(rel)
    except ValueError:
        return jsonify({"error":"invalid path"}), 400
    if not target.exists() or not target.is_file():
        return jsonify({"error":"not found"}), 404

    size = target.stat().st_size
    if size > MAX_READ_BYTES:
        return jsonify({"error":"file too large", "size": size}), 413

    # Try to read as text; if binary-ish, refuse (dashboard editor expects text)
    try:
        text = target.read_text(encoding="utf-8", errors="strict")
    except Exception:
        return jsonify({"error":"file not readable as utf-8 text"}), 415

    return jsonify({"path": rel, "size": size, "content": text})

@app.route("/api/file", methods=["POST"])
def api_write_file():
    """
    POST /api/file
    JSON: { "path": "rel/path.txt", "content": "...", "overwrite": true }
    Will create parent dirs if needed. Atomic write via tempfile + replace.
    """
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error":"invalid json"}), 400
    rel = payload.get("path")
    content = payload.get("content", "")
    overwrite = bool(payload.get("overwrite", True))

    if not rel:
        return jsonify({"error":"missing path"}), 400

    try:
        target = safe_resolve(rel)
    except ValueError:
        return jsonify({"error":"invalid path"}), 400

    # size guard
    if len(content.encode("utf-8")) > MAX_WRITE_BYTES:
        return jsonify({"error":"payload too large"}), 413

    if target.exists() and not overwrite:
        return jsonify({"error":"target exists"}), 409

    ensure_parent_dir(target)
    # atomic write
    fd, tmpname = tempfile.mkstemp(dir=str(target.parent))
    os.close(fd)
    try:
        with open(tmpname, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmpname, str(target))
    finally:
        if os.path.exists(tmpname):
            os.remove(tmpname)
    return jsonify({"ok": True, "path": rel})

@app.route("/api/folder", methods=["POST"])
def api_create_folder():
    """
    POST /api/folder
    JSON: {"path": "rel/new/folder"}
    """
    payload = request.get_json(force=True)
    rel = payload.get("path")
    if not rel:
        return jsonify({"error":"missing path"}), 400
    try:
        target = safe_resolve(rel)
    except ValueError:
        return jsonify({"error":"invalid path"}), 400
    target.mkdir(parents=True, exist_ok=True)
    return jsonify({"ok": True, "path": rel})

@app.route("/api/delete", methods=["POST"])
def api_delete():
    """
    POST /api/delete
    JSON: {"path":"rel/path", "recursive": true}
    """
    payload = request.get_json(force=True)
    rel = payload.get("path")
    recursive = bool(payload.get("recursive", True))
    if not rel:
        return jsonify({"error":"missing path"}), 400
    try:
        target = safe_resolve(rel)
    except ValueError:
        return jsonify({"error":"invalid path"}), 400
    if not target.exists():
        return jsonify({"error":"not found"}), 404
    if target.is_dir():
        if recursive:
            shutil.rmtree(target)
        else:
            target.rmdir()
    else:
        target.unlink()
    return jsonify({"ok": True})

@app.route("/api/rename", methods=["POST"])
def api_rename():
    """
    POST /api/rename
    JSON: {"from":"rel/old", "to":"rel/new"}
    """
    payload = request.get_json(force=True)
    f = payload.get("from")
    t = payload.get("to")
    if not f or not t:
        return jsonify({"error":"missing from/to"}), 400
    try:
        src = safe_resolve(f)
        dst = safe_resolve(t)
    except ValueError:
        return jsonify({"error":"invalid path"}), 400
    ensure_parent_dir(dst)
    os.replace(str(src), str(dst))
    return jsonify({"ok": True, "from": f, "to": t})

# Simple health
@app.route("/api/ping")
def ping():
    return jsonify({"ok": True, "base": str(Path(BASE_PATH).resolve())})

# ===== CLI runner =====
if __name__ == "__main__":
    if not os.path.exists(BASE_PATH):
        print(f"ERROR: BASE_PATH not found: {BASE_PATH}", file=sys.stderr)
        sys.exit(1)
    host = os.environ.get("APONI_HOST", "0.0.0.0")
    port = int(os.environ.get("APONI_PORT", 8000))
    print(f"Aponi Explorer serving {BASE_PATH} on http://{host}:{port}")
    # Use threaded mode for lightweight concurrency. For production use Gunicorn / uWSGI + auth.
    app.run(host=host, port=port, threaded=True)