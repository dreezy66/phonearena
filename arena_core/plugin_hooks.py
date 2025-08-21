from .plugin_loader import plugin_mgr

def trigger_plugins_on_event(event, input_data=None):
    for p in plugin_mgr.get_plugins():
        if event in getattr(p, 'triggers', []):
            try:
                p.run(input_data)
                print(f"[PluginHook] {p.name} triggered by {event}")
            except:
                print(f"[PluginHook] {p.name} failed on {event}")
