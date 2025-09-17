#!/usr/bin/env python3
from core.phonearena_core import read_marketplace
import json
def run():
    listings = read_marketplace()
    if not listings: return "No listings"
    return json.dumps(listings, indent=2)
