from demoparser2 import DemoParser

print("Loading demo...")

parser = DemoParser("demos/MATCH20260725-1.dem")

df = parser.parse_ticks([
    "X",
    "Y",
    "Z",
    "yaw",
    "pitch",
    "is_alive",
    "team_name"
])

print("\n=== ORIGINAL ===")

memory_bytes = df.memory_usage(index=True, deep=True).sum()

print(f"Rows: {len(df):,}")
print(f"Memory: {memory_bytes / 1024**2:.2f} MiB")
print(df.memory_usage(index=True, deep=True).sort_values(ascending=False))
print("\nDtypes:")
print(df.dtypes)

print("\n=== TICK STATS ===")

print(f"Unique ticks: {df['tick'].nunique():,}")
print(f"Unique players: {df['steamid'].nunique():,}")
print(f"Tick range: {df['tick'].min()} -> {df['tick'].max()}")
print(f"Average rows/tick: {len(df) / df['tick'].nunique():.2f}")

print("\n=== OPTIMIZED ===")

optimized = df.copy()

optimized["team_name"] = optimized["team_name"].astype("category")
optimized["name"] = optimized["name"].astype("category")
optimized["steamid"] = optimized["steamid"].astype("uint64")
optimized["tick"] = optimized["tick"].astype("uint32")

for col in ["X", "Y", "Z", "pitch", "yaw"]:
    optimized[col] = optimized[col].astype("float32")

optimized_bytes = optimized.memory_usage(index=True, deep=True).sum()

print(f"Original:  {memory_bytes / 1024**2:.2f} MiB")
print(f"Optimized: {optimized_bytes / 1024**2:.2f} MiB")
print(f"Reduction: {(1 - optimized_bytes / memory_bytes) * 100:.1f}%")

print("\nOptimized dtypes:")
print(optimized.dtypes)