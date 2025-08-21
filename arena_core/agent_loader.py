import os, importlib.util
from arena_core import agent_runtime

PLUGIN_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "plugins")
plugins = []

class Plugin:
    def __init__(self, name, path):
        self.name = name
        self.path = path
    def run(self, kwargs=None):
        spec = importlib.util.spec_from_file_location(self.name, self.path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "run"):
            return mod.run(kwargs)
        return None

def load_plugins():
    global plugins
    plugins = []
    if not os.path.isdir(PLUGIN_DIR):
        os.makedirs(PLUGIN_DIR)
    for f in os.listdir(PLUGIN_DIR):
        if f.endswith(".py"):
            path = os.path.join(PLUGIN_DIR,f)
            try:
                plugins.append(Plugin(f[:-3], path))
                print(f"[PluginLoader] Loaded {f}")
            except Exception as e:
                print(f"[PluginLoader] Failed to load {f}: {e}")

def manage_plugins():
    load_plugins()
    print("=== Plugins Loaded ===")
    for p in plugins:
        print(p.name)