"""Build the single source of truth for the dashboard.

Runs the whole system once and returns a JSON-serializable payload the charts
read: the variance money shot (forecast vs actual, inventory vs target, with
Helm holding the line while an uncontrolled baseline drifts), cash against the
floor, the per-cycle control journal, Awardsmith's supplier split beating the
naive buy, the payout engine's Bulwark before/after and tax, and the honest
evaluation summary.
"""
from __future__ import annotations

import functools

from arms.awardsmith import AwardsmithSolver, DiscountTier, SupplierQuote, naive_single_supplier_cost
from arms.payout_engine import Contribution, Party, run_payout_engine
from council.loop import HelmLoop
from evaluation import constant_policy, evaluate, run_policy
from helm_core import ControllerParams, RecedingHorizonController
from paypal import Ledger, PayPalClient
from simulator import BusinessParams, BusinessSim
from simulator.real_demand import P263_WEEKLY, PLANNED_DEMAND, PRODUCT_CODE

N_PERIODS = len(P263_WEEKLY)


def _suppliers() -> list[SupplierQuote]:
    return [
        SupplierQuote("Alpha", [DiscountTier(0, 9.0)], capacity=200),
        SupplierQuote("Beta", [DiscountTier(0, 8.5), DiscountTier(40, 8.0)], capacity=200),
        SupplierQuote("Gamma", [DiscountTier(50, 7.5)], capacity=120),
    ]


def _scenario_params() -> BusinessParams:
    # Real recorded demand (UCI product P263). The business plans around a flat
    # PLANNED_DEMAND; the actual series surges and collapses on its own.
    return BusinessParams(
        price=20.0, unit_cost=8.0, lead_time=1,
        init_inventory=40.0, init_cash=1500.0, target_inventory=40.0,
        cash_floor=0.0, baseline_demand=PLANNED_DEMAND,
        demand_series=list(P263_WEEKLY),
    )


def build_dashboard_data() -> dict:
    params = _scenario_params()
    suppliers = _suppliers()
    controller = RecedingHorizonController(ControllerParams(horizon=8))

    # Helm run (controller + Awardsmith + journal) and an uncontrolled baseline,
    # both on the same real demand series so the only difference is the control.
    helm_sim = BusinessSim(params, seed=7, n_periods=N_PERIODS)
    loop = HelmLoop(helm_sim, controller, suppliers)
    journal = loop.run()

    base_sim = BusinessSim(params, seed=7, n_periods=N_PERIODS)
    run_policy(base_sim, constant_policy())

    periods = [o.period for o in helm_sim.history]
    variance = {
        "periods": periods,
        "forecast_demand": [o.forecast_demand for o in helm_sim.history],
        "actual_demand": [o.demand for o in helm_sim.history],
        "source": f"real recorded weekly demand, UCI product {PRODUCT_CODE}",
    }
    inventory = {
        "periods": periods,
        "target": [o.target_inventory for o in helm_sim.history],
        "helm": [o.inventory for o in helm_sim.history],
        "uncontrolled": [o.inventory for o in base_sim.history],
    }
    cash = {
        "periods": periods,
        "helm": [o.cash for o in helm_sim.history],
        "floor": params.cash_floor,
    }
    journal_rows = [{
        "period": j.period,
        "order_target": round(j.order_target, 1),
        "ordered_qty": round(j.ordered_qty, 1),
        "order_cost": round(j.order_cost, 2),
        "suppliers": [{"name": n, "qty": round(q, 1), "price": p} for n, q, p in j.supplier_split],
        "inventory_after": round(j.inventory_after, 1),
        "cash_after": round(j.cash_after, 2),
        "deviation_after": j.deviation_after,
    } for j in journal]

    # Awardsmith panel: a restock above the cheapest supplier's capacity, so the
    # optimal multi-supplier split genuinely beats the naive single-supplier buy
    target = 150.0
    award = AwardsmithSolver(suppliers).allocate(target)
    naive = naive_single_supplier_cost(suppliers, target)
    awardsmith = {
        "target": target,
        "lines": [{"supplier": l.supplier, "quantity": l.quantity,
                   "unit_price": l.unit_price, "line_cost": l.line_cost}
                  for l in award.lines],
        "optimal_cost": award.total_cost,
        "naive_cost": None if naive == float("inf") else naive,
        "savings": None if naive == float("inf") else round(naive - award.total_cost, 2),
    }

    # Payout engine panel (demo PayPal)
    client, ledger = PayPalClient(env={"DEMO_MODE": "1"}), Ledger()
    pe = run_payout_engine(
        1000.0,
        [Contribution("A", {"c1", "c2", "c3", "c4"}),
         Contribution("B", {"c3", "c4", "c5"}),
         Contribution("C", {"c5", "c6"})],
        [Party("A", 400), Party("B", 300), Party("C", 150)],
        Party("Z", 500, cluster="Z", honest=False),
        {"A": {"email": "a@ex.com", "country": "US"},
         "B": {"email": "b@ex.com", "country": "IN"},
         "C": {"email": "c@ex.com", "country": "BR"},
         "Z": {"email": "z@ex.com", "country": "US"}},
        client, ledger, sender_batch_id="dash-payengine", purpose="COMMISSION",
        fail_items=set(), approved=True)
    payout_engine = {
        "mete": pe.mete.shares,
        "bulwark": {
            "naive_cheater_take": pe.bulwark.naive_cheater_take,
            "hardened_cheater_take": pe.bulwark.hardened_cheater_take,
            "honest_share": pe.bulwark.honest_cheater_share,
            "hardening_applied": pe.bulwark.hardening_applied,
            "defeated": pe.bulwark.defeated,
        },
        "clearwright_ok": pe.clearwright.ok,
        "tollgate": {"gross": pe.tollgate.total_gross,
                     "withheld": pe.tollgate.total_withheld,
                     "net": pe.tollgate.total_net},
        "keystone": {"status": pe.keystone.status, "batch_id": pe.keystone.batch_id,
                     "paid": pe.keystone.paid_total, "conserved": pe.keystone.conserved},
    }

    # Honest evaluation (smaller n for responsiveness)
    ev = evaluate(n=120, seed=0)
    evaluation = {
        "n": ev["n_scenarios"],
        "deviation": {"helm": ev["helm_mean_deviation"], "base_stock": ev["base_stock_mean_deviation"]},
        "fill": {"helm": ev["helm_mean_fill"], "base_stock": ev["base_stock_mean_fill"]},
        "avg_inventory": {"helm": ev["helm_mean_avg_inventory"],
                          "base_stock": ev["base_stock_mean_avg_inventory"]},
        "cash_breaches": {"raw_helm": ev["helm_total_cash_breaches"],
                          "verified_helm": ev["helm_verified_total_cash_breaches"],
                          "base_stock": ev["base_stock_total_cash_breaches"]},
    }

    return {
        "variance": variance,
        "inventory": inventory,
        "cash": cash,
        "journal": journal_rows,
        "awardsmith": awardsmith,
        "payout_engine": payout_engine,
        "evaluation": evaluation,
        "cumulative_deviation": {
            "helm": helm_sim.cumulative_inv_deviation(),
            "uncontrolled": round(sum(abs(o.inventory - o.target_inventory)
                                      for o in base_sim.history), 2),
        },
    }


@functools.lru_cache(maxsize=1)
def dashboard_data_cached() -> dict:
    """The dashboard payload, computed once and reused.

    A full build runs the controller loop plus a 120-scenario evaluation (about
    five seconds). The inputs are fixed seeds, so the result is identical every
    time; recomputing it on each page load would make every visitor wait. The
    server warms this once at startup and serves the cached payload thereafter.
    """
    return build_dashboard_data()
