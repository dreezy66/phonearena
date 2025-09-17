#!/usr/bin/env python3
"""
aponi_launch.py — Single-file ADAAD-ready Aponi server (stdlib-only)

Features:
 - Static file serving + JSON API
 - Safe-path enforcement (ROOT)
 - Token-based protection for mutating endpoints (APONI_TOKEN or X-API-Key/api_key)
 - Atomic writes, create, rename, copy, delete
 - run (blocking) and run_stream (SSE) — runs scripts only inside ROOT
 - Naive per-IP rate limiter
 - Task queue + limited concurrent tasks + cleanup TTL
 - Configurable via env vars

Designed to be easy to run on Termux / Pydroid3 and safe for local / LAN use.
"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
import os, sys, json, time, threading, traceback, shutil, subprocess, uuid, logging
from pathlib import Path
import secrets
import queue

# ---------- Configuration (env overrides) ----------
HOST = os.environ.get("APONI_HOST", "127.0.0.1")     # set to 0.0.0.0 to allow LAN
PORT = int(os.environ.get("APONI_PORT", "8765"))
ROOT = Path(os.environ.get("APONI_ROOT") or (Path.home() / "storage" / "shared" / "ADAAD")).resolve()
API_TOKEN = os.environ.get("APONI_TOKEN", "")       # set to enable protection; empty => dev-open mode
ALLOW_ORIGINS = os.environ.get("APONI_ALLOW_ORIGINS", "*")  # CORS
RUN_TIMEOUT = int(os.environ.get("APONI_RUN_TIMEOUT", "60"))      # seconds for blocking run
MAX_WRITE_BYTES = int(os.environ.get("APONI_MAX_WRITE_BYTES", str(2 * 1024 * 1024)))
RATE_LIMIT_MAX = int(os.environ.get("APONI_RATE_LIMIT_MAX", "60"))  # requests
RATE_LIMIT_WINDOW = int(os.environ.get("APONI_RATE_LIMIT_WINDOW", "60"))  # seconds
MAX_CONCURRENT_STREAMS = int(os.environ.get("APONI_MAX_CONCURRENT_STREAMS", "6"))
TASK_TTL = int(os.environ.get("APONI_TASK_TTL", str(60 * 60)))  # keep finished tasks for N seconds

# ---------- Logging ----------
logger = logging.getLogger("aponi")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ---------- Rate limiter (naive in-memory per-IP) ----------
_rate_store = {}  # ip -> list of timestamps
_rate_lock = threading.Lock()

def rate_allowed(ip):
    now = time.time()
    with _rate_lock:
        arr = _rate_store.get(ip, [])
        arr = [t for t in arr if t > now - RATE_LIMIT_WINDOW]
        if len(arr) >= RATE_LIMIT_MAX:
            return False
        arr.append(now)
        _rate_store[ip] = arr
        return True

# ---------- Tasks / Streams ----------
TASKS = {}       # task_id -> {"q": queue.Queue, "finished_at": None}
TASKS_LOCK = threading.Lock()
_active_streams = 0
_active_streams_lock = threading.Lock()

def spawn_task(q):
    with TASKS_LOCK:
        if len(TASKS) >= 256:
            return None
        tid = str(uuid.uuid4())
        TASKS[tid] = {"q": q, "finished_at": None}
        return tid

def mark_task_done(tid):
    with TASKS_LOCK:
        meta = TASKS.get(tid)
        if meta:
            meta["finished_at"] = time.time()

def cleanup_task_ttl_loop():
    while True:
        now = time.time()
        with TASKS_LOCK:
            for tid, meta in list(TASKS.items()):
                if meta.get("finished_at") and (now - meta["finished_at"] > TASK_TTL):
                    logger.debug("Cleaning task %s", tid)
                    TASKS.pop(tid, None)
        time.sleep(30)

threading.Thread(target=cleanup_task_ttl_loop, daemon=True).start()

# ---------- Helpers ----------
def json_response(handler, obj, status=200):
    body = json.dumps(obj, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", ALLOW_ORIGINS)
    handler.end_headers()
    handler.wfile.write(body)

def text_response(handler, text, status=200, content_type="text/plain; charset=utf-8"):
    body = text.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", ALLOW_ORIGINS)
    handler.end_headers()
    handler.wfile.write(body)

def require_token(handler, optional=False):
    """
    Returns (True, None) if OK; else (False, response_obj)
    """
    if not API_TOKEN:
        if optional:
            return True, None
        # Dev mode: allow but warn
        logger.warning("APONI_TOKEN not set -> running in open dev mode (mutating endpoints unprotected).")
        return True, None
    key = handler.headers.get("X-API-Key") or handler.headers.get("Api-Key") or parse_qs(urlparse(handler.path).query).get("api_key", [None])[0]
    if not key or not secrets.compare_digest(key, API_TOKEN):
        return False, ({"ok": False, "error": "Missing or invalid API key"}, 401)
    return True, None

def safe_path(rel):
    """
    Resolve a user-provided path relative to ROOT, disallow escaping.
    Accepts both absolute (must be under ROOT) or relative paths.
    Returns Path object resolved.
    """
    if not rel:
        raise ValueError("empty path")
    p = Path(unquote(rel))
    if p.is_absolute():
        p = p.resolve()
    else:
        p = (ROOT.joinpath(p)).resolve()
    try:
        p.relative_to(ROOT)
    except Exception:
        raise ValueError("Path outside allowed root")
    return p

def atomic_write(p: Path, content: str):
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(p)

# Small KPI generator (can be extended)
def make_kpis():
    try:
        import psutil
        cpu = int(psutil.cpu_percent(interval=0.1))
        ram = round(psutil.virtual_memory().used / (1024*1024), 1)
        engine = "psutil"
    except Exception:
        import random
        cpu = random.randint(3, 45)
        ram = round(256 + (cpu * 4.2), 1)
        engine = "sim"
    return {
        "active_agents": 12,
        "cycles_per_hr": 24,
        "cpu_percent": cpu,
        "ram_mb": ram,
        "updated_at": time.time(),
        "engine": engine
    }

def make_agents():
    return [
        {"id": "agent-1", "name": "scaffold", "status": "idle"},
        {"id": "agent-2", "name": "repair", "status": "running"},
        {"id": "agent-3", "name": "propose-tests", "status": "idle"},
    ]

# ---------- HTTP Handler ----------
class AponiHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        # set CORS for static + API
        self.send_header("Access-Control-Allow-Origin", ALLOW_ORIGINS)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key, Api-Key")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def _get_ip(self):
        return self.client_address[0] if self.client_address else "local"

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # rate limit
        ip = self._get_ip()
        if not rate_allowed(ip):
            json_response(self, {"ok": False, "error": "rate limit exceeded"}, status=429)
            return

        # small API endpoints
        if path == "/api/kpis":
            json_response(self, {"ok": True, "kpis": make_kpis()})
            return
        if path == "/api/agents":
            json_response(self, {"ok": True, "agents": make_agents()})
            return
        if path == "/api/status":
            json_response(self, {"ok": True, "status": "ok", "root": str(ROOT), "token_protected": bool(API_TOKEN)})
            return
        if path == "/api/stream":
            qs = parse_qs(parsed.query)
            tid = qs.get("task", [None])[0]
            if not tid:
                json_response(self, {"ok": False, "error": "missing task id"}, status=400)
                return
            with TASKS_LOCK:
                meta = TASKS.get(tid)
            if not meta:
                json_response(self, {"ok": False, "error": "invalid or expired task id"}, status=404)
                return
            q = meta["q"]
            # stream SSE
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                while True:
                    try:
                        line = q.get(timeout=30)
                    except queue.Empty:
                        try:
                            self.wfile.write(b": ping\n\n")
                            self.wfile.flush()
                        except BrokenPipeError:
                            break
                        continue
                    payload = line
                    msg = f"data: {json.dumps({'line': payload})}\n\n".encode("utf-8")
                    try:
                        self.wfile.write(msg)
                        self.wfile.flush()
                    except BrokenPipeError:
                        break
                    if payload == "__APOni_TASK_DONE__":
                        mark_task_done(tid)
                        break
            except Exception:
                logger.exception("stream error")
            return

        # default: static file serving from ROOT
        # adjust current directory temporarily so SimpleHTTPRequestHandler serves from ROOT
        cwd = os.getcwd()
        try:
            os.chdir(str(ROOT))
            return super().do_GET()
        finally:
            os.chdir(cwd)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # rate limit
        ip = self._get_ip()
        if not rate_allowed(ip):
            json_response(self, {"ok": False, "error": "rate limit exceeded"}, status=429)
            return

        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else b""
        data = {}
        try:
            if body:
                data = json.loads(body.decode("utf-8"))
        except Exception:
            json_response(self, {"ok": False, "error": "invalid JSON"}, status=400)
            return

        # ---------- LIST ----------
        if path == "/api/list":
            q = data.get("path") or parse_qs(parsed.query).get("path", ["."])[0]
            try:
                p = safe_path(q)
            except Exception as e:
                json_response(self, {"ok": False, "error": str(e)}, status=400)
                return
            if not p.exists():
                json_response(self, {"ok": False, "error": "not found"}, status=404)
                return
            items = []
            try:
                for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                    stat = child.stat()
                    items.append({
                        "name": child.name,
                        "path": str(child.relative_to(ROOT)),
                        "is_dir": child.is_dir(),
                        "size": stat.st_size if child.is_file() else None,
                        "mtime": stat.st_mtime
                    })
                json_response(self, {"ok": True, "path": str(p.relative_to(ROOT)), "items": items})
            except Exception:
                logger.exception("list error")
                json_response(self, {"ok": False, "error": "list error"}, status=500)
            return

        # ---------- READ ----------
        if path == "/api/read":
            q = data.get("path") or parse_qs(parsed.query).get("path", [None])[0]
            if not q:
                json_response(self, {"ok": False, "error": "missing path"}, status=400)
                return
            try:
                p = safe_path(q)
            except Exception as e:
                json_response(self, {"ok": False, "error": str(e)}, status=400)
                return
            if not p.exists() or not p.is_file():
                json_response(self, {"ok": False, "error": "file not found"}, status=404)
                return
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
                json_response(self, {"ok": True, "path": str(p.relative_to(ROOT)), "content": text})
            except Exception:
                logger.exception("read error")
                json_response(self, {"ok": False, "error": "read error"}, status=500)
            return

        # The following endpoints are mutating/protected
        ok, err = require_token(self, optional=False)
        if not ok:
            resp, code = err
            json_response(self, resp, status=code)
            return

        # ---------- WRITE ----------
        if path == "/api/write":
            path_in = data.get("path")
            content = data.get("content", "")
            if not path_in:
                json_response(self, {"ok": False, "error": "missing path"}, status=400)
                return
            if len(content.encode("utf-8")) > MAX_WRITE_BYTES:
                json_response(self, {"ok": False, "error": "content too large"}, status=413)
                return
            try:
                p = safe_path(path_in)
            except Exception as e:
                json_response(self, {"ok": False, "error": str(e)}, status=400)
                return
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                atomic_write(p, content)
                logger.info("Wrote file %s", p)
                json_response(self, {"ok": True, "path": str(p.relative_to(ROOT))})
            except Exception:
                logger.exception("write error")
                json_response(self, {"ok": False, "error": "write error"}, status=500)
            return

        # ---------- CREATE ----------
        if path == "/api/create":
            path_in = data.get("path")
            typ = data.get("type", "file")
            if not path_in:
                json_response(self, {"ok": False, "error": "missing path"}, status=400)
                return
            try:
                p = safe_path(path_in)
            except Exception as e:
                json_response(self, {"ok": False, "error": str(e)}, status=400)
                return
            try:
                if typ == "dir":
                    p.mkdir(parents=True, exist_ok=True)
                else:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text("", encoding="utf-8")
                logger.info("Created %s as %s", p, typ)
                json_response(self, {"ok": True, "path": str(p.relative_to(ROOT))})
            except Exception:
                logger.exception("create error")
                json_response(self, {"ok": False, "error": "create error"}, status=500)
            return

        # ---------- RENAME ----------
        if path == "/api/rename":
            src = data.get("src"); dst = data.get("dst")
            if not src or not dst:
                json_response(self, {"ok": False, "error": "missing src/dst"}, status=400)
                return
            try:
                ps = safe_path(src); pd = safe_path(dst)
            except Exception as e:
                json_response(self, {"ok": False, "error": str(e)}, status=400)
                return
            try:
                pd.parent.mkdir(parents=True, exist_ok=True)
                ps.replace(pd)
                logger.info("Renamed %s -> %s", ps, pd)
                json_response(self, {"ok": True, "src": str(ps.relative_to(ROOT)), "dst": str(pd.relative_to(ROOT))})
            except Exception:
                logger.exception("rename error")
                json_response(self, {"ok": False, "error": "rename error"}, status=500)
            return

        # ---------- COPY ----------
        if path == "/api/copy":
            src = data.get("src"); dst = data.get("dst")
            if not src or not dst:
                json_response(self, {"ok": False, "error": "missing src/dst"}, status=400)
                return
            try:
                ps = safe_path(src); pd = safe_path(dst)
            except Exception as e:
                json_response(self, {"ok": False, "error": str(e)}, status=400)
                return
            try:
                pd.parent.mkdir(parents=True, exist_ok=True)
                if ps.is_dir():
                    shutil.copytree(ps, pd)
                else:
                    shutil.copy2(ps, pd)
                logger.info("Copied %s -> %s", ps, pd)
                json_response(self, {"ok": True, "src": str(ps.relative_to(ROOT)), "dst": str(pd.relative_to(ROOT))})
            except Exception:
                logger.exception("copy error")
                json_response(self, {"ok": False, "error": "copy error"}, status=500)
            return

        # ---------- DELETE ----------
        if path == "/api/delete":
            pth = data.get("path")
            if not pth:
                json_response(self, {"ok": False, "error": "missing path"}, status=400)
                return
            try:
                p = safe_path(pth)
            except Exception as e:
                json_response(self, {"ok": False, "error": str(e)}, status=400)
                return
            try:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
                logger.info("Deleted %s", p)
                json_response(self, {"ok": True})
            except Exception:
                logger.exception("delete error")
                json_response(self, {"ok": False, "error": "delete error"}, status=500)
            return

        # ---------- RUN (blocking) ----------
        if path == "/api/run":
            pth = data.get("path")
            args = data.get("args", [])
            if not pth:
                json_response(self, {"ok": False, "error": "missing path"}, status=400)
                return
            try:
                p = safe_path(pth)
            except Exception as e:
                json_response(self, {"ok": False, "error": str(e)}, status=400)
                return
            if not p.exists():
                json_response(self, {"ok": False, "error": "not found"}, status=404)
                return
            # Only allow running files inside ROOT. No shell expansion.
            cmd = [sys.executable, str(p)] if p.suffix in (".py", ".pyw") else ["/system/bin/sh", str(p)]
            try:
                proc = subprocess.run(cmd + list(map(str, args)), capture_output=True, text=True, timeout=RUN_TIMEOUT)
                json_response(self, {"ok": True, "exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
            except subprocess.TimeoutExpired as te:
                json_response(self, {"ok": False, "error": "timeout", "details": str(te)}, status=500)
            except Exception:
                logger.exception("run error")
                json_response(self, {"ok": False, "error": "run exception"}, status=500)
            return

        # ---------- RUN_STREAM (SSE) ----------
        if path == "/api/run_stream":
            pth = data.get("path") or parse_qs(parsed.query).get("path", [None])[0]
            if not pth:
                json_response(self, {"ok": False, "error": "missing path"}, status=400)
                return
            try:
                p = safe_path(pth)
            except Exception as e:
                json_response(self, {"ok": False, "error": str(e)}, status=400)
                return
            if not p.exists():
                json_response(self, {"ok": False, "error": "not found"}, status=404)
                return

            # enforce concurrency limit
            global _active_streams
            with _active_streams_lock:
                if _active_streams >= MAX_CONCURRENT_STREAMS:
                    json_response(self, {"ok": False, "error": "too many concurrent streams"}, status=429)
                    return
                _active_streams += 1

            q = queue.Queue()
            tid = spawn_task(q)
            if not tid:
                with _active_streams_lock:
                    _active_streams -= 1
                json_response(self, {"ok": False, "error": "task queue full"}, status=503)
                return

            # start background process that writes to queue
            def run_proc_to_queue(tid, q, p):
                try:
                    cmd = [sys.executable, str(p)] if p.suffix in (".py", ".pyw") else ["/system/bin/sh", str(p)]
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    # read stdout and stderr in interleaved fashion
                    while True:
                        out = proc.stdout.readline()
                        err = proc.stderr.readline()
                        if out:
                            q.put(out.rstrip())
                        if err:
                            q.put("[ERR] " + err.rstrip())
                        if out == '' and err == '' and proc.poll() is not None:
                            break
                    q.put("__APOni_TASK_DONE__")
                except Exception as e:
                    q.put("[EXC] " + str(e))
                    q.put("__APOni_TASK_DONE__")
                finally:
                    # mark done time
                    mark_task_done(tid)
                    with _active_streams_lock:
                        global _active_streams
                        _active_streams -= 1

            threading.Thread(target=run_proc_to_queue, args=(tid, q, p), daemon=True).start()
            # return JSON with task id and SSE endpoint for client to connect
            json_response(self, {"ok": True, "task": tid, "sse": f"/api/stream?task={tid}"})
            return

        # unknown POST
        json_response(self, {"ok": False, "error": "unknown POST endpoint"}, status=404)
        return

# ---------- Run server ----------
def main():
    # ensure ROOT exists
    try:
        ROOT.mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.exception("cannot create root")
        sys.exit(1)
    logger.info("Aponi server starting")
    logger.info("Root: %s", ROOT)
    logger.info("Bind: %s:%s (open token=%s)", HOST, PORT, not bool(API_TOKEN))
    server = ThreadingHTTPServer((HOST, PORT), AponiHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down (keyboard interrupt)")
    except Exception:
        logger.exception("Server error")
    finally:
        server.server_close()
        logger.info("Server closed")

if __name__ == "__main__":
    main()