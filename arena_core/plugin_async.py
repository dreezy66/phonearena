import asyncio
from .plugin_loader import plugin_mgr

async def run_plugin_safe(name, input_data=None):
    try:
        result = await plugin_mgr.run_plugin(name, input_data)
        print(f"[PluginAsync] Plugin {name} completed with result: {result}")
    except Exception as e:
        print(f"[PluginAsync] Plugin {name} failed: {e}")
