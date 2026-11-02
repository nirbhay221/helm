"""Honest evaluation: does Helm's controller actually beat a strong baseline?

The earlier demos proved only that the code runs on one hand-picked scenario
against a weak strawman. That proves nothing. This harness does the opposite: it
runs the controller against a properly tuned order-up-to (base-stock) policy,
which is the standard and genuinely competitive method for this problem, across
many RANDOMIZED scenarios (varied demand level, noise, lead time, and shock
timing and size), on identical demand paths, and reports where Helm wins AND
where it loses.

Fairness: demand in the simulator is a seeded draw that does not depend on the
ordering decisions, so two policies run on sims built with the same seed and
same shocks face the exact same realized demand. Both policies are costed at the
flat unit cost here, so any difference is control quality (timing and sizing),
not sourcing; the sourcing saving is a separate, already-demonstrated effect.

The base-stock level is set analytically from the known parameters
(S = target + lead_time * baseline demand), not tuned on the realized path, so
the baseline never sees the future. Metrics per run:

  cum_abs_deviation  - total |inventory - target| over the horizon (primary)
  fill_rate          - units sold / units demanded (service level)
  stockout_periods   - periods with unmet demand
  min_cash           - lowest cash balance seen
  order_cost         - total spent on orders (flat unit cost)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, pstdev
from typing import Callable

from helm_core import ControllerParams, RecedingHorizonController
from simulator import BusinessParams, BusinessSim

Policy = Callable[[BusinessSim], float]


@dataclass
class Scenario:
    seed: int
    params: BusinessParams
    shocks: dict[int, float] = field(default_factory=dict)
    n_periods: int = 24
    label: str = ""

    def fresh_sim(self) -> BusinessSim:
        sim = BusinessSim(self.params, seed=self.seed, n_periods=self.n_periods)
        for period, delta in self.shocks.items():
            sim.inject_shock(period, delta)
        return sim


@dataclass
class RunMetrics:
    cum_abs_deviation: float    # Helm's own objective (so a win here is partly circular)
    fill_rate: float            # service: NOT Helm's objective
    stockout_periods: int
    avg_inventory: float        # capital tied up in stock: NOT Helm's objective
    min_cash: float
    cash_floor_breaches: int    # periods cash fell below the floor: NOT Helm's objective
    order_cost: float

    @staticmethod
    def from_history(sim: BusinessSim) -> "RunMetrics":
        hist = sim.history
        total_demand = sum(o.demand for o in hist)
        total_sales = sum(o.sales for o in hist)
        dev = sum(abs(o.inventory - o.target_inventory) for o in hist)
        stockouts = sum(1 for o in hist if o.demand - o.sales > 1e-6)
        order_cost = sum(o.order_placed for o in hist) * sim.p.unit_cost
        floor = sim.p.cash_floor
        breaches = sum(1 for o in hist if o.cash < floor - 1e-6)
        return RunMetrics(
            cum_abs_deviation=round(dev, 2),
            fill_rate=round(total_sales / total_demand, 4) if total_demand > 0 else 1.0,
            stockout_periods=stockouts,
            avg_inventory=round(mean(o.inventory for o in hist) if hist else sim.inventory, 2),
            min_cash=round(min((o.cash for o in hist), default=sim.cash), 2),
            cash_floor_breaches=breaches,
            order_cost=round(order_cost, 2),
        )


# --- policies ---------------------------------------------------------------
def _pipeline_total(sim: BusinessSim) -> float:
    return sum(sim._pipeline.values())


def base_stock_policy(controller_cap: float = 200.0) -> Policy:
    """Order-up-to S, with S set from known parameters (target plus expected
    lead-time demand). Inventory position = on hand + on order."""
    def decide(sim: BusinessSim) -> float:
        S = sim.p.target_inventory + sim.p.lead_time * sim.p.baseline_demand
        position = sim.inventory + _pipeline_total(sim)
        return max(0.0, min(S - position, controller_cap))
    return decide


def constant_policy() -> Policy:
    """Weak strawman kept only for contrast: order the baseline demand, always."""
    def decide(sim: BusinessSim) -> float:
        return sim.p.baseline_demand
    return decide


def helm_policy(controller: RecedingHorizonController) -> Policy:
    def decide(sim: BusinessSim) -> float:
        H = controller.p.horizon
        dec = controller.plan(
            inv0=sim.inventory,
            cash0=sim.cash,
            forecast=sim.forecast(H),
            target=sim.target_trajectory(H + 1),
            pending_arrivals=sim.pipeline_arrivals(H),
        )
        return dec.order_qty
    return decide


def helm_verified_policy(controller: RecedingHorizonController) -> Policy:
    """The controller's order, then the verifier's HARD cash-floor clamp: never
    spend this period if it would push cash below the floor. This is the same
    guard the deployed agent applies; the eval uses it to measure whether the
    verifier actually reduces cash-floor breaches."""
    base = helm_policy(controller)

    def decide(sim: BusinessSim) -> float:
        qty = base(sim)
        floor = sim.p.cash_floor
        cost = sim.p.unit_cost * qty
        if cost > 0 and sim.cash - cost < floor:
            affordable = max(0.0, sim.cash - floor) / sim.p.unit_cost
            qty = max(0.0, min(qty, affordable))
        return qty
    return decide


def helm_signal_policy(controller: RecedingHorizonController, adjustment) -> Policy:
    """Helm, but the controller plans against a forecast adjusted by a verified
    signal. Identical to helm_policy except the demand fed to the optimizer
    carries the signal's per-period deltas, so the controller can pre-position
    stock for a disruption that has been announced but not yet realized, which a
    flat forecast cannot. `adjustment` is any object with `delta_for(period)`
    (a verifier-sanitized ForecastAdjustment)."""
    def decide(sim: BusinessSim) -> float:
        H = controller.p.horizon
        base = sim.forecast(H)
        t = sim.t
        fc = [max(0.0, float(base[i]) + adjustment.delta_for(t + i)) for i in range(H)]
        dec = controller.plan(
            inv0=sim.inventory,
            cash0=sim.cash,
            forecast=fc,
            target=sim.target_trajectory(H + 1),
            pending_arrivals=sim.pipeline_arrivals(H),
        )
        return dec.order_qty
    return decide


def run_policy(sim: BusinessSim, decide: Policy) -> RunMetrics:
    while not sim.done():
        sim.step(decide(sim))
    return RunMetrics.from_history(sim)


# --- scenario generation ----------------------------------------------------
def make_scenarios(n: int, seed: int = 0) -> list[Scenario]:
    import numpy as np

    rng = np.random.default_rng(seed)
    scenarios: list[Scenario] = []
    for i in range(n):
        baseline = float(rng.integers(25, 70))
        noise = float(rng.uniform(2.0, 10.0))
        lead = int(rng.integers(1, 4))
        target = float(rng.integers(80, 180))
        n_periods = 24
        unit_cost = 8.0
        # thin margins in some scenarios so cash can actually bind
        price = round(unit_cost * float(rng.uniform(1.05, 2.5)), 2)
        # some scenarios start cash-tight with a positive floor
        init_cash = float(rng.integers(1200, 6000))
        cash_floor = float(rng.choice([0.0, 0.0, 0.0, 500.0, 1000.0]))
        params = BusinessParams(
            price=price,
            unit_cost=unit_cost,
            baseline_demand=baseline,
            demand_noise_sd=noise,
            lead_time=lead,
            target_inventory=target,
            init_inventory=target,
            init_cash=init_cash,
            cash_floor=cash_floor,
        )
        shocks: dict[int, float] = {}
        n_shocks = int(rng.integers(0, 3))
        for _ in range(n_shocks):
            period = int(rng.integers(2, n_periods - 2))
            # a demand shock up or down, scaled to the baseline
            delta = float(rng.uniform(-0.8, 1.5)) * baseline
            shocks[period] = round(delta, 1)
        scenarios.append(Scenario(
            seed=int(rng.integers(1, 1_000_000)),
            params=params, shocks=shocks, n_periods=n_periods,
            label=f"s{i:03d}(base={baseline:.0f},lead={lead},target={target:.0f},shocks={len(shocks)})",
        ))
    return scenarios


# --- evaluation -------------------------------------------------------------
def evaluate(n: int = 200, seed: int = 0, horizon: int = 8) -> dict:
    scenarios = make_scenarios(n, seed=seed)
    rows = []
    helm_wins_dev = 0
    helm_wins_fill = 0
    losses: list[dict] = []

    for sc in scenarios:
        cparams = ControllerParams(
            horizon=horizon,
            max_order=200.0,
            unit_cost=sc.params.unit_cost,
            price=sc.params.price,
            cash_floor=sc.params.cash_floor,
            lead_time=sc.params.lead_time,
        )
        controller = RecedingHorizonController(cparams)

        m_helm = run_policy(sc.fresh_sim(), helm_policy(controller))
        m_base = run_policy(sc.fresh_sim(), base_stock_policy())
        m_const = run_policy(sc.fresh_sim(), constant_policy())
        m_helm_v = run_policy(sc.fresh_sim(), helm_verified_policy(controller))

        dev_win = m_helm.cum_abs_deviation < m_base.cum_abs_deviation
        fill_win = m_helm.fill_rate > m_base.fill_rate + 1e-9
        helm_wins_dev += int(dev_win)
        helm_wins_fill += int(fill_win)
        if not dev_win:
            losses.append({
                "scenario": sc.label,
                "helm_dev": m_helm.cum_abs_deviation,
                "base_dev": m_base.cum_abs_deviation,
                "helm_fill": m_helm.fill_rate,
                "base_fill": m_base.fill_rate,
            })
        rows.append((m_helm, m_base, m_const, m_helm_v))

    def agg(idx, attr):
        return [getattr(r[idx], attr) for r in rows]

    helm_fill = agg(0, "fill_rate")
    base_fill = agg(1, "fill_rate")
    # service tie counts fairly: base-stock is "not worse" when within a small margin
    base_fill_not_worse = sum(1 for h, b in zip(helm_fill, base_fill) if b >= h - 1e-9)

    summary = {
        "n_scenarios": n,
        # circular-by-construction (the controller optimizes deviation)
        "helm_mean_deviation": round(mean(agg(0, "cum_abs_deviation")), 2),
        "base_stock_mean_deviation": round(mean(agg(1, "cum_abs_deviation")), 2),
        "constant_mean_deviation": round(mean(agg(2, "cum_abs_deviation")), 2),
        "helm_deviation_win_rate": round(helm_wins_dev / n, 3),
        # non-circular: service, capital held, cost, cash protection
        "helm_mean_fill": round(mean(helm_fill), 4),
        "base_stock_mean_fill": round(mean(base_fill), 4),
        "helm_fill_win_rate": round(helm_wins_fill / n, 3),
        "base_fill_not_worse_rate": round(base_fill_not_worse / n, 3),
        "helm_mean_avg_inventory": round(mean(agg(0, "avg_inventory")), 2),
        "base_stock_mean_avg_inventory": round(mean(agg(1, "avg_inventory")), 2),
        "helm_mean_order_cost": round(mean(agg(0, "order_cost")), 2),
        "base_stock_mean_order_cost": round(mean(agg(1, "order_cost")), 2),
        "helm_total_cash_breaches": sum(agg(0, "cash_floor_breaches")),
        "base_stock_total_cash_breaches": sum(agg(1, "cash_floor_breaches")),
        "helm_verified_total_cash_breaches": sum(agg(3, "cash_floor_breaches")),
        "helm_verified_mean_fill": round(mean(agg(3, "fill_rate")), 4),
        "helm_verified_mean_stockout_periods": round(mean(agg(3, "stockout_periods")), 2),
        "helm_mean_stockout_periods": round(mean(agg(0, "stockout_periods")), 2),
        "base_stock_mean_stockout_periods": round(mean(agg(1, "stockout_periods")), 2),
        "n_losses_vs_base": len(losses),
        "worst_losses": sorted(losses, key=lambda d: d["helm_dev"] - d["base_dev"],
                               reverse=True)[:5],
    }
    return summary
