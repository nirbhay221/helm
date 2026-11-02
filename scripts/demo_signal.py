"""Does the language model earn its place? A non-circular test.

A promotion is announced two weeks before it lands. The announcement is free
text; only a language model can read it. The signal desk turns it into a bounded
forecast adjustment, the verifier admits it, and the controller pre-positions
stock for the surge. We run three policies on the SAME real demand path:

  base-stock          - the standard competitive baseline, no signal
  Helm (no signal)    - the MPC controller on a flat forecast
  Helm + signal       - the same controller, forecast informed by the signal

and we score them on what a business actually cares about (stockouts, fill rate,
lost sales), NOT on deviation (the controller's own objective). If the
signal-aware run avoids a stockout the other two suffer, the LLM has earned its
place in a way deviation-gaming never could.
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

from agent import LLMClient, SignalDesk  # noqa: E402
from agent.verifier import ActionVerifier  # noqa: E402
from arms.awardsmith import DiscountTier, SupplierQuote  # noqa: E402
from evaluation import base_stock_policy, helm_policy, helm_signal_policy, run_policy  # noqa: E402
from helm_core import ControllerParams, RecedingHorizonController  # noqa: E402
from simulator import BusinessParams, BusinessSim  # noqa: E402
from simulator.real_demand import P263_WEEKLY, PLANNED_DEMAND  # noqa: E402

PROMO_WEEK = 24
SIGNAL_SEEN_AT = 22
SIGNAL_TEXT = (
    "Heads up from marketing: we have booked a major promotion for week 24. "
    "The last few times we ran a promo on this product, weekly demand came in at "
    "roughly triple the normal level during the promo week."
)


def suppliers() -> list[SupplierQuote]:
    return [
        SupplierQuote("Alpha", [DiscountTier(0, 9.0)], capacity=400),
        SupplierQuote("Beta", [DiscountTier(0, 8.5), DiscountTier(40, 8.0)], capacity=400),
        SupplierQuote("Gamma", [DiscountTier(50, 7.5)], capacity=300),
    ]


def params() -> BusinessParams:
    # lead time 2: you must order before you can see the demand, so anticipation
    # (what the signal buys you) actually matters.
    return BusinessParams(
        price=20.0, unit_cost=8.0, lead_time=2,
        init_inventory=40.0, init_cash=4000.0, target_inventory=40.0,
        cash_floor=0.0, baseline_demand=PLANNED_DEMAND,
        demand_series=list(P263_WEEKLY),
    )


def fresh_sim() -> BusinessSim:
    return BusinessSim(params(), seed=7, n_periods=len(P263_WEEKLY))


def main() -> None:
    p = params()
    cparams = ControllerParams(horizon=8, unit_cost=p.unit_cost, price=p.price,
                               cash_floor=p.cash_floor, lead_time=p.lead_time)
    controller = RecedingHorizonController(cparams)

    # 1. the signal desk reads the free text
    desk = SignalDesk(LLMClient())
    print(f"driver: {'MODEL ' + desk.llm.model if desk.available else 'scripted fallback (no key)'}")
    print(f"signal (seen at week {SIGNAL_SEEN_AT}): {SIGNAL_TEXT}\n")
    proposed = desk.interpret(SIGNAL_TEXT, current_period=SIGNAL_SEEN_AT,
                              baseline_demand=PLANNED_DEMAND, horizon=8)
    print(f"model proposed deltas: { {k: round(v,1) for k,v in proposed.period_deltas.items()} }")
    print(f"  cited: \"{proposed.cited_signal[:80]}\"  (source: {proposed.source})")

    # 2. the verifier bounds it before the controller may use it
    verifier = ActionVerifier(fresh_sim(), controller, suppliers())
    verdict, adj = verifier.verify_forecast_adjustment(
        proposed, current_period=SIGNAL_SEEN_AT, baseline_demand=PLANNED_DEMAND, horizon=8)
    print(f"verifier: ok={verdict.ok} admitted deltas={ {k: round(v,1) for k,v in adj.period_deltas.items()} }")
    if verdict.violations:
        for vio in verdict.violations:
            print(f"  - {vio}")
    print()

    # 3. three policies on the same real demand path
    m_base = run_policy(fresh_sim(), base_stock_policy())
    m_helm = run_policy(fresh_sim(), helm_policy(controller))
    m_sig = run_policy(fresh_sim(), helm_signal_policy(controller, adj))

    def row(name, m):
        print(f"  {name:<22} stockouts={m.stockout_periods:>2}  fill={m.fill_rate:.3f}  "
              f"lost_sales_units={round((1-m.fill_rate)*sum(P263_WEEKLY)):>3}  "
              f"avg_inv={m.avg_inventory:>5.1f}  order_cost=${m.order_cost:,.0f}")

    print("results on the real P263 demand path (metrics that matter, not deviation):")
    row("base-stock", m_base)
    row("Helm (no signal)", m_helm)
    row("Helm + signal", m_sig)

    print(f"\nat the promo week {PROMO_WEEK}, demand = {P263_WEEKLY[PROMO_WEEK]} vs plan {PLANNED_DEMAND:.0f}")
    print(f"stockouts avoided by the signal: base-stock {m_base.stockout_periods} / "
          f"no-signal {m_helm.stockout_periods} -> with-signal {m_sig.stockout_periods}")


if __name__ == "__main__":
    main()
