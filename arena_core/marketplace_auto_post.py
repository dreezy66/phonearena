# marketplace_auto_post.py — auto-list new agents after creation
import os, json
from arena_core.marketplace_auto import _load, _save
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MARKET_FILE = os.path.join(BASE, "marketplace_data", "listings.json")

def post_agents(new_agents):
    """
    new_agents: list of agent objects with name, score attributes
    Automatically lists new agents to marketplace with dynamic price & metadata
    """
    if not new_agents:
        return

    listings = _load()
    existing_names = {l.get("name") for l in listings}

    for a in new_agents:
        try:
            name = getattr(a, "name", None)
            score = getattr(a, "score", 0)
            if name in existing_names:
                continue
            price = round(10 + score/10, 2)
            listings.append({
                "name": name,
                "author": "PhoneArena",
                "price": price,
                "score": score,
                "description": f"Auto-listed agent (score={score})",
                "tags": ["auto", "beast", "new"]
            })
            print(f"[MarketplaceAutoPost] Listed {name} for ${price}")
        except Exception as e:
            print("[MarketplaceAutoPost] Failed to post agent:", e)

    _save(listings)
