"""
arena_core/__init__.py
Minimal lazy-load shim to prevent circular imports.
"""
__all__ = []

# Lazy import helper
import importlib
import sys

def lazy_import(name):
    try:
        return importlib.import_module(name)
    except Exception as e:
        print(f"Lazy import failed: {name} -> {e}")
        return None

# Example: you can later do
# arena_core.models = lazy_import('.models', 'arena_core')
