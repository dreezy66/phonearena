#!/usr/bin/env python3
import os
def run(base_dir="."):
    buckets = ["projects","user_projects"]
    out = []
    for b in buckets:
        p = os.path.join(base_dir, b)
        if not os.path.isdir(p): continue
        for name in sorted(os.listdir(p)):
            full = os.path.join(p, name)
            if os.path.isdir(full):
                out.append(full)
    return out
