import json, os

PROFIT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent_data", "profits.json"))

def record_profit(agent_name, amount):
    data = {}
    if os.path.exists(PROFIT_FILE):
        with open(PROFIT_FILE) as f: data = json.load(f)
    data[agent_name] = data.get(agent_name, 0) + amount
    with open(PROFIT_FILE, "w") as f: json.dump(data, f, indent=2)
    print(f"[ProfitTracker] {agent_name} +${amount}")
