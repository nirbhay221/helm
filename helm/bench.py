"""Three captains, same storms: replay the same business and shocks across many seeds.

  ghost  does nothing (where the business drifts without anyone steering)
  rule   reorder point with one preferred supplier and a fixed commission, the common approach
  helm   the full loop: forecast, Navigator, Quartermaster, Validator

Metrics: distance from the owner's inventory plan, lost sales, weeks below the cash floor,
final cash, and the bullwhip ratio (variance of orders over variance of demand; above 1
means the captain amplifies swings instead of absorbing them).

Run:  python -m helm.bench --seeds 20
"""

from __future__ import annotations

import argparse
import statistics as st
from dataclasses import dataclass

import numpy as np

from helm import scenario
from helm.loop import Helm, SimExecutor
from helm.model import Action, Order
from helm.sim.twin import DemandModel, Twin
from helm.validate.gates import Fact


@dataclass
class Score:
    captain: str
    inv_gap: float
    lost_units: float
    floor_weeks: int
    final_cash: float
    bullwhip: float


def _score(name: str, sc: scenario.Scenario, rows: list[tuple[float, float, float, float]]) -> Score:
    weeks = len(rows)
    gaps = [abs(inv - sc.business.inventory_target[w + 1]) for w, (inv, _, _, _) in enumerate(rows)]
    demand = np.array([d for _, _, _, d in rows])
    orders = np.array([o for _, _, o, _ in rows])
    bw = float(np.var(orders) / np.var(demand)) if np.var(demand) > 0 else 0.0
    cash = [c for _, c, _, _ in rows]
    return Score(name, float(np.mean(gaps)), 0.0, sum(c < sc.business.cash_floor for c in cash), cash[-1], bw)


def viral_fact(week: int) -> Fact:
    source = ("Creator @pawsandprints posted our harness in a video that passed 3M views overnight. "
              "Their last viral post tripled orders for about 3 weeks.")
    return Fact(
        "demand_shift", {"start_week": week, "weeks": 3, "multiplier": 3.0}, source,
        "Their last viral post tripled orders for about 3 weeks.", ("3 weeks",),
    )


def run_ghost(seed: int, weeks: int) -> Score:
    sc = scenario.build(weeks=weeks, seed=seed)
    s, rows, lost = sc.state, [], 0.0
    for _ in range(weeks):
        r = sc.twin.step(s, Action())
        s = r.state
        lost += r.lost
        rows.append((s.on_hand, s.cash, 0.0, r.demand))
    out = _score("ghost", sc, rows)
    out.lost_units = lost
    return out


def run_rule(seed: int, weeks: int) -> Score:
    sc = scenario.build(weeks=weeks, seed=seed)
    sup = next(x for x in sc.suppliers if x.id == "harborwhole")
    s, rows, lost = sc.state, [], 0.0
    for _ in range(weeks):
        avg = float(np.mean(s.demand_history[-4:]))
        position = s.on_hand + sum(q for _, q, _ in s.pipeline)
        reorder_point = avg * (sup.lead_weeks + 1)
        action = Action()
        if position < reorder_point:
            qty = min(max(int(avg * 4 - position + reorder_point), sup.moq), sup.capacity)
            if sup.order_cost(qty) <= s.cash - sc.business.cash_floor:
                action.orders.append(Order(sup.id, qty, sup.unit_price(qty), sup.fixed_fee))
        r = sc.twin.step(s, action)
        s = r.state
        lost += r.lost
        rows.append((s.on_hand, s.cash, float(sum(o.qty for o in action.orders)), r.demand))
    out = _score("rule", sc, rows)
    out.lost_units = lost
    return out


def run_helm(seed: int, weeks: int, with_lookout: bool = True, runs: int = 100) -> Score:
    sc = scenario.build(weeks=weeks, seed=seed)
    validator_twin = Twin(DemandModel(base=sc.twin.demand.base), sc.twin.price, sc.twin.lead_times)
    helm = Helm(validator_twin, sc.business, sc.limits, sc.suppliers, imagine_runs=runs)
    facts = {14: [viral_fact(14)]} if with_lookout else {}
    s, rows, lost = sc.state, [], 0.0
    ex = SimExecutor(sc.twin)
    for _ in range(weeks):
        c = helm.cycle(s, ex, facts.get(s.week))
        s = c.result.state
        lost += c.result.lost
        rows.append((s.on_hand, s.cash, float(sum(o.qty for o in c.executed.orders)), c.result.demand))
    out = _score("helm" if with_lookout else "helm (no lookout)", sc, rows)
    out.lost_units = lost
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--weeks", type=int, default=30)
    args = ap.parse_args()
    captains = {
        "ghost": lambda sd: run_ghost(sd, args.weeks),
        "rule": lambda sd: run_rule(sd, args.weeks),
        "helm (no lookout)": lambda sd: run_helm(sd, args.weeks, with_lookout=False),
        "helm": lambda sd: run_helm(sd, args.weeks, with_lookout=True),
    }
    print(f"{args.seeds} seeds x {args.weeks} weeks, viral spike at week 14 (3x for 3 weeks)\n")
    for name, fn in captains.items():
        scores = [fn(sd) for sd in range(args.seeds)]
        print(
            f"{name:18s} inventory gap {st.mean(x.inv_gap for x in scores):7.1f} units/wk | "
            f"lost sales {st.mean(x.lost_units for x in scores):7.1f} | "
            f"weeks under floor {st.mean(x.floor_weeks for x in scores):4.1f} | "
            f"final cash {st.mean(x.final_cash for x in scores):9.0f} | "
            f"bullwhip {st.mean(x.bullwhip for x in scores):5.2f}"
        )


if __name__ == "__main__":
    main()
