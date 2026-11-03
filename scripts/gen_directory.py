"""Build the creator directory: the whole population at scale, plus a browsable
sample of named individuals, so the dashboard can show both the crowd and a
person. Run after gen_reinvest.py (it reads the pool's return). Synthetic data.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.allocator import Weights, allocate, make_global_creators

N, SEED, SAMPLE = 5000, 3, 400
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "ui", "directory_data.json")
REINVEST = os.path.join(HERE, "ui", "reinvest_data.json")


def main() -> None:
    creators = make_global_creators(N, seed=SEED)
    budget = round(sum(c.owed for c in creators) * 0.30, 2)
    r = allocate(creators, budget, Weights(1, 1, 1, 1))     # the "normal" policy
    paid = {l["name"]: l["amount"] for l in r.lines}

    try:
        with open(REINVEST, encoding="utf-8") as f:
            ret = json.load(f)["nav_return_pct"] / 100.0
    except Exception:
        ret = 0.0

    by_country = defaultdict(lambda: {"count": 0, "owed": 0.0, "paid": 0.0})
    for i, c in enumerate(creators):
        bc = by_country[c.country]
        bc["count"] += 1
        bc["owed"] += c.owed
        bc["paid"] += paid.get(c.name, 0.0)

    def record(i, c):
        reinvesting = (i % 4 == 0)
        return {"display": c.display, "country": c.country, "owed": c.owed,
                "risk": c.risk, "paid": round(paid.get(c.name, 0.0), 2),
                "reinvesting": reinvesting,
                "stake": round(c.owed * (1 + ret), 2) if reinvesting else 0.0}

    # a sample that spans the whole list (every stride-th creator)
    stride = max(1, N // SAMPLE)
    sample = [record(i, creators[i]) for i in range(0, N, stride)][:SAMPLE]

    data = {
        "total": N,
        "sample_size": len(sample),
        "paid_count": r.paid_count,
        "total_owed": round(sum(c.owed for c in creators), 2),
        "total_paid": r.total_paid,
        "reinvesting_count": sum(1 for i in range(N) if i % 4 == 0),
        "by_country": {k: {"count": v["count"], "owed": round(v["owed"], 2),
                           "paid": round(v["paid"], 2)} for k, v in by_country.items()},
        "sample": sample,
        "note": "Synthetic creator population (realistic shape); not real users.",
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"{N} creators, paid {r.paid_count} this cycle, sample {len(sample)} named individuals")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
