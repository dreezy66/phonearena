import os, json, time
from .marketplace_auto import auto_list_agents, _load_marketplace, _save_marketplace
from .gui_dashboard import run_dashboard

MARKETPLACE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "marketplace_data", "listings.json"))

def update_marketplace_gui(top_n=5):
    auto_list_agents(top_n=top_n)
    # After auto-listing, refresh dashboard to show updated listings
    listings = _load_marketplace()
    print("\n=== Updated Marketplace Listings ===")
    for item in listings:
        print(f"{item['name']} | Price: ${item['price']} | Score: {item['score']} | Tags: {', '.join(item['tags'])}")
    # Optional: run full dashboard
    run_dashboard()

def dynamic_pricing():
    listings = _load_marketplace()
    for item in listings:
        # Increase price if score improved since last listing
        item['price'] = round(10 + item['score']/10, 2)
    _save_marketplace(listings)
    print("[Marketplace] Dynamic pricing updated.")
