# plugin_loader.py — simple plugin loader
import os, importlib.util
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PLUGINS_DIR = os.path.join(BASE, "plugins")

class PluginManager:
    def __init__(self):
        self.plugins = []
        self.load_plugins()

    def load_plugins(self):
        self.plugins = []
        if not os.path.isdir(PLUGINS_DIR):
            os.makedirs(PLUGINS_DIR, exist_ok=True)
        for fn in sorted(os.listdir(PLUGINS_DIR)):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(PLUGINS_DIR, fn)
            try:
                spec = importlib.util.spec_from_file_location(fn[:-3], path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                # accept plugin_instance, or class named Plugin, or module with run()
                instance = getattr(mod, "plugin_instance", None)
                if instance is None:
                    PluginClass = getattr(mod, "Plugin", None)
                    if PluginClass:
                        instance = PluginClass()
                    elif hasattr(mod, "run"):
                        # create a thin wrapper
                        class _Wrap:
                            name = fn[:-3]
                            description = getattr(mod, "DESCRIPTION", "")
                            def run(self, data=None):
                                return mod.run(data)
                        instance = _Wrap()
                if instance:
                    # ensure name and run exist
                    if not hasattr(instance, "name"):
                        instance.name = getattr(instance, "name", fn[:-3])
                    self.plugins.append(instance)
                    print(f"[PluginLoader] Loaded {fn}")
            except Exception as e:
                print(f"[PluginLoader] Failed to load {fn}: {e}")

plugin_mgr = PluginManager()
