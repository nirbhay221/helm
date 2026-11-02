"""Helm's cash-and-payout controller for the marketplace.

A receding-horizon linear program. Each cycle it looks `horizon` periods ahead
and chooses how much to pay creators now so that they are paid as fast as
possible (minimize the outstanding balance over time) while cash never drops
below the floor plus the reserve required against chargebacks. It applies only
the first period's payout, then re-plans next period on the real observed state.

This is the Miller-Orr cash-management idea (keep cash between bounds at least
cost) generalized to a rolling horizon, the bridge Salas-Molina (arXiv
2401.08548) draws between stochastic cash management and model-predictive
control. The floor-plus-reserve requirement is modeled as a penalized slack so
the program is always feasible and never throws.

Solver: OR-Tools GLOP (linear programming).
"""
from __future__ import annotations

from dataclasses import dataclass

from ortools.linear_solver import pywraplp


@dataclass
class CashPayoutParams:
    horizon: int = 8
    take_rate: float = 0.20
    refund_rate: float = 0.05
    chargeback_rate: float = 0.03
    owed_weight: float = 1.0        # push outstanding creator balances down (pay fast)
    reserve_weight: float = 50.0    # keep cash above floor+reserve (near-hard)
    pay_reg: float = 0.001          # tiny smoothing against needless churn


@dataclass
class CashPayoutDecision:
    payout: float
    status: str
    projected_owed: float


class CashPayoutController:
    def __init__(self, params: CashPayoutParams | None = None) -> None:
        self.p = params or CashPayoutParams()

    def plan(
        self,
        owed0: float,
        cash0: float,
        forecast_gmv,
        reserve_floor,
        cash_floor: float = 0.0,
    ) -> CashPayoutDecision:
        p = self.p
        g = [float(x) for x in forecast_gmv]
        H = min(p.horizon, len(g))
        reserve_floor = [float(x) for x in reserve_floor]

        solver = pywraplp.Solver.CreateSolver("GLOP")
        if solver is None:  # pragma: no cover
            raise RuntimeError("OR-Tools GLOP solver unavailable")
        inf = solver.infinity()

        pay = [solver.NumVar(0.0, inf, f"pay_{t}") for t in range(H)]
        owed = [solver.NumVar(0.0, inf, f"owed_{t}") for t in range(H + 1)]
        cash = [solver.NumVar(-inf, inf, f"cash_{t}") for t in range(H + 1)]
        short = [solver.NumVar(0.0, inf, f"short_{t}") for t in range(H + 1)]

        solver.Add(owed[0] == float(owed0))
        solver.Add(cash[0] == float(cash0))

        for t in range(H):
            earnings = (1.0 - p.take_rate) * g[t]
            net_in = g[t] * (1.0 - p.refund_rate - p.chargeback_rate)
            solver.Add(owed[t + 1] == owed[t] + earnings - pay[t])
            solver.Add(cash[t + 1] == cash[t] + net_in - pay[t])
            solver.Add(pay[t] <= owed[t])           # cannot pay more than is owed

        for t in range(H + 1):
            rf = reserve_floor[t] if t < len(reserve_floor) else reserve_floor[-1]
            # shortfall below (floor + reserve); heavily penalized, so near-hard
            solver.Add(short[t] >= (cash_floor + rf) - cash[t])

        solver.Minimize(
            p.owed_weight * solver.Sum(owed)
            + p.reserve_weight * solver.Sum(short)
            + p.pay_reg * solver.Sum(pay)
        )

        result = solver.Solve()
        status = {
            pywraplp.Solver.OPTIMAL: "Optimal",
            pywraplp.Solver.FEASIBLE: "Feasible",
            pywraplp.Solver.INFEASIBLE: "Infeasible",
            pywraplp.Solver.UNBOUNDED: "Unbounded",
        }.get(result, "Unknown")

        pay0 = pay[0].solution_value() if (pay and status in ("Optimal", "Feasible")) else 0.0
        projected = sum(o.solution_value() for o in owed) if status in ("Optimal", "Feasible") else 0.0
        return CashPayoutDecision(
            payout=max(0.0, float(pay0)),
            status=status,
            projected_owed=round(float(projected), 2),
        )
