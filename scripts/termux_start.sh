#!/bin/sh
# Termux-friendly startup. Put in Termux:Boot or run manually.
cd "$ARENA_DIR"
nohup python3 phonearena_dashboard.py > logs/dashboard.out 2>&1 &
