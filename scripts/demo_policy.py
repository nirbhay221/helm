"""Type a treasury policy in English; the agent compiles it; the solver obeys.

Three written policies, same creators and budget. The model compiles each into
weights and hard constraints (validated), and the allocator enforces them. You
see the allocation change with the policy: a diversification cap, a risk hold, a
country freeze. This is the deep use of the model, reading a policy and turning
it into an enforceable, auditable payout plan, not picking numbers.
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

from agent import LLMClient, PolicyDesk
from marketplace.allocator import allocate, make_global_creators

POLICIES = [
    "Cash is healthy. Pay our creators fast this week, prioritise the ones waiting longest.",
    "A fraud wave is hitting new accounts. Hold anyone high-risk, and no single creator may get "
    "more than 15% of the batch.",
    "Freeze all payouts to Nigeria and China this week pending review, and deliver as much net "
    "to creators as possible.",
]


def main() -> None:
    desk = PolicyDesk(LLMClient())
    creators = make_global_creators(60, seed=3)
    budget = 12000.0
    print(f"driver: {'MODEL ' + desk.llm.model if desk.available else 'scripted fallback'}")
    print(f"{len(creators)} creators across 10 countries, budget ${budget:,.0f}\n")

    for pol in POLICIES:
        d = desk.compile(pol)
        w, c = d.weights, d.constraints
        r = allocate(creators, budget, w, c)
        countries_paid = sorted({l["country"] for l in r.lines})
        top_share = max((l["amount"] for l in r.lines), default=0) / budget
        print(f"POLICY: {pol}")
        print(f"  compiled ({d.source}): weights speed={w.speed} tax={w.tax} risk={w.risk} fx={w.fx} | "
              f"cap={c.max_fraction_per_creator} exclude={list(c.exclude_countries)} max_risk={c.max_risk} min_priority={c.min_priority}")
        if d.reading:
            print(f"  reading: {d.reading[:90]}")
        print(f"  -> paid {r.paid_count}/{len(creators)}, ${r.total_paid:,.0f}; net ${r.net_delivered:,.0f}; "
              f"risk exposure {r.risk_exposure:,.1f}; biggest share {top_share*100:.0f}%; countries {countries_paid}")
        if d.violations:
            print(f"  validator: {d.violations}")
        print()


if __name__ == "__main__":
    main()
