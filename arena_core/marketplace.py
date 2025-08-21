# marketplace.py — simple dashboard utilities
import os
from .io_utils import safe_read_json, safe_write_json

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MARKET_FILE = os.path.join(BASE, "marketplace_data", "listings.json")

def list_agents_for_sale():
    listings = safe_read_json(MARKET_FILE) or []
    if not listings:
        print("No agents listed in marketplace.")
        return
    print("=== Marketplace Listings ===")
    for i, l in enumerate(listings, 1):
        print(f"{i}. {l.get('name')} | ${l.get('price')} | score={l.get('score')}")
    print("===========================")

def add_agent_to_market(agent_name, price, author="PhoneArena", score=0, description=""):
    listings = safe_read_json(MARKET_FILE) or []
    if any(l.get("name") == agent_name for l in listings):
        print("Agent already listed.")
        return False
    listings.append({
        "name": agent_name,
        "author": author,
        "price": float(price),
        "score": score,
        "description": description,
        "tags": []
    })
    safe_write_json(MARKET_FILE, listings)
    print(f"Added {agent_name} to marketplace for ${price}")
    return True

def remove_agent_from_market(agent_name):
    listings = safe_read_json(MARKET_FILE) or []
    new = [l for l in listings if l.get("name") != agent_name]
    if len(new) == len(listings):
        print("Agent not found.")
        return False
    safe_write_json(MARKET_FILE, new)
    print(f"Removed {agent_name} from marketplace.")
    return True
