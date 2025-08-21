import os, time, json

LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent_data", "log.json"))

def log_event(event_type, message):
    log_entry = {
        "time": int(time.time()),
        "type": event_type,
        "message": message
    }
    logs = []
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH) as f: logs = json.load(f)
    logs.append(log_entry)
    with open(LOG_PATH, "w") as f: json.dump(logs, f, indent=2)
