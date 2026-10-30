import json

d = json.load(open("data/demo_plan.json"))
problems = []

def slots():
    for day in d["days"]:
        for s in day["slots"]:
            yield day["day"], s

# 1. Required keys
for k in ["destination", "stay", "days", "extras", "fairness"]:
    if k not in d: problems.append(f"Missing key: {k}")

# 2. Stay should not also appear as a stop
stay = d["stay"]["name"]
for day, s in slots():
    if s["name"] == stay:
        problems.append(f"Stay '{stay}' is also scheduled as a stop (day {day})")

# 3. No venue repeated
names = [s["name"] for _, s in slots()]
for n in set(names):
    if names.count(n) > 1: problems.append(f"Repeated venue: {n} x{names.count(n)}")

# 4. Every friend has a spotlight
people = list(d["fairness"].keys())
spot = {p: 0 for p in people}
for _, s in slots():
    if s.get("spotlight") in spot: spot[s["spotlight"]] += 1
for p, c in spot.items():
    if c == 0: problems.append(f"No spotlight for {p}")

# 5. Scores in range and not flat
allscores = {p: [] for p in people}
for _, s in slots():
    for p, v in s.get("per_person", {}).items():
        if not 0 <= v <= 1: problems.append(f"Score out of range: {s['name']} {p}={v}")
        if p in allscores: allscores[p].append(v)
for p, v in allscores.items():
    if v and max(v) - min(v) < 0.1:
        problems.append(f"{p}'s scores are nearly flat ({min(v):.2f}-{max(v):.2f})")

# 6. Fairness formula
for p, v in allscores.items():
    pass
print("Stay:", stay)
print("Stops:", len(names), "| Spotlights:", spot)
print("Fairness:", d["fairness"])
print("\nPROBLEMS:" if problems else "\nNo automatic problems found.")
for x in problems: print(" -", x)