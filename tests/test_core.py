import numpy as np
import pytest

from helm import scenario
from helm.bench import viral_fact
from helm.forecast.conformal import forecast
from helm.loop import Helm, SimExecutor
from helm.model import Action, Order, Payout, Supplier, Tier
from helm.produce import navigator, quartermaster
from helm.sim.twin import DemandModel, Twin
from helm.validate import gates
from helm.validate.gates import Fact


def test_quartermaster_beats_lowest_unit_price_at_a_tier_boundary():
    # 1450 units: buying 1500 reaches the next tier and costs less than 1450 at the base price.
    s = scenario.SUPPLIERS
    best = quartermaster.solve(1450, s)
    naive = quartermaster.naive(1450, s)
    assert best.ok and best.qty >= 1450
    assert best.total_cost < naive.total_cost


def test_quartermaster_respects_minimums_and_capacity():
    s = [Supplier("a", "A", (Tier(100, 5.0),), 1, capacity=300)]
    plan = quartermaster.solve(40, s)
    assert plan.qty >= 100  # rounds up to the minimum order
    assert quartermaster.solve(500, s).status != "optimal"  # cannot exceed capacity


def test_navigator_stays_inside_spend_limit():
    sc = scenario.build()
    fc = forecast(sc.state.demand_history, 0, 8)
    tight = sc.limits.__class__(500.0, 0.05, 0.25, sc.limits.allowed_suppliers)
    nav = navigator.plan(sc.state, fc, sc.business, tight, sc.suppliers, 0.4, 2.5)
    spend = sum(q * c.unit_cost for q, c in zip(nav.order_qty.values(), navigator.supply_classes(sc.suppliers)))
    assert nav.ok and spend <= 500.0 + 1e-6


def test_forecast_band_contains_point():
    rng = np.random.default_rng(0)
    hist = list(100 + rng.normal(0, 10, 30))
    fc = forecast(hist, 30, 6)
    assert np.all(fc.lo <= fc.point) and np.all(fc.point <= fc.hi)
    assert np.all(np.diff(fc.hi - fc.lo) >= -1e-9)  # the band widens with the horizon


def test_evidence_gate_rejects_numbers_not_in_the_quote():
    good = viral_fact(5)
    assert gates.evidence([good]).passed
    forged = Fact("demand_shift", {"start_week": 5, "weeks": 3, "multiplier": 3.0}, good.source,
                  "tripled orders for about 6 weeks", ("6 weeks",))
    assert not gates.evidence([forged]).passed


def test_constraints_gate_blocks_paying_a_supplier_through_payouts_and_breaking_the_floor():
    sc = scenario.build()
    bad = Action(payouts=[Payout("fastfab", 100.0, "commission")])
    v = gates.constraints(bad, sc.state, sc.business, sc.suppliers)
    assert not v.passed and "Orders, not Payouts" in v.reason

    s = sc.suppliers[2]
    huge = Action(orders=[Order(s.id, 1500, s.unit_price(1500), s.fixed_fee)])
    v = gates.constraints(huge, sc.state, sc.business, sc.suppliers)
    assert not v.passed and v.detail["code"] == "cash"


def test_constraints_gate_catches_a_wrong_tier_price():
    sc = scenario.build()
    s = sc.suppliers[0]
    cheat = Action(orders=[Order(s.id, 60, 9.10, s.fixed_fee)])  # 9.10 needs 200 units
    assert not gates.constraints(cheat, sc.state, sc.business, sc.suppliers).passed


def test_envelope_escalates_instead_of_rejecting():
    sc = scenario.build()
    v = gates.envelope(Action(commission_rate=0.4), sc.limits)
    assert v.outcome == gates.ESCALATE


def test_loop_cuts_spend_after_a_cash_reject():
    sc = scenario.build()
    sc.state.cash = 2600.0  # barely above the 1500 floor
    vt = Twin(DemandModel(base=120.0), sc.twin.price, sc.twin.lead_times)
    helm = Helm(vt, sc.business, sc.limits, sc.suppliers, imagine_runs=40)
    c = helm.cycle(sc.state, SimExecutor(sc.twin))
    spend = c.executed.spend
    assert sc.state.cash - spend >= sc.business.cash_floor - 1e-6
    for a in c.attempts:
        for v in a.verdicts:
            assert v.outcome in (gates.PASS, gates.REJECT, gates.ESCALATE)


@pytest.mark.parametrize("seed", [0, 1])
def test_helm_beats_the_reorder_rule_on_plan_tracking(seed):
    from helm.bench import run_helm, run_rule
    h = run_helm(seed, 24, runs=40)
    r = run_rule(seed, 24)
    assert h.inv_gap < r.inv_gap
    assert h.floor_weeks == 0
