"""Run the creator-marketplace controller and pay real creators on PayPal.

Each period the controller decides how much to pay, and that money goes out as a
real PayPal Payouts batch to the creators' sandbox emails. With sandbox
credentials in .env (DEMO_MODE=0) these are live sandbox transactions with real
batch ids; otherwise they are labeled demo stubs.
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

from marketplace import (CashPayoutController, CashPayoutParams, Creator,
                         CreatorMarketplace, MarketplaceParams, run_marketplace_live)
from paypal import Ledger, PayPalClient

GMV = [1000]*3 + [1800, 2600, 3000, 1800] + [350, 400, 900, 900]

CREATORS = [
    Creator("Ava", "ava-creator@personal.example.com", weight=3.0),
    Creator("Ben", "ben-creator@personal.example.com", weight=2.0),
    Creator("Cy", "cy-creator@personal.example.com", weight=1.0),
]


def main() -> None:
    params = MarketplaceParams(
        baseline_gmv=1000.0, take_rate=0.12, refund_rate=0.05, chargeback_rate=0.12,
        chargeback_lag=2, chargeback_window=4, reserve_rate=0.30, cash_floor=300.0,
        init_cash=900.0, demand_series=[float(x) for x in GMV])
    sim = CreatorMarketplace(params, seed=7, n_periods=len(GMV))
    controller = CashPayoutController(CashPayoutParams(
        horizon=8, take_rate=0.12, refund_rate=0.05, chargeback_rate=0.12))
    client, ledger = PayPalClient(env=os.environ), Ledger()

    print(f"paypal: {'DEMO' if client.demo else 'LIVE sandbox'}")
    print(f"creators: {', '.join(c.name for c in CREATORS)}\n")

    runs = run_marketplace_live(sim, controller, CREATORS, client, ledger,
                                purpose="COMMISSION", poll_status=True)
    for r in runs:
        who = ", ".join(f"{x['creator']} ${x['amount']:.0f}" for x in r.recipients)
        print(f"wk{r.period:>2} paid ${r.payout_total:>7,.2f} -> [{who}]  "
              f"batch={r.batch_id} status={r.status} "
              f"cash=${r.cash_after:,.0f} reserve_ok={r.reserve_ok}")

    total = sum(r.payout_total for r in runs)
    print(f"\n{len(runs)} payout batches sent, ${total:,.2f} to creators total.")


if __name__ == "__main__":
    main()
