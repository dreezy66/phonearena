#!/usr/bin/env python3
# aponi_tree_full.py — ADAAD / Aponi full file tree + sizes + agent tags + HTML/JSON export + optional serve
# Stdlib-only, optimized for Termux / Pydroid3 / Linux
from __future__ import annotations
import argparse
import base64
import concurrent.futures
import html
import hashlib
import http.server
import json
import os
import socketserver
import sys
import time
import traceback
import webbrowser
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ----------------------
# Configuration (NO DEFAULT EXCLUDES)
# ----------------------
DEFAULT_EXCLUDE_DIR_PATTERNS: List[str] = []   # empty -> include everything by default
DEFAULT_EXCLUDE_FILE_PATTERNS: List[str] = []  # empty -> include everything by default

AGENT_FILENAME_TAGS = [
    ("beast", ["beastv", "beast"]),
    ("improved", ["improved", "_improved_"]),
    ("needs_repair", ["needs_repair", "needs-repair", "needsrepair"]),
    ("generated", ["agent_", "generated_agents", "agent_initial_seed", "good_agent"]),
    ("quarantine", ["quarantine", ".quarantine"]),
]

RUNTIME_WHITELIST = {
    "core", "agents", "generated_agents", "plugins", "bin", "scripts", "remote_worker",
    "marketing", "main.py", "run_adaad.sh", "adaad_env.sh", "adaad_logs", "quarantine",
    "recovered_sources", "marketplace_data", "data",
}

# extension -> emoji/icon (feel free to change to class names if you use CSS icons)
ICON_MAP = {
    'dir': '📂',
    'symlink': '🔗',
    '.py': '🐍',
    '.md': '📘',
    '.json': '🧾',
    '.yml': '🧾',
    '.yaml': '🧾',
    '.html': '🌐',
    '.htm': '🌐',
    '.js': '🟨',
    '.css': '🎨',
    '.png': '🖼️',
    '.jpg': '🖼️',
    '.jpeg': '🖼️',
    '.gif': '🖼️',
    '.svg': '🖼️',
    '.mp3': '🎵',
    '.wav': '🎵',
    '.ogg': '🎵',
    '.mp4': '🎬',
    '.mkv': '🎬',
    '.zip': '🗜️',
    '.tar': '🗜️',
    '.gz': '🗜️',
    '.pdf': '📕',
    '.exe': '⚙️',
    '.sh': '🐚',
    '.lock': '🔒',
    '.txt': '📄',
    'unknown': '❓',
}

# ----------------------
# Data structures
# ----------------------
@dataclass
class Node:
    path: str                # relative path from root ('.' for root)
    name: str
    is_dir: bool
    size: int = 0            # bytes (for dirs: aggregated)
    mtime: float = 0.0
    tag: Optional[str] = None
    health: Optional[str] = None
    sha256: Optional[str] = None
    children: List["Node"] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # ensure children is list
        if self.children is None:
            d["children"] = []
        else:
            d["children"] = [c.to_dict() for c in self.children]
        return d

# ----------------------
# Helpers
# ----------------------
def detect_aponi_root() -> Path:
    """
    Auto-detect common Aponi locations used on Android/Termux.
    Preference order:
     - /storage/emulated/0/ADAAD/Aponi
     - /storage/emulated/0/ADAAD
     - ~/storage/shared/ADAAD/Aponi (Termux)
     - current working directory
    """
    candidates = [
        Path("/storage/emulated/0/ADAAD/Aponi"),
        Path("/storage/emulated/0/ADAAD"),
        Path.home() / "storage" / "shared" / "ADAAD" / "Aponi",
        Path.cwd(),
    ]
    for p in candidates:
        try:
            if p.exists() and p.is_dir():
                # prefer explicit "Aponi" folder if present
                if "Aponi" in p.name or str(p).endswith("/ADAAD"):
                    return p.resolve()
        except Exception:
            continue
    return Path.cwd().resolve()

def human_size(n: int) -> str:
    if n < 1024:
        return f"{n}B"
    for unit in ("KB", "MB", "GB", "TB"):
        n /= 1024.0
        if n < 1024.0:
            return f"{n:.1f}{unit}"
    return f"{n:.1f}PB"

def icon_for(path: Path, is_dir: bool, is_symlink: bool) -> str:
    if is_dir:
        return ICON_MAP.get('dir')
    if is_symlink:
        return ICON_MAP.get('symlink')
    ext = path.suffix.lower()
    return ICON_MAP.get(ext, ICON_MAP.get('unknown'))

def detect_agent_tag(path: Path) -> Optional[str]:
    s = str(path).lower()
    name = path.name.lower()
    for tag, toks in AGENT_FILENAME_TAGS:
        for t in toks:
            if t in name or t in s:
                return tag
    # fallback heuristics
    if "agent" in name:
        return "generated"
    return None

def analyze_agent_content(text: str) -> str:
    """Heuristic health measurement from file content (caller should compile to detect syntax)."""
    lowered = text.lower()
    if any(k in lowered for k in ("def run(", "def main(", "if __name__")):
        return "ok"
    if "class agent" in lowered or "class agent(" in lowered:
        return "ok"
    return "warn"

def file_sha256(path: Path, block_size: int = 1 << 16) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(block_size), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

# ----------------------
# Tree builder (fast, iterative). NO default excludes.
# Supports optional parallel hashing/agent analysis.
# ----------------------
def build_tree(root: Path,
               max_depth: Optional[int] = None,
               exclude_dirs: List[str] = None,
               exclude_files: List[str] = None,
               focus: str = "all",
               do_hash: bool = False,
               hash_workers: int = 4) -> Tuple[Node, Dict[str,int]]:
    """
    Iterative scan using os.scandir for speed and memory efficiency.
    do_hash: compute SHA256 for files in parallel (thread pool)
    Returns (root_node, summary)
    """
    if exclude_dirs is None:
        exclude_dirs = DEFAULT_EXCLUDE_DIR_PATTERNS[:]
    if exclude_files is None:
        exclude_files = DEFAULT_EXCLUDE_FILE_PATTERNS[:]

    root = root.resolve()
    summary = {"dirs": 0, "files": 0, "agents": 0, "bytes": 0}

    nodes_by_path: Dict[str, Node] = {}
    file_tasks_for_hash: List[Path] = []
    agent_file_candidates: List[Path] = []

    stack: List[Tuple[Path, int, Optional[Path]]] = [(root, 0, None)]

    while stack:
        p, depth, parent = stack.pop()
        try:
            st = p.stat() if p.exists() else None
        except Exception:
            st = None

        rel_path = "." if p == root else str(p.relative_to(root))
        node = Node(
            path=rel_path,
            name=p.name if p != root else (root.name or str(root)),
            is_dir=p.is_dir() if p.exists() else False,
            size=0,
            mtime=float(st.st_mtime) if st else 0.0,
            children=[]
        )
        nodes_by_path[str(p)] = node

        if max_depth is not None and depth > max_depth:
            continue

        if p.is_dir():
            # try scandir
            try:
                with os.scandir(p) as it:
                    entries = list(it)
            except PermissionError:
                entries = []
            except FileNotFoundError:
                entries = []
            # push children (reverse sort for natural DFS)
            entries.sort(key=lambda e: (not e.is_dir(), e.name.lower()), reverse=True)
            for ent in entries:
                # Note: user requested NO default excludes, but we still accept user-supplied ones.
                if ent.is_dir(follow_symlinks=False) and any(ent.name.lower().startswith(pat.lower().rstrip("*")) for pat in (exclude_dirs or [])):
                    # if user provided explicit exclude patterns, honor them
                    continue
                if ent.is_file(follow_symlinks=False) and any(ent.name.lower().startswith(pat.lower().rstrip("*")) for pat in (exclude_files or [])):
                    continue

                # focus filter: when runtime focus, keep only whitelisted folders
                if focus == "runtime":
                    allowed = any(w in ent.path for w in RUNTIME_WHITELIST) or any(w in str(p) for w in RUNTIME_WHITELIST)
                    if not allowed:
                        continue
                stack.append((Path(ent.path), depth + 1, p))
        else:
            # file: record size and candidates for hashing / agent analysis
            try:
                st = p.stat()
                node.size = int(st.st_size)
                node.mtime = float(st.st_mtime)
                summary["files"] += 1
                summary["bytes"] += node.size
            except Exception:
                node.size = 0

            if p.suffix == ".py":
                # heuristics: files that live in "agents" folders OR contain "agent" in name
                parts = [part.lower() for part in p.parts]
                if "agents" in parts or "generated_agents" in parts or "agent" in p.name.lower():
                    summary["agents"] += 1
                    agent_file_candidates.append(p)
            # schedule for hashing if requested
            if do_hash:
                file_tasks_for_hash.append(p)

    # assemble tree by parent relationships
    for abs_path_str, node in nodes_by_path.items():
        abs_path = Path(abs_path_str)
        if abs_path == root:
            continue
        parent = abs_path.parent
        parent_node = nodes_by_path.get(str(parent))
        if parent_node is not None:
            parent_node.children.append(node)

    # compute aggregated sizes (post-order)
    def aggregate(n: Node) -> int:
        if not n.is_dir:
            return n.size
        total = 0
        for c in n.children:
            total += aggregate(c)
        n.size = total
        return n.size

    root_node = nodes_by_path.get(str(root))
    if root_node:
        aggregate(root_node)
        summary["dirs"] = sum(1 for n in nodes_by_path.values() if n.is_dir)

    # parallel SHA256
    if do_hash and file_tasks_for_hash:
        def hash_worker(p: Path) -> Tuple[str, Optional[str]]:
            return (str(p), file_sha256(p))
        with concurrent.futures.ThreadPoolExecutor(max_workers=hash_workers) as ex:
            futures = [ex.submit(hash_worker, p) for p in file_tasks_for_hash]
            for f in concurrent.futures.as_completed(futures):
                try:
                    pstr, digest = f.result()
                except Exception:
                    continue
                # attach digest if present
                node = nodes_by_path.get(pstr)
                if node:
                    node.sha256 = digest

    # parallel agent analysis (compile + heuristics)
    if agent_file_candidates:
        def agent_worker(p: Path) -> Tuple[str, Optional[str], Optional[str]]:
            # returns (path, tag, health)
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return (str(p), detect_agent_tag(p), "unknown")
            # try compile to detect syntax errors
            try:
                compile(text, str(p), "exec")
            except SyntaxError:
                return (str(p), detect_agent_tag(p), "broken")
            except Exception:
                # non-syntax exception, still try heuristic
                return (str(p), detect_agent_tag(p), analyze_agent_content(text))
            # compiled OK -> run heuristics
            return (str(p), detect_agent_tag(p), analyze_agent_content(text))

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, max(2, os.cpu_count() or 2))) as ex:
            futures = [ex.submit(agent_worker, p) for p in agent_file_candidates]
            for f in concurrent.futures.as_completed(futures):
                try:
                    pstr, tag, health = f.result()
                except Exception:
                    continue
                node = nodes_by_path.get(pstr)
                if node:
                    node.tag = tag
                    node.health = health

    return root_node, summary

# ----------------------
# Console tree printing (pretty)
# ----------------------
def print_tree_console(node: Node, prefix: str = "") -> None:
    def _print(n: Node, pref: str):
        icon = ICON_MAP.get('dir') if n.is_dir else ICON_MAP.get(Path(n.name).suffix.lower(), ICON_MAP.get('unknown'))
        size_text = f" ({human_size(n.size)})" if n.size else ""
        tag_text = f" [{n.tag}]" if n.tag else ""
        health_text = f" [{n.health}]" if n.health else ""
        print(f"{pref}{icon} {n.name}{'/' if n.is_dir else ''}{size_text}{tag_text}{health_text}")
        if n.children:
            for i, c in enumerate(sorted(n.children, key=lambda x: (not x.is_dir, x.name.lower()))):
                next_pref = pref + ("    " if i == len(n.children)-1 else "│   ")
                _print(c, pref + ("└── " if i == len(n.children)-1 else "├── "))
    _print(node, prefix)

# ----------------------
# HTML template (client-rendered with embedded base64 JSON)
# ----------------------
HTML_TEMPLATE = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>ADAAD / Aponi — File Tree</title>
<style>
:root{--bg:#071226;--panel:#0b1220;--muted:#a7b6c9;--accent:#7c3aed;--glass:rgba(255,255,255,0.03)}
html,body{height:100%;margin:0;background:linear-gradient(180deg,var(--bg),#020617);font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;color:#e6eef8}
.header{padding:12px;display:flex;gap:12px;align-items:center}
.controls{margin-left:auto;display:flex;gap:8px}
.container{display:flex;gap:12px;padding:12px}
.sidebar{width:340px}
.card{background:var(--panel);padding:12px;border-radius:12px;box-shadow:0 8px 30px rgba(2,6,23,0.6);margin-bottom:12px}
.tree-area{flex:1;min-height:60vh;overflow:auto;padding:12px;background:linear-gradient(180deg,rgba(255,255,255,0.02),transparent);border-radius:12px}
.node{padding:6px 8px;border-radius:8px;margin:4px 0;display:flex;align-items:center;gap:8px}
.node .meta{color:var(--muted);font-size:12px;margin-left:auto}
.folder{cursor:pointer;font-weight:700}
.badge{display:inline-block;padding:4px 8px;border-radius:999px;background:rgba(255,255,255,0.03);color:var(--muted);font-size:12px;margin-left:6px}
.tag-beast{color:#ffd166}
.tag-improved{color:#ffb4a2}
.tag-generated{color:#bde0fe}
.tag-needs_repair{color:#ffb677}
.tag-quarantine{color:#ff7b7b}
.health-ok{background:linear-gradient(90deg,#042, #146); color:#dfffe0}
.health-warn{background:linear-gradient(90deg,#432,#aa6); color:#fff6df}
.health-broken{background:linear-gradient(90deg,#a22,#f66); color:#fff0f0}
.small{font-size:13px;color:var(--muted)}
.search{width:100%;padding:8px;border-radius:8px;border:1px solid rgba(255,255,255,0.03);background:transparent;color:inherit}
.controls-row{display:flex;gap:8px;align-items:center}
.footer{font-size:12px;color:var(--muted);padding:8px;text-align:center}
</style>
</head>
<body>
  <div class="header">
    <div style="font-weight:900;font-size:18px">ADAAD / Aponi — File Explorer</div>
    <div class="controls">
      <input id="search" class="search" placeholder="filter name, tag, health, path" />
      <select id="sort">
        <option value="name">Sort: name</option>
        <option value="size">Sort: size</option>
        <option value="mtime">Sort: mtime</option>
      </select>
      <label title="Only show nodes with agent tags"><input id="only-agents" type="checkbox" /> only agents</label>
      <button id="download-json">Download JSON</button>
      <button id="refresh">Refresh</button>
    </div>
  </div>
  <div class="container">
    <div class="sidebar">
      <div class="card">
        <div style="font-weight:700">Summary</div>
        <div class="small" id="summary">—</div>
      </div>
      <div class="card">
        <div style="font-weight:700">Quick actions</div>
        <div style="margin-top:8px" class="small">
          <div><button id="expand-all">Expand all</button> <button id="collapse-all">Collapse all</button></div>
          <div style="margin-top:8px">Tip: click folder names to collapse/expand. Use search to quickly find agents.</div>
        </div>
      </div>
      <div class="card">
        <div style="font-weight:700">Legend</div>
        <div class="small">
          <div>📂 folder &nbsp; 📄 file</div>
          <div><span class="badge tag-beast">beast</span> <span class="badge tag-improved">improved</span> <span class="badge tag-generated">generated</span></div>
          <div style="margin-top:6px"><span class="badge health-ok">ok</span> <span class="badge health-warn">warn</span> <span class="badge health-broken">broken</span></div>
        </div>
      </div>
    </div>

    <div class="tree-area" id="tree-area" tabindex="0">
      Loading...
    </div>
  </div>

  <div class="footer" id="footer"></div>

<script>
/* JSON data is injected as a base64 blob to be safe with special chars */
const base64_json = "{json_b64}";
const raw = JSON.parse(atob(base64_json));
const root = raw.root;
const summary = raw.summary;

function fmtSize(n){
  if(!n) return "";
  if(n<1024) return n + "B";
  let units=["KB","MB","GB","TB"], v=n/1024, i=0;
  while(v>=1024 && i<units.length-1){ v/=1024; i++; }
  return v.toFixed(1)+units[i];
}

function createNodeElement(n, depth=0){
  const el = document.createElement("div");
  el.className = "node " + (n.is_dir ? "folder" : "file");
  el.dataset.path = n.path || "";
  el.style.paddingLeft = (depth * 14) + "px";
  const ico = document.createElement("span");
  ico.textContent = n.is_dir ? "📂" : (n.name.split('.').length>1 ? "📄" : "📄");
  ico.style.minWidth = "18px";
  el.appendChild(ico);

  const title = document.createElement("span");
  title.textContent = n.name + (n.is_dir ? "/" : "");
  title.style.fontWeight = n.is_dir ? "700" : "400";
  el.appendChild(title);

  const meta = document.createElement("span");
  meta.className = "meta";
  meta.textContent = (n.is_dir ? fmtSize(n.size) : (n.sha256 ? "sha256:" + n.sha256.slice(0,8) : fmtSize(n.size)));
  el.appendChild(meta);

  if(n.tag){
    const t = document.createElement("span");
    t.className = "badge tag-" + n.tag;
    t.textContent = n.tag;
    el.appendChild(t);
  }
  if(n.health){
    const h = document.createElement("span");
    h.className = "badge health-" + n.health;
    h.textContent = n.health;
    el.appendChild(h);
  }
  // attach children container (for folders)
  if(n.is_dir){
    const container = document.createElement("div");
    container.dataset.parent = n.path;
    container.style.display = "none"; // collapsed by default
    el.addEventListener("click", (ev)=>{
      if(ev.target === el || ev.target === title || ev.target === ico) {
        container.style.display = container.style.display === "none" ? "" : "none";
      }
    });
    // render children lazily
    if(n.children && n.children.length){
      for(const c of n.children){
        container.appendChild(createNodeElement(c, depth+1));
      }
    }
    return el.outerHTML + container.outerHTML;
  } else {
    return el.outerHTML;
  }
}

function buildTreeArea(){
  const area = document.getElementById("tree-area");
  area.innerHTML = "";
  const html = createNodeElement(root, 0);
  area.innerHTML = html;
  applyFilter();
}

function applyFilter(){
  const q = document.getElementById("search").value.trim().toLowerCase();
  const onlyAgents = document.getElementById("only-agents").checked;
  document.querySelectorAll("[data-path]").forEach(el=>{
    const name = (el.textContent || "").toLowerCase();
    const path = el.getAttribute("data-path") || "";
    const matchesQ = !q || name.includes(q) || path.includes(q);
    const matchesAgent = !onlyAgents || /beast|improved|generated|needs_repair|quarantine/.test(name);
    el.style.display = (matchesQ && matchesAgent) ? "" : "none";
  });
}

document.getElementById("search").addEventListener("input", applyFilter);
document.getElementById("only-agents").addEventListener("change", applyFilter);
document.getElementById("refresh").addEventListener("click", ()=> location.reload());
document.getElementById("download-json").addEventListener("click", ()=>{
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(raw, null, 2));
  const a = document.createElement("a"); a.href = dataStr; a.download = "aponi_tree.json"; document.body.appendChild(a); a.click(); a.remove();
});
document.getElementById("expand-all").addEventListener("click", ()=>{
  document.querySelectorAll('[data-parent]').forEach(d=>d.style.display = "");
});
document.getElementById("collapse-all").addEventListener("click", ()=>{
  document.querySelectorAll('[data-parent]').forEach(d=>d.style.display = "none");
});

(function populateSummary(){
  const s = document.getElementById("summary");
  s.innerHTML = `<div style="font-weight:700">${summary.files} files • ${summary.dirs} dirs • ${summary.agents} agents</div><div class="small">Total size: ${fmtSize(summary.bytes)}</div>`;
})();
buildTreeArea();

document.getElementById("sort").addEventListener("change", (ev)=>{
  // quick client-side sort by re-render; sort preference only affects display order inside JS objects
  const v = ev.target.value;
  function sortNode(n){
    if(!n.children) return;
    if(v === "name") n.children.sort((a,b)=> a.name.localeCompare(b.name));
    if(v === "size") n.children.sort((a,b)=> b.size - a.size);
    if(v === "mtime") n.children.sort((a,b)=> (b.mtime||0) - (a.mtime||0));
    n.children.forEach(sortNode);
  }
  sortNode(root);
  buildTreeArea();
});
</script>
</body>
</html>
"""

# ----------------------
# CLI & main
# ----------------------
def parse_args():
    p = argparse.ArgumentParser(description="ADAAD / Aponi full tree explorer — sizes, tags, health, HTML/JSON export")
    p.add_argument("--root", "-r", default=None, help="Root path (auto-detected if omitted)")
    p.add_argument("--out-html", default="adaad_tree_full.html", help="Write interactive HTML to this file (relative to root)")
    p.add_argument("--out-json", default="adaad_tree_full.json", help="Write JSON to this file (relative to root)")
    p.add_argument("--max-depth", type=int, default=None, help="Limit recursion depth (optional)")
    p.add_argument("--focus", choices=("all", "runtime"), default="all", help="Focus: 'all' or 'runtime' (whitelist)")
    p.add_argument("--exclude-dir", action="append", help="Exclude dir glob pattern (can repeat)")
    p.add_argument("--exclude-file", action="append", help="Exclude file glob pattern (can repeat)")
    p.add_argument("--serve", action="store_true", help="Start lightweight HTTP server to serve HTML/JSON (uses http.server)")
    p.add_argument("--port", type=int, default=8766, help="Port to serve on when --serve is used (default 8766)")
    p.add_argument("--no-console", action="store_true", help="Don't print console tree output (useful for scripts)")
    p.add_argument("--hash", action="store_true", help="Compute SHA256 for all files (parallel; may be slow)")
    p.add_argument("--hash-workers", type=int, default=6, help="Number of worker threads for hashing")
    p.add_argument("--gzip", action="store_true", help="Write a gzip-compressed JSON as <out-json>.gz")
    p.add_argument("--open", action="store_true", help="When --serve is used, open the browser automatically")
    return p.parse_args()

def main():
    args = parse_args()
    if args.root:
        root = Path(args.root).expanduser().resolve()
    else:
        root = detect_aponi_root()

    if not root.exists():
        print("Root not found:", root, file=sys.stderr)
        sys.exit(2)

    # override default excludes only if user supplied patterns
    exclude_dirs = DEFAULT_EXCLUDE_DIR_PATTERNS[:]
    exclude_files = DEFAULT_EXCLUDE_FILE_PATTERNS[:]
    if args.exclude_dir:
        exclude_dirs.extend(args.exclude_dir)
    if args.exclude_file:
        exclude_files.extend(args.exclude_file)

    print(f"Scanning root: {root}")
    start = time.time()
    try:
        root_node, summary = build_tree(root,
                                       max_depth=args.max_depth,
                                       exclude_dirs=exclude_dirs,
                                       exclude_files=exclude_files,
                                       focus=args.focus,
                                       do_hash=args.hash,
                                       hash_workers=max(1, args.hash_workers))
    except Exception as e:
        print("Scan failed:", e)
        traceback.print_exc()
        sys.exit(1)
    elapsed = time.time() - start
    print(f"Scan finished in {elapsed:.2f}s — {summary['files']} files, {summary['dirs']} dirs, {summary['agents']} agents, {human_size(summary['bytes'])}")

    # prepare JSON object
    json_obj = {
        "root": root_node.to_dict() if root_node else {},
        "summary": summary,
        "generated_at": time.time(),
        "root_path": str(root),
    }
    # write JSON
    out_json_path = Path(args.out_json) if Path(args.out_json).is_absolute() else (root / args.out_json)
    try:
        out_json_path.write_text(json.dumps(json_obj, indent=2), encoding="utf-8")
        print("JSON exported to:", out_json_path)
        if args.gzip:
            import gzip
            gz_path = str(out_json_path) + ".gz"
            with gzip.open(gz_path, "wb") as gz:
                gz.write(json.dumps(json_obj).encode("utf-8"))
            print("Gzipped JSON exported to:", gz_path)
    except Exception as e:
        print("Failed to write JSON:", e)

    # write HTML (embed base64 JSON to avoid JS parsing edge cases)
    try:
        out_html_path = Path(args.out_html) if Path(args.out_html).is_absolute() else (root / args.out_html)
        json_blob = json.dumps(json_obj, separators=(",", ":"), ensure_ascii=False)
        json_b64 = base64.b64encode(json_blob.encode("utf-8")).decode("ascii")
        html_out = HTML_TEMPLATE.replace("{json_b64}", json_b64)
        out_html_path.write_text(html_out, encoding="utf-8")
        print("HTML exported to:", out_html_path)
    except Exception as e:
        print("Failed to write HTML:", e)

    # Console tree
    if not args.no_console and root_node:
        print()
        print_tree_console(root_node)
        print()

    # serve if requested
    if args.serve:
        try:
            os.chdir(str(root))
            handler = http.server.SimpleHTTPRequestHandler
            with socketserver.TCPServer(("0.0.0.0", args.port), handler) as httpd:
                url = f"http://127.0.0.1:{args.port}/{out_html_path.name}"
                print(f"Serving {root} at {url} (Ctrl+C to quit)")
                if args.open:
                    try:
                        webbrowser.open(url)
                    except Exception:
                        pass
                try:
                    httpd.serve_forever()
                except KeyboardInterrupt:
                    print("Stopping server…")
        except Exception as e:
            print("Failed to start server:", e)

if __name__ == "__main__":
    main()