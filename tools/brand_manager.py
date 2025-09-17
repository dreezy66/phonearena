#!/usr/bin/env python3
import os, json, random, time
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BFILE = os.path.join(BASE, "branding", "banners.json")
LOG = os.path.join(BASE, "branding", "brand_manager.log")

def rotate_seed():
    try:
        with open(BFILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("load failed", e); return
    keys = [k for k in data.keys() if k not in ("current",)]
    if not keys:
        print("no keys"); return
    pick = random.choice(keys)
    data["current"] = data[pick]
    with open(BFILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    with open(LOG, "a", encoding="utf-8") as lf:
        lf.write(f"{time.asctime()}: rotated -> {pick}\n")
    print("rotated ->", pick)

if __name__ == "__main__":
    rotate_seed()
