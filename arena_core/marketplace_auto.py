# marketplace_auto.py — auto-list agents safely
import os
from .io_utils import safe_read_json, safe_write_json

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MARKET_FILE = os.path.join(BASE, "marketplace_data", "listings.json")

def _load_listings():
    return safe_read_json(MARKET_FILE) or []

def _save_listings(lst):
    return safe_write_json(MARKET_FILE, lst)

def auto_list_agents(agents=None, top_n=5):
    """
    Auto-list top agents into marketplace_data/listings.json.
    agents: list of Agent objects or dicts. If None, attempt to import agent_runtime.get_agents().
    top_n: how many to list.
    This function is synchronous and safe to call from main runtime.
    """
    # (local import to avoid circular import)
    if agents is None:
        try:
            from .agent_runtime import get_agents
            agents = get_agents()
        except Exception:
            agents = []

    normalized = []
    for a in agents:
        try:
            # support Agent objects or dicts
            if hasattr(a, "name"):
                name = getattr(a, "name")
                score = getattr(a, "score", 0)
            elif isinstance(a, dict):
                name = a.get("name") or a.get("filename")
                score = a.get("score", 0)
            else:
                continue
            if not name:
                continue
            price = round(10 + (float(score) if score else 0) / 10, 2)
            normalized.append({"name": name, "price": price, "score": score})
        except Exception:
            continue

    # sort by score desc
    top = sorted(normalized, key=lambda x: x.get("score", 0), reverse=True)[:top_n]
    listings = _load_listings()
    existing = {l.get("name") for l in listings}
    added = []
    for t in top:
        if t["name"] in existing:
            continue
        listings.append({
            "name": t["name"],
            "author": "PhoneArena",
            "price": t["price"],
            "score": t["score"],
            "description": f"Auto-listed agent (score={t['score']})",
            "tags": ["auto", "beast"]
        })
        existing.add(t["name"])
        added.append(t["name"])
    _save_listings(listings)
    return added
