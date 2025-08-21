DESCRIPTION = "Demonstrates agent hooks and logging."

import asyncio

async def run_plugin(input_data=None):
    print("[example_super_plugin] Running plugin...")
    if input_data:
        print(f"[example_super_plugin] Received input: {input_data}")
    # Simulate async work
    await asyncio.sleep(1)
    print("[example_super_plugin] Plugin completed.")
