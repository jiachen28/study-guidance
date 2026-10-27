"""Summarise independently completed human review files; never infer reviewer identity."""
import csv
from pathlib import Path
FIELDS = ("explanation_supported", "verification_actionable", "limitations_appropriate")
for name in ("Xin", "Siyuan"):
    path = Path("results") / f"human_review_{name}.csv"
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 20 or len({r["id"] for r in rows}) != 20:
        raise ValueError(f"{path}: expected 20 unique scenario IDs")
    print(name)
    for key in FIELDS:
        values = [r[key].strip() for r in rows]
        if any(v not in ("0", "1") for v in values):
            raise ValueError(f"{path}: incomplete or invalid {key}")
        print(f"  {key}: {sum(map(int, values))}/20")
