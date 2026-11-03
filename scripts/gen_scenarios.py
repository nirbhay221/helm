"""Precompute the agent's policy scenarios over the full creator population.

Runs the LIVE model (needs HELM_LLM_API_KEY in .env) to compile several written
treasury policies into weights + constraints, allocates the cycle budget across
the whole 2000-creator global population for each, and saves the results to
ui/scenarios_data.json. The dashboard then loads that file, so the page is
deterministic and needs no key or network, while still showing what the real
model compiled. Re-run this to refresh the scenarios.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:
    pass

from collections import defaultdict

from agent import LLMClient, PolicyDesk
from marketplace.allocator import allocate, make_global_creators

N_CREATORS, SEED = 5000, 3
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "scenarios_data.json")

POLICIES = [
    ("Normal week", "Cash is healthy. Pay creators fairly and prioritise the ones who have "
                     "waited longest to be paid."),
    ("Fraud wave", "A fraud and chargeback wave is hitting brand-new accounts this week. Hold "
                   "high-risk creators, and no single creator may get more than 10% of the batch."),
    ("Country freeze", "Freeze all payouts to Nigeria and China this week pending a compliance "
                       "review, and deliver as much net as possible to everyone else."),
    ("Tight cash", "Cash is tight this week. Be conservative, favour delivering more net to "
                   "creators, and cap any one creator at 15% of the batch."),
]


def _rollup(lines):
    by = defaultdict(lambda: {"amount": 0.0, "count": 0})
    for l in lines:
        by[l["country"]]["amount"] += l["amount"]
        by[l["country"]]["count"] += 1
    return {k: {"amount": round(v["amount"], 2), "count": v["count"]} for k, v in by.items()}


def main() -> None:
    desk = PolicyDesk(LLMClient())
    creators = make_global_creators(N_CREATORS, seed=SEED)
    budget = round(sum(c.owed for c in creators) * 0.30, 2)
    print(f"driver: {'MODEL ' + desk.llm.model if desk.available else 'FALLBACK (no key!)'}")

    pop_rollup = defaultdict(lambda: {"owed": 0.0, "count": 0})
    for c in creators:
        pop_rollup[c.country]["owed"] += c.owed
        pop_rollup[c.country]["count"] += 1
    population = {
        "n": len(creators),
        "total_owed": round(sum(c.owed for c in creators), 2),
        "budget": budget,
        "by_country": {k: {"owed": round(v["owed"], 2), "count": v["count"]}
                       for k, v in pop_rollup.items()},
    }

    scenarios = []
    for label, text in POLICIES:
        d = desk.compile(text)
        w, con = d.weights, d.constraints
        r = allocate(creators, budget, w, con)
        scenarios.append({
            "label": label, "policy": text, "source": d.source, "reading": d.reading,
            "weights": {"speed": w.speed, "tax": w.tax, "risk": w.risk, "fx": w.fx},
            "constraints": {"max_fraction_per_creator": con.max_fraction_per_creator,
                            "exclude_countries": list(con.exclude_countries),
                            "max_risk": con.max_risk, "min_priority": con.min_priority},
            "violations": d.violations,
            "paid_count": r.paid_count, "total_paid": r.total_paid,
            "net_delivered": r.net_delivered, "tax_withheld": r.tax_withheld,
            "fx_cost": r.fx_cost, "risk_exposure": round(r.risk_exposure, 1),
            "by_country": _rollup(r.lines),
            "top": r.lines[:8],
        })
        print(f"  {label}: paid {r.paid_count}, ${r.total_paid:,.0f}, "
              f"exclude={list(con.exclude_countries)} cap={con.max_fraction_per_creator}")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"population": population, "scenarios": scenarios}, f, indent=2)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
