import json, os, sys
# Minimal fallback colors; if arena_core.colors exists, prefer that.
try:
    from arena_core.colors import C
except Exception:
    class C:
        HEADER = "\033[95m"; BLUE="\033[94m"; CYAN="\033[96m"
        GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"
        BOLD = "\033[1m"; END = "\033[0m"

_COLOR_MAP = {
    "CYAN": C.CYAN, "BLUE": C.BLUE, "RED": C.RED,
    "GREEN": C.GREEN, "YELLOW": C.YELLOW, "HEADER": C.HEADER, "BOLD": C.BOLD
}

def load_banners(base_dir):
    path = os.path.join(base_dir, "branding", "banners.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def get_banner_text(banners, mode="adaad"):
    item = banners.get(mode) or banners.get("adaad", {})
    color = _COLOR_MAP.get((item.get("color") or "CYAN").upper(), "")
    art_lines = item.get("art", [])
    return f"{color}{C.BOLD}" + "\n".join(art_lines) + f"{C.END}"

def print_banner(base_dir, mode="adaad", stream=None):
    banners = load_banners(base_dir)
    txt = get_banner_text(banners, mode)
    (stream or sys.stdout).write(txt + "\n")
