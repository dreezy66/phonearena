#!/usr/bin/env python3
import os, importlib.util, sys
def list_plugins(base_dir):
    plugin_paths = [os.path.join(base_dir,"plugins"), os.path.join(base_dir,"arena_core","plugins")]
    found=[]
    for p in plugin_paths:
        if os.path.isdir(p):
            for f in sorted(os.listdir(p)):
                if f.endswith(".py"):
                    found.append(os.path.join(p,f))
    return found

def reload_plugin(path):
    try:
        modname = os.path.splitext(os.path.basename(path))[0]
        spec = importlib.util.spec_from_file_location(modname, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for key in list(sys.modules.keys()):
            if key.endswith(modname):
                sys.modules[key] = mod
        return True, "Reloaded"
    except Exception as e:
        return False, str(e)
