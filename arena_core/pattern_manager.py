import os, json, ast

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PATTERN_FILE = os.path.join(BASE, "patterns.json")

# Ensure file exists
if not os.path.exists(PATTERN_FILE):
    with open(PATTERN_FILE, "w") as f:
        json.dump({}, f, indent=2)

def get_all_patterns():
    try:
        with open(PATTERN_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_pattern(agent_name, code_snippet):
    """
    Save a code snippet pattern under agent_name.
    """
    patterns = get_all_patterns()
    if agent_name not in patterns:
        patterns[agent_name] = []
    if code_snippet not in patterns[agent_name]:
        patterns[agent_name].append(code_snippet)
    with open(PATTERN_FILE, "w") as f:
        json.dump(patterns, f, indent=2)

def extract_top_snippets(agent_path, max_lines=10):
    """
    Extract top snippets from an agent source code for pattern storage.
    Naive implementation: save last max_lines lines.
    """
    try:
        with open(agent_path) as f:
            lines = f.readlines()
        snippet = "".join(lines[-max_lines:]).strip()
        return snippet
    except Exception:
        return ""
