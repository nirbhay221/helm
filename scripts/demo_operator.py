"""Helm's money-out operator running the payout loop, steered by the model.

The agent decides, each cycle, how conservative to be and which creators to pay
versus hold based on their risk, then pays on PayPal. The deterministic tools
size the safe release and hard-clamp the agent. Watch it hold the risky creator
when a fraud signal lands, and release to the safe ones.
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

from agent import LLMClient, MoneyOutOperator, OperatorCreator, OperatorTools, SignalDesk
from marketplace import CashPayoutController, CashPayoutParams, CreatorMarketplace, MarketplaceParams
from paypal import Ledger, PayPalClient

GMV = [1000, 1000, 1400, 2600, 2000, 1200, 900, 900]

CREATORS = [
    OperatorCreator("Ava", "ava-creator@personal.example.com", 3.0,
                    context="long-tenured (2 years), steady sales, clean refund history"),
    OperatorCreator("Ben", "ben-creator@personal.example.com", 2.0,
                    context="brand new this week, just went viral with a huge spike"),
    OperatorCreator("Cy", "cy-creator@personal.example.com", 1.0,
                    context="mid-tier, a year on platform, occasional small refunds"),
]

SIGNALS = {3: "Risk alert: a fraud and chargeback wave is hitting brand-new viral accounts in this category this week."}


def main() -> None:
    params = MarketplaceParams(
        baseline_gmv=1000.0, take_rate=0.12, refund_rate=0.05, chargeback_rate=0.12,
        chargeback_lag=2, chargeback_window=4, reserve_rate=0.30, cash_floor=300.0,
        init_cash=900.0, demand_series=[float(x) for x in GMV])
    sim = CreatorMarketplace(params, seed=7, n_periods=len(GMV))
    controller = CashPayoutController(CashPayoutParams(
        horizon=8, take_rate=0.12, refund_rate=0.05, chargeback_rate=0.12))
    client, ledger = PayPalClient(env=os.environ), Ledger()
    llm = LLMClient()
    desk = SignalDesk(llm)
    tools = OperatorTools(sim, controller, CREATORS, desk, client, ledger)
    operator = MoneyOutOperator(tools, llm, signal_schedule=SIGNALS)

    print(f"driver: {'MODEL ' + llm.model if llm.available else 'scripted fallback'}")
    print(f"paypal: {'DEMO' if client.demo else 'LIVE sandbox'}\n")

    records = operator.run(len(GMV))
    for r in records:
        sig = SIGNALS.get(r.period, "")
        print(f"--- cycle {r.period}  ({r.driver})" + (f'  SIGNAL: {sig}' if sig else ''))
        f = r.facts
        if "safe_release_total" in f:
            print(f"    risk_multiplier={f.get('risk_multiplier')}  safe_release=${f.get('safe_release_total')}")
        paid = ", ".join(f"{p['creator']} ${p['amount']:.0f}" for p in (f.get('paid') or [])) or "nobody"
        print(f"    paid: [{paid}]  status={f.get('status')}  batch={f.get('batch_id')}  "
              f"cash_after=${f.get('cash_after')}  reserve_ok={f.get('reserve_ok_after')}")
        if f.get("guardrail_overrides"):
            for o in f["guardrail_overrides"]:
                print(f"    guardrail: {o}")

    print("\nThe model chose the risk posture and who to pay; the tools sized the "
          "safe release and clamped every payout. That is the AI steering, bounded.")


if __name__ == "__main__":
    main()
