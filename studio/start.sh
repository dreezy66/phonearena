#!/bin/bash
# PhoneArena startup script
echo "[Startup] Checking environment..."
mkdir -p ../agent_data ../marketplace_data ../plugins
echo "[Startup] Launching main.py..."
python3 main.py
