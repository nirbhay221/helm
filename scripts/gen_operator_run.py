"""Capture one real run of the money-out operator as the dashboard's centerpiece.

Runs the LLM operator over a creator marketplace with a chargeback shock and an
approval threshold low enough that a large release is HELD for a human. Writes a
full per-cycle journal to ui/operator_run.json: the signal the agent read, the
risk posture it chose, the safe release the controller sized, who it paid and who
it HELD, whether the human-approval gate fired, the PayPal batch, and the cash,
owed and reserve trajectory. This is the closed loop, from the real engine.
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

from agent import LLMClient, MoneyOutOperator, OperatorCreator, OperatorTools, SignalDesk
from marketplace import CashPayoutController, CashPayoutParams, CreatorMarketplace, MarketplaceParams
from paypal import Ledger, PayPalClient

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "operator_run.json")

# a GMV path that rises into a spike then falls, so variance is real
GMV = [1000, 1100, 1500, 2600, 2100, 1300, 1000, 950]

CREATORS = [
    OperatorCreator("Manuela B.", "manuela-creator@personal.example.com", 3.0,
                    context="Brazil, two years on platform, steady sales, clean refund history"),
    OperatorCreator("Aarav R.", "aarav-creator@personal.example.com", 2.5,
                    context="India, 14 months, consistent, very few refunds"),
    OperatorCreator("Ben D.", "ben-creator@personal.example.com", 2.0,
                    context="United States, brand new this week, just went viral with a huge spike"),
    OperatorCreator("Zainab K.", "zainab-creator@personal.example.com", 1.5,
                    context="Nigeria, 8 months, mid-tier, occasional small refunds"),
    OperatorCreator("Noah D.", "noah-creator@personal.example.com", 1.5,
                    context="United States, flagged this week for a cluster of disputes and chargebacks"),
]

SIGNALS = {3: "Risk alert: a fraud and chargeback wave is hitting brand-new viral accounts in this category this week."}


def _gate_demo() -> dict:
    """The human-approval gate round-trip: the agent proposes a release over the
    threshold; the gate HOLDS it (the agent cannot approve itself); a human then
    releases the same batch and it settles. Deterministic, no model needed."""
    thr = 1500.0
    alloc = [{"creator": c.name, "amount": 450.0} for c in CREATORS]   # total 2250 > threshold

    def fresh():
        p = MarketplaceParams(baseline_gmv=1000.0, init_cash=5000.0,
                              chargeback_window=2, cash_floor=0.0)
        s = CreatorMarketplace(p, seed=7, n_periods=3)
        c = CashPayoutController(CashPayoutParams(horizon=6))
        t = OperatorTools(s, c, CREATORS, SignalDesk(LLMClient(env={})),
                          PayPalClient(), Ledger(), approval_threshold=thr)
        for cr in CREATORS:
            t.led.accrue(cr.name, 700.0, period=0)
        t.observe(); t.size_safe_release(1.0)
        return t

    held = fresh().call("pay_creators", {"allocations": alloc, "approved": True})   # agent cannot self-approve
    approved = fresh().pay_creators(alloc, approved=True)                            # human releases it
    return {
        "threshold": thr,
        "proposed_total": round(sum(a["amount"] for a in alloc), 2),
        "held": {"status": held["status"], "paid_total": held["paid_total"]},
        "approved": {"status": approved["status"], "paid_total": approved["paid_total"],
                     "batch_id": approved["batch_id"]},
    }


def main() -> None:
    params = MarketplaceParams(baseline_gmv=1000.0, demand_series=[float(x) for x in GMV],
                               init_cash=1800.0, chargeback_window=2)
    sim = CreatorMarketplace(params=params, seed=7, n_periods=len(GMV))
    controller = CashPayoutController(CashPayoutParams(horizon=6))
    client = PayPalClient()       # live sandbox if creds present, else demo
    # the main loop runs with a high gate so it shows the true paying behaviour;
    # the human-approval gate is demonstrated on its own below.
    tools = OperatorTools(sim, controller, CREATORS, SignalDesk(LLMClient()),
                          client, Ledger(), approval_threshold=1_000_000.0)
    op = MoneyOutOperator(tools, LLMClient(), signal_schedule=SIGNALS)

    cycles = []
    period = 0
    while not sim.done():
        snap = tools.observe()                         # state BEFORE this cycle
        rec = op.run(1)[-1]                             # run exactly one cycle
        f = rec.facts
        paid = {p["creator"]: p["amount"] for p in (f.get("paid") or [])}
        held = [{"creator": c["creator"], "context": c["context"], "owed": c["owed"]}
                for c in snap["creators"]
                if c["owed"] > 1e-6 and c["creator"] not in paid]
        cycles.append({
            "period": period,
            "driver": rec.driver,
            "signal": snap["signal"] if snap["signal"] != "(none)" else "",
            "assessment": f.get("signal_assessment", ""),
            "suggests_caution": bool(f.get("suggests_caution", False)),
            "risk_multiplier": f.get("risk_multiplier", 1.0),
            "safe_release": f.get("safe_release_total", 0.0),
            "forecast_gmv": f.get("forecast_gmv_next"),
            "forecast_sigma": f.get("forecast_sigma_next"),
            "paid": [{"creator": k, "amount": v} for k, v in paid.items()],
            "held": held,
            "status": f.get("status", ""),
            "needs_approval": f.get("status") == "needs_approval",
            "batch_id": f.get("batch_id"),
            "paid_total": f.get("paid_total", 0.0),
            "cash_after": f.get("cash_after"),
            "reserve_ok_after": f.get("reserve_ok_after"),
            "overrides": f.get("guardrail_overrides", []),
            "narration": (rec.narration or "").strip()[:280],
        })
        period += 1

    out = {
        "driver": "model" if LLMClient().available else "fallback",
        "paypal": "live sandbox" if not client.demo else "demo",
        "creators": [{"name": c.name, "context": c.context} for c in CREATORS],
        "gmv_path": GMV,
        "approval_threshold": 1500.0,
        "cycles": cycles,
        "gate_demo": _gate_demo(),
    }
    with open(OUT, "w", encoding="utf-8") as fp:
        json.dump(out, fp, indent=2, default=str)
    print(f"wrote {OUT}: {len(cycles)} cycles, driver={out['driver']}, paypal={out['paypal']}")
    for c in cycles:
        tag = "HELD-FOR-APPROVAL" if c["needs_approval"] else c["status"]
        sig = "  <-- SIGNAL" if c["signal"] else ""
        print(f"  cycle {c['period']}: posture {c['risk_multiplier']}x, safe ${c['safe_release']}, "
              f"paid {len(c['paid'])} / held {len(c['held'])}, {tag}{sig}")


if __name__ == "__main__":
    main()
