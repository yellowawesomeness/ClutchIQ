from demoparser2 import DemoParser

path = r"C:\Projects\ClutchIQ\demos\MATCH20260725-1.dem"
parser = DemoParser(path)

for event_name in ["round_start", "round_freeze_end", "round_end"]:
    print(f"`n=== {event_name} ===")
    result = parser.parse_event(event_name)

    print("type:", type(result))
    print("columns:", list(result.columns))
    print(result.head(10).to_string(index=False))
