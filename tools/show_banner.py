#!/usr/bin/env python3
import os, sys
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE)
try:
    from branding.banners import print_banner
    mode = (sys.argv[1] if len(sys.argv)>1 else "adaad")
    print_banner(BASE, mode)
except Exception as e:
    print("Banner error:", e)
