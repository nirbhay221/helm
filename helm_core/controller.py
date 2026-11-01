"""Helm's brain: a receding-horizon (model-predictive) controller.

Each cycle the controller looks `horizon` periods ahead, plans supplier orders
that keep projected inventory on the target trajectory and cash above a floor,
then applies ONLY the first order. Next period it re-plans from the real,
observed state. That is the closed loop: it reacts to realized variance.

The program is a linear program (variance is measured as absolute deviation,
not squared, so it stays linear and solves fast and reliably). Integer
lot-sizing is deliberately NOT done here; the controller emits a continuous
target order, and procurement optimization (Awardsmith) turns it into a concrete
purchase. Keeping this core a simple, always-feasible LP is intentional: the
fragile thing in systems like this is an over-ambitious solver, not a plain
reliable one. Cash-floor and non-negativity pressures are modeled as penalized
slacks so the LP is always feasible and never throws at runtime.

Solver: OR-Tools GLOP (linear programming).
"""
from __future__ import annotations

from dataclasses import dataclass

from ortools.linear_solver import pywraplp


@dataclass
class ControllerParams:
    horizon: int = 8
    max_order: float = 200.0       # per-period order cap (budget/capacity)
    unit_cost: float = 8.0
    price: float = 20.0
    cash_floor: float = 0.0
    lead_time: int = 1
    dev_weight: float = 1.0        # weight on inventory deviation from target
    cash_weight: float = 0.05      # weight on cash dropping below the floor
    stockout_weight: float = 5.0   # weight on inventory going negative
    order_reg: float = 0.001       # tiny regularizer against needless ordering


@dataclass
class ControllerDecision:
    order_qty: float
    status: str
    projected_dev: float


class RecedingHorizonController:
    def __init__(self, params: ControllerParams | None = None) -> None:
        self.p = params or ControllerParams()

    def plan(
        self,
        inv0: float,
        cash0: float,
        forecast,
        target,
        pending_arrivals: dict[int, float] | None = None,
    ) -> ControllerDecision:
        p = self.p
        H = min(p.horizon, len(forecast))
        pending_arrivals = pending_arrivals or {}
        forecast = [float(x) for x in forecast]
        target = [float(x) for x in target]

        solver = pywraplp.Solver.CreateSolver("GLOP")
        if solver is None:  # pragma: no cover
            raise RuntimeError("OR-Tools GLOP solver unavailable")
        inf = solver.infinity()

        q = [solver.NumVar(0.0, p.max_order, f"q_{t}") for t in range(H)]
        inv = [solver.NumVar(-inf, inf, f"inv_{t}") for t in range(H + 1)]
        cash = [solver.NumVar(-inf, inf, f"cash_{t}") for t in range(H + 1)]
        dev = [solver.NumVar(0.0, inf, f"dev_{t}") for t in range(H + 1)]
        short = [solver.NumVar(0.0, inf, f"short_{t}") for t in range(H + 1)]
        neg = [solver.NumVar(0.0, inf, f"neg_{t}") for t in range(H + 1)]

        solver.Add(inv[0] == float(inv0))
        solver.Add(cash[0] == float(cash0))

        for t in range(H):
            arr = float(pending_arrivals.get(t, 0.0))
            if t - p.lead_time >= 0:
                solver.Add(inv[t + 1] == inv[t] + q[t - p.lead_time] + arr - forecast[t])
            else:
                solver.Add(inv[t + 1] == inv[t] + arr - forecast[t])
            solver.Add(cash[t + 1] == cash[t] + p.price * forecast[t] - p.unit_cost * q[t])

        for t in range(H + 1):
            tgt = target[t] if t < len(target) else target[-1]
            solver.Add(dev[t] >= inv[t] - tgt)
            solver.Add(dev[t] >= tgt - inv[t])
            solver.Add(short[t] >= p.cash_floor - cash[t])
            solver.Add(neg[t] >= -inv[t])

        solver.Minimize(
            p.dev_weight * solver.Sum(dev)
            + p.cash_weight * solver.Sum(short)
            + p.stockout_weight * solver.Sum(neg)
            + p.order_reg * solver.Sum(q)
        )

        result = solver.Solve()
        status = {
            pywraplp.Solver.OPTIMAL: "Optimal",
            pywraplp.Solver.FEASIBLE: "Feasible",
            pywraplp.Solver.INFEASIBLE: "Infeasible",
            pywraplp.Solver.UNBOUNDED: "Unbounded",
            pywraplp.Solver.ABNORMAL: "Abnormal",
            pywraplp.Solver.NOT_SOLVED: "NotSolved",
        }.get(result, "Unknown")

        q0 = q[0].solution_value() if (q and status in ("Optimal", "Feasible")) else 0.0
        projected_dev = sum(d.solution_value() for d in dev) if status in ("Optimal", "Feasible") else 0.0
        return ControllerDecision(
            order_qty=max(0.0, float(q0)),
            status=status,
            projected_dev=round(float(projected_dev), 2),
        )
