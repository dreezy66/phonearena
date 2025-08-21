import os, json
from .marketplace_auto import _load_marketplace, _save_marketplace

def prune_low_performers(min_score=50):
    listings = _load_marketplace()
    filtered = [l for l in listings if l['score'] >= min_score]
    _save_marketplace(filtered)
    print(f"[Marketplace] Pruned {len(listings)-len(filtered)} low-score agents")
