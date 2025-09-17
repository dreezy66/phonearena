### START: aponi_server.py (clean secure version)
#!/usr/bin/env python3
"""
Aponi secure server (single-file)
 - Configurable via env: APONI_HOST, APONI_PORT, APONI_ROOT, APONI_TOKEN
 - Rate-limited, API-key protected mutating endpoints (write/create/rename/copy/delete/run)
 - Safe-path restrictions (ROOT)
 - SSE streaming endpoint for run_stream
"""
import os, sys, json, time, traceback, signal, logging, secrets, subprocess
from pathlib import Path
from functools import wraps
from flask import Flask, request, jsonify, Response, stream_with_context, send_from_directory
from flask_cors import CORS

# ---------- configuration ----------
HOST = os.environ.get("APONI_HOST", "127.0.0.1")   # set "0.0.0.0" to allow LAN access (careful)
PORT = int(os.environ.get("APONI_PORT", "8765"))
ROOT = Path(os.environ.get("APONI_ROOT") or str(Path.home() / "storage" / "shared" / "ADAAD")).resolve()
API_TOKEN = os.environ.get("APONI_TOKEN", "")  # required for mutating endpoints
ALLOW_ORIGINS = os.environ.get("APONI_ALLOW_ORIGINS", "http://127.0.0.1:8080,http://localhost:8080").split(",")
RUN_TIMEOUT = int(os.environ.get("APONI_RUN_TIMEOUT", "60"))  # seconds
MAX_WRITE_BYTES = int(os.environ.get("APONI_MAX_WRITE_BYTES", str(2 * 1024 * 1024)))  # 2 MB

# ---------- logging ----------
logger = logging.getLogger("aponi")
logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
h = logging.StreamHandler(sys.stdout)
h.setFormatter(fmt)
logger.addHandler(h)

# ---------- app ----------
app = Flask("aponi_server")
CORS(app, origins=[o for o in ALLOW_ORIGINS if o])

# ---------- helpers ----------
def json_ok(**kw):
    d = {"ok": True}
    d.update(kw)
    return jsonify(d)

def json_err(msg, code=400, **extra):
    d = {"ok": False, "error": msg}
    d.update(extra)
    return jsonify(d), code

def safe_path(rel):
    p = Path(rel)
    p = p if p.is_absolute() else (ROOT.joinpath(rel))
    try:
        p = p.resolve()
    except Exception:
        raise ValueError("Invalid path")
    try:
        p.relative_to(ROOT)
    except Exception:
        raise ValueError("Path outside allowed root")
    return p

def require_api_key(optional=False):
    def deco(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not API_TOKEN:
                if optional:
                    return fn(*args, **kwargs)
                logger.warning("API token not configured - rejecting protected request")
                return json_err("Server configured without API token", 403)
            key = request.headers.get("X-API-Key") or request.args.get("api_key")
            if not key or not secrets.compare_digest(key, API_TOKEN):
                return json_err("Missing or invalid API key", 401)
            return fn(*args, **kwargs)
        return wrapped
    return deco

# naive in-memory rate limiter (per IP)
_rate_store = {}
def rate_limited(max_requests=40, window=60):
    def deco(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            ip = request.remote_addr or "local"
            now = time.time()
            timestamps = _rate_store.get(ip, [])
            timestamps = [t for t in timestamps if t > now - window]
            if len(timestamps) >= max_requests:
                logger.warning("Rate limit exceeded for %s", ip)
                return json_err("Rate limit exceeded", 429)
            timestamps.append(now)
            _rate_store[ip] = timestamps
            return fn(*args, **kwargs)
        return wrapped
    return deco

# ---------- endpoints ----------
@app.route("/api/list", methods=["GET"])
def api_list():
    q = request.args.get("path", ".")
    try: p = safe_path(q)
    except Exception as e: return json_err(str(e), 400)
    if not p.exists(): return json_err("Not found", 404)
    items = []
    try:
        for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            items.append({
                "name": child.name,
                "path": str(child.relative_to(ROOT)),
                "is_dir": child.is_dir(),
                "size": child.stat().st_size if child.exists() and child.is_file() else None,
                "mtime": child.stat().st_mtime
            })
        return json_ok(path=str(p.relative_to(ROOT)), items=items)
    except Exception as e:
        logger.exception("list error")
        return json_err("list error: " + str(e), 500)

@app.route("/api/read", methods=["GET"])
def api_read():
    q = request.args.get("path")
    if not q: return json_err("missing path", 400)
    try: p = safe_path(q)
    except Exception as e: return json_err(str(e), 400)
    if not p.exists() or not p.is_file(): return json_err("file not found", 404)
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
        return json_ok(path=str(p.relative_to(ROOT)), content=text)
    except Exception as e:
        logger.exception("read error")
        return json_err("read error: " + str(e), 500)

@app.route("/api/write", methods=["POST"])
@require_api_key(optional=False)
@rate_limited()
def api_write():
    try:
        data = request.get_json(force=True)
    except Exception:
        return json_err("Invalid JSON", 400)
    path = data.get("path")
    content = data.get("content", "")
    if not path: return json_err("missing path", 400)
    if len(content.encode("utf-8")) > MAX_WRITE_BYTES:
        return json_err("content too large", 413)
    try:
        p = safe_path(path)
    except Exception as e:
        return json_err(str(e), 400)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        # atomic save: write to temp then rename
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(p)
        logger.info("Wrote file %s", p)
        return json_ok(path=str(p.relative_to(ROOT)))
    except Exception as e:
        logger.exception("write error")
        return json_err("write error: "+str(e), 500)

@app.route("/api/create", methods=["POST"])
@require_api_key(optional=False)
@rate_limited()
def api_create():
    try:
        data = request.get_json(force=True)
    except Exception:
        return json_err("Invalid JSON", 400)
    path = data.get("path"); typ = data.get("type", "file")
    if not path: return json_err("missing path", 400)
    try: p = safe_path(path)
    except Exception as e: return json_err(str(e), 400)
    try:
        if typ == "dir":
            p.mkdir(parents=True, exist_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("", encoding="utf-8")
        logger.info("Created %s as %s", p, typ)
        return json_ok(path=str(p.relative_to(ROOT)))
    except Exception as e:
        logger.exception("create error")
        return json_err("create error: "+str(e), 500)

@app.route("/api/rename", methods=["POST"])
@require_api_key(optional=False)
@rate_limited()
def api_rename():
    try:
        data = request.get_json(force=True)
    except Exception:
        return json_err("Invalid JSON", 400)
    src = data.get("src"); dst = data.get("dst")
    if not src or not dst: return json_err("missing src/dst", 400)
    try:
        ps = safe_path(src); pd = safe_path(dst)
    except Exception as e:
        return json_err(str(e), 400)
    try:
        pd.parent.mkdir(parents=True, exist_ok=True)
        ps.rename(pd)
        logger.info("Renamed %s -> %s", ps, pd)
        return json_ok(src=str(ps.relative_to(ROOT)), dst=str(pd.relative_to(ROOT)))
    except Exception as e:
        logger.exception("rename error")
        return json_err("rename error: "+str(e), 500)

@app.route("/api/copy", methods=["POST"])
@require_api_key(optional=False)
@rate_limited()
def api_copy():
    import shutil
    try:
        data = request.get_json(force=True)
    except Exception:
        return json_err("Invalid JSON", 400)
    src = data.get("src"); dst = data.get("dst")
    if not src or not dst: return json_err("missing src/dst", 400)
    try:
        ps = safe_path(src); pd = safe_path(dst)
    except Exception as e: return json_err(str(e), 400)
    try:
        pd.parent.mkdir(parents=True, exist_ok=True)
        if ps.is_dir():
            shutil.copytree(ps, pd)
        else:
            shutil.copy2(ps, pd)
        logger.info("Copied %s -> %s", ps, pd)
        return json_ok(src=str(ps.relative_to(ROOT)), dst=str(pd.relative_to(ROOT)))
    except Exception as e:
        logger.exception("copy error")
        return json_err("copy error: "+str(e), 500)

@app.route("/api/delete", methods=["POST"])
@require_api_key(optional=False)
@rate_limited()
def api_delete():
    import shutil
    try:
        data = request.get_json(force=True)
    except Exception:
        return json_err("Invalid JSON", 400)
    path = data.get("path")
    if not path: return json_err("missing path", 400)
    try: p = safe_path(path)
    except Exception as e: return json_err(str(e), 400)
    try:
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        logger.info("Deleted %s", p)
        return json_ok()
    except Exception as e:
        logger.exception("delete error")
        return json_err("delete error: "+str(e), 500)

@app.route("/api/run", methods=["POST"])
@require_api_key(optional=False)
@rate_limited(max_requests=10, window=60)
def api_run():
    try:
        data = request.get_json(force=True)
    except Exception:
        return json_err("Invalid JSON", 400)
    path = data.get("path")
    args = data.get("args", [])
    if not path: return json_err("missing path", 400)
    try: p = safe_path(path)
    except Exception as e: return json_err(str(e), 400)
    if not p.exists(): return json_err("not found", 404)
    cmd = [sys.executable, str(p)] + args if p.suffix in (".py", ".pyw") else ["/system/bin/sh", str(p)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=RUN_TIMEOUT)
        return json_ok(exit_code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
    except subprocess.TimeoutExpired as te:
        return json_err("timeout", 500, details=str(te))
    except Exception as e:
        logger.exception("run error")
        return json_err("exception", 500, details=str(e))

@app.route("/api/run_stream", methods=["GET"])
@require_api_key(optional=False)
def api_run_stream():
    path = request.args.get("path")
    if not path: return json_err("missing path", 400)
    try: p = safe_path(path)
    except Exception as e: return json_err(str(e), 400)
    if not p.exists(): return json_err("not found", 404)
    cmd = [sys.executable, str(p)] if p.suffix in (".py", ".pyw") else ["/system/bin/sh", str(p)]
    def generate():
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            while True:
                out = proc.stdout.readline()
                err = proc.stderr.readline()
                if out:
                    yield f"data: {json.dumps({'type':'stdout','line':out.rstrip()})}\\n\\n"
                if err:
                    yield f"data: {json.dumps({'type':'stderr','line':err.rstrip()})}\\n\\n"
                if out == '' and err == '' and proc.poll() is not None:
                    break
                time.sleep(0.01)
            yield f"data: {json.dumps({'type':'exit','code':proc.returncode})}\\n\\n"
        except Exception as e:
            logger.exception("stream error")
            yield f"data: {json.dumps({'type':'error','msg':str(e)})}\\n\\n"
    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/aponi_static/<path:fn>", methods=["GET"])
def static_file(fn):
    try:
        p = safe_path(fn)
    except Exception:
        return "forbidden", 403
    if p.is_file():
        return send_from_directory(str(p.parent), p.name)
    return "not found", 404

def handle_signal(sig, frame):
    logger.info("Signal %s received, shutting down...", sig)
    sys.exit(0)

import signal
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

if __name__ == "__main__":
    logger.info("Aponi server root: %s", ROOT)
    logger.info("Binding host %s port %s", HOST, PORT)
    if not API_TOKEN:
        logger.warning("APONI_TOKEN is not set. Mutating endpoints and run endpoints are protected and will reject requests.")
    app.run(host=HOST, port=PORT, debug=False, threaded=True)
### END
