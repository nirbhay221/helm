"""The agent sets payout weights; the solver allocates across many global creators.

Two situations, same creators and budget: a normal week and a week with a fraud
wave. The model reads each and sets the objective weights; the solver allocates.
The fraud week should raise the risk weight and pull money away from risky
creators, at some cost to speed. This is the multi-objective, global, at-scale
version: many countries, withholding and FX in the objective, the model steering
the trade-off and the solver doing the math.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:
    pass

from agent import LLMClient, WeightDesk
from marketplace.allocator import allocate, make_global_creators

SITUATIONS = [
    ("NORMAL", "Normal operating week. Cash is healthy. No unusual activity."),
    ("FRAUD WAVE", "A fraud and chargeback wave is hitting high-risk creator accounts "
                   "this week; several disputes are already landing."),
]


def main() -> None:
    desk = WeightDesk(LLMClient())
    creators = make_global_creators(60, seed=3)
    budget = 12000.0
    countries = sorted({c.country for c in creators})
    print(f"driver: {'MODEL ' + desk.llm.model if desk.available else 'scripted fallback'}")
    print(f"creators: {len(creators)} across {len(countries)} countries {countries}, budget ${budget:,.0f}\n")

    for label, text in SITUATIONS:
        d = desk.decide(text)
        w = d.weights
        r = allocate(creators, budget, w)
        print(f"[{label}] {text}")
        print(f"  weights: speed={w.speed} tax={w.tax} risk={w.risk} fx={w.fx}  ({d.source}: {d.rationale[:70]})")
        print(f"  paid {r.paid_count}/{len(creators)} creators, ${r.total_paid:,.0f}; "
              f"net to creators ${r.net_delivered:,.0f}; tax withheld ${r.tax_withheld:,.0f}; "
              f"FX cost ${r.fx_cost:,.0f}; risk exposure {r.risk_exposure:,.1f}")
        top = ", ".join(f"{l['name']} ${l['amount']:.0f}" for l in r.lines[:4])
        print(f"  top: {top}\n")

    print("Same creators and budget; the model moved the weights and the solver "
          "re-allocated. The fraud week carries lower risk exposure because the "
          "agent raised the risk weight and the solver held the risky creators.")


if __name__ == "__main__":
    main()
