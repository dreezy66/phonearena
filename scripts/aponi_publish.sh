#!/usr/bin/env bash
# ap0ni_publish.sh — build + serve Aponi release (portable, Termux/Pydroid friendly)
set -euo pipefail
IFS=$'\n\t'

# ---------------------------
# Configurable args:
#   $1 ROOT   (default: .)
#   $2 PORT   (default: 8000)
#   $3 MODE   (fg|bg) default fg
#   $4 FORMAT (tar|zip|both) default both
#   $5 KEEP   (int) how many releases to keep, default 12
# ---------------------------

ROOT="${1:-.}"
PORT="${2:-8000}"
MODE="${3:-fg}"
FORMAT="${4:-both}"
KEEP="${5:-12}"

# Normalize
ROOT="$(cd "$ROOT" && pwd -P)"
mkdir -p "$ROOT/.aponi_backups/releases"
mkdir -p "$ROOT/.aponi_backups"

log() { printf '>>> %s\n' "$*"; }
err() { printf '!!! %s\n' "$*' >&2"; }

# Ensure port is numeric (fallback to 8000)
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
  log "Invalid port '$PORT' — using 8000"
  PORT=8000
fi

# temp cleanup
TMPFILES=()
cleanup() {
  for t in "${TMPFILES[@]:-}"; do [ -e "$t" ] && rm -f "$t"; done
}
trap cleanup EXIT INT TERM

TS="$(date +%Y%m%d%H%M%S)"
REL_DIR=".aponi_backups/releases/$TS"
RELEASE_DIR="$ROOT/$REL_DIR"
mkdir -p "$RELEASE_DIR"

log "Building release -> $RELEASE_DIR (format=$FORMAT)"

# optional tree.json regeneration
if [ -x "$ROOT/tree_json.py" ] || [ -f "$ROOT/tree_json.py" ]; then
  log "Regenerating tree.json (best-effort)"
  python3 "$ROOT/tree_json.py" --json . > "$ROOT/tree.json" 2>/dev/null || log "tree_json.py failed (continuing)"
fi

# --- create tar.gz ---
TAR_OUT=""
if [ "$FORMAT" = "tar" ] || [ "$FORMAT" = "both" ]; then
  TAR_OUT="$RELEASE_DIR/aponi_release_${TS}.tar.gz"
  log "Creating tar.gz -> $(basename "$TAR_OUT")"
  (cd "$ROOT" && tar -czf "$TAR_OUT" \
      --exclude='.aponi_backups' \
      --exclude='.git' \
      --exclude='node_modules' \
      --exclude='__pycache__' \
      --exclude='*.pyc' \
      --exclude='*.log' \
      --exclude='.DS_Store' .)
  # symlink if possible, else copy (Android shared storage usually forbids symlinks)
  if ! ln -sfn "$TAR_OUT" "$ROOT/.aponi_backups/latest.tar.gz" 2>/dev/null; then
    cp -f "$TAR_OUT" "$ROOT/.aponi_backups/latest.tar.gz"
  fi
fi

# --- create zip (zip command preferred; python fallback) ---
ZIP_OUT=""
if [ "$FORMAT" = "zip" ] || [ "$FORMAT" = "both" ]; then
  ZIP_OUT="$RELEASE_DIR/aponi_release_${TS}.zip"
  log "Creating zip -> $(basename "$ZIP_OUT")"
  if command -v zip >/dev/null 2>&1; then
    (cd "$ROOT" && zip -q -r "$ZIP_OUT" . \
       -x ".aponi_backups/*" ".git/*" "node_modules/*" "__pycache__/*" "*.pyc" "*.log" ".DS_Store")
  else
    # python fallback
    python3 - <<'PY' "$ROOT" "$ZIP_OUT"
import os,sys,zipfile
root,out=sys.argv[1:]
excl={'.aponi_backups','.git','node_modules','__pycache__'}
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for dp,_,fs in os.walk(root):
        parts = dp.split(os.sep)
        if any(p in excl for p in parts):
            continue
        for f in fs:
            if f.endswith(('.pyc','.log')) or f == '.DS_Store':
                continue
            full = os.path.join(dp, f)
            z.write(full, os.path.relpath(full, root))
print("zip done")
PY
  fi
  if ! ln -sfn "$ZIP_OUT" "$ROOT/.aponi_backups/latest.zip" 2>/dev/null; then
    cp -f "$ZIP_OUT" "$ROOT/.aponi_backups/latest.zip"
  fi
fi

# --- metadata via Python (sha256 + sizes) ---
METADATA_FILE="$RELEASE_DIR/metadata.json"
ARTIFACTS=()
[ -n "$TAR_OUT" ] && [ -f "$TAR_OUT" ] && ARTIFACTS+=("$TAR_OUT")
[ -n "$ZIP_OUT" ] && [ -f "$ZIP_OUT" ] && ARTIFACTS+=("$ZIP_OUT")

python3 - <<'PY' "$TS" "$ROOT" "$METADATA_FILE" "${ARTIFACTS[@]:-}"
import sys,os,json,hashlib
ts,root,meta = sys.argv[1:4]
files = sys.argv[4:]
meta_obj = {"timestamp": ts, "root": root, "artifacts": []}
total = 0
for f in files:
    try:
        s = os.path.getsize(f)
        h = hashlib.sha256()
        with open(f,'rb') as fh:
            for chunk in iter(lambda: fh.read(65536), b''):
                h.update(chunk)
        meta_obj["artifacts"].append({"file": os.path.basename(f), "size": s, "sha256": h.hexdigest()})
        total += s
    except Exception as e:
        meta_obj["artifacts"].append({"file": os.path.basename(f), "error": str(e)})
meta_obj["total_archive_size_bytes"] = total
# reasonably accurate files_count: count files (excluding .aponi_backups)
cnt = 0
for dp,_,fs in os.walk(root):
    if '.aponi_backups' in dp.split(os.sep):
        continue
    cnt += len(fs)
meta_obj["files_count"] = cnt
with open(meta, "w") as fh:
    json.dump(meta_obj, fh, indent=2)
print("metadata written")
PY

log "Metadata written -> $(basename "$METADATA_FILE")"

# --- prune older releases ---
if [ "${KEEP:-0}" -gt 0 ]; then
  PARENT="$ROOT/.aponi_backups/releases"
  if [ -d "$PARENT" ]; then
    TO_REMOVE=$(ls -1d "$PARENT"/*/ 2>/dev/null | sed 's#/$##' | sed 's#.*/##' | sort | head -n -"${KEEP}" || true)
    if [ -n "$TO_REMOVE" ]; then
      log "Pruning old releases (keeping $KEEP)..."
      for d in $TO_REMOVE; do
        log " - removing $d"
        rm -rf "$PARENT/$d"
      done
    fi
  fi
fi

# --- pick artifact to serve (prefer tar then zip) ---
TARGET=""
if [ -f "$ROOT/.aponi_backups/latest.tar.gz" ]; then
  TARGET="$ROOT/.aponi_backups/latest.tar.gz"
elif [ -f "$ROOT/.aponi_backups/latest.zip" ]; then
  TARGET="$ROOT/.aponi_backups/latest.zip"
fi

if [ -z "$TARGET" ] || [ ! -f "$TARGET" ]; then
  log "ERROR: no artifact to serve (expected latest.tar.gz or latest.zip)"
  exit 1
fi

SERVE_DIR=$(dirname "$TARGET")
BASENAME=$(basename "$TARGET")
URL="http://127.0.0.1:${PORT}/${BASENAME}"

log "Serving: $TARGET"
log "URL: $URL"

# rotate ap0ni_share.log (keep 5 logs)
LOGFILE="$ROOT/aponi_share.log"
if [ -f "$LOGFILE" ]; then
  for i in 4 3 2 1; do
    [ -f "$LOGFILE.$i" ] && mv "$LOGFILE.$i" "$LOGFILE.$((i+1))"
  done
  mv "$LOGFILE" "$LOGFILE.1"
fi

# show QR (if qrcode_terminal installed)
python3 - "$URL" <<'PY' || true
import sys
try:
    import qrcode_terminal
    qrcode_terminal.draw(sys.argv[1])
except Exception:
    print("(QR skipped — install qrcode-terminal or qrcode_terminal to show ASCII QR)")
PY

# try to copy to Android clipboard if available
if command -v termux-clipboard-set >/dev/null 2>&1; then
  log "Copying URL to Android clipboard"
  printf '%s' "$URL" | termux-clipboard-set
fi

# --- start server ---
cd "$SERVE_DIR"
if [ "$MODE" = "bg" ]; then
  nohup python3 -m http.server "$PORT" --bind 0.0.0.0 &> "$LOGFILE" &
  pid=$!
  log "Server started in background (pid=$pid, log=$LOGFILE)"
  log "Download: $URL"
  printf '%s\n' "$pid" > "$ROOT/.aponi_backups/last_server.pid"
else
  log "Foreground mode — Ctrl-C to stop (serving $BASENAME on port $PORT)"
  python3 -m http.server "$PORT" --bind 0.0.0.0
fi