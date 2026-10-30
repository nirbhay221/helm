"""The demo business: a small online pet-accessories brand that sells through creator affiliates.

Three suppliers give the Quartermaster a real choice: a fast domestic maker with a small
minimum, a cheap overseas factory with a big minimum and deep tiers, and a mid-priced
wholesaler. The owner's plan is flat-ish demand; the shock is a creator video going viral.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from helm.model import BusinessPlan, Limits, State, Supplier, Tier
from helm.sim.twin import DemandModel, Shock, Twin

PRICE = 24.0

SUPPLIERS = [
    Supplier("fastfab", "FastFab (domestic)", (Tier(50, 9.80), Tier(200, 9.10)), lead_weeks=1, capacity=600, fixed_fee=25.0),
    Supplier("harborwhole", "Harbor Wholesale", (Tier(150, 8.20), Tier(400, 7.60), Tier(800, 7.10)), lead_weeks=2, capacity=1200, fixed_fee=60.0),
    Supplier("pacificworks", "Pacific Works (overseas)", (Tier(500, 6.40), Tier(1500, 5.70), Tier(3000, 5.20)), lead_weeks=4, capacity=5000, fixed_fee=180.0),
]

LEAD_TIMES = {s.id: s.lead_weeks for s in SUPPLIERS}


@dataclass
class Scenario:
    twin: Twin
    state: State
    business: BusinessPlan
    limits: Limits
    suppliers: list[Supplier]


def build(weeks: int = 40, seed: int = 7, viral_week: int | None = 14, viral_multiplier: float = 3.0) -> Scenario:
    shocks = [Shock(viral_week, 3, viral_multiplier, "creator video goes viral")] if viral_week is not None else []
    demand = DemandModel(base=120.0, shocks=shocks)
    twin = Twin(demand, PRICE, LEAD_TIMES, seed=seed)

    # Twelve weeks of history before Helm takes the helm, sampled from the same demand model.
    rng = np.random.default_rng(seed + 1)
    history = [demand.sample(w, demand.baseline_commission, rng) for w in range(-12, 0)]
    revenue = [h * PRICE for h in history]

    # The owner's plan: three weeks of cover, and cash growing with expected margin.
    # The plan is made before anyone knows about the viral video, so it uses demand without shocks.
    horizon = weeks + 20
    calm = DemandModel(base=demand.base)
    expected = [calm.expected(w, demand.baseline_commission) for w in range(horizon)]
    inv_target = tuple(3.0 * e for e in expected)
    cash0 = 6000.0
    weekly_margin = 120.0 * (PRICE - 7.6 - PRICE * demand.affiliate_share * demand.baseline_commission)
    cash_target = tuple(cash0 + weekly_margin * w for w in range(horizon))

    state = State(
        week=0, on_hand=inv_target[0], cash=cash0, commission_rate=demand.baseline_commission,
        demand_history=history, revenue_history=revenue,
    )
    business = BusinessPlan(inv_target, cash_target, cash_floor=1500.0, price=PRICE)
    limits = Limits(
        max_spend_per_week=9000.0, commission_min=0.05, commission_max=0.25,
        allowed_suppliers=frozenset(s.id for s in SUPPLIERS),
    )
    return Scenario(twin, state, business, limits, list(SUPPLIERS))
