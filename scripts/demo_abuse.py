"""The both-sides abuse engine on a marketplace: who is at fault, and the action.

Generates a 120-account two-sided marketplace with real order/return patterns,
then has the engine flag abusers on BOTH sides and attribute fault by how widely
each one's returns spread. Serial-returner buyers and bad sellers are caught
separately, with a plain-language reason and a suspension.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market.abuse import AbuseEngine
from market.marketplace import generate_marketplace


def main() -> None:
    m = generate_marketplace(n_accounts=120, seed=7)
    total_orders = len(m.orders)
    bad = sum(1 for o in m.orders if o.status in ("returned", "charged_back"))
    print(f"marketplace: {len(m.accounts)} accounts, {len(m.listings)} listings, "
          f"{total_orders} orders, {bad} returns/chargebacks\n")

    engine = AbuseEngine(min_bad=10)
    verdicts = engine.scan(m)
    print(f"abuse engine flagged {len(verdicts)} accounts (both sides):\n")
    for v in verdicts:
        print(f"  [{v.action.upper():7}] {v.name:<12} as {v.role:<6} "
              f"{v.bad_count} bad / {v.distinct_counterparties} counterparties, rate {int(v.rate*100)}%")
        print(f"            {v.reason}")

    n = engine.apply(m, verdicts)
    print(f"\n{n} accounts suspended; their innocent counterparties keep their money and standing.")


if __name__ == "__main__":
    main()
