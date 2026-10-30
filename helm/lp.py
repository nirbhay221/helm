"""A small linear / mixed-integer program builder on top of scipy's HiGHS bindings.

Variables are created by name and constraints are written as {var: coeff} dicts,
which keeps the Navigator and Quartermaster formulations readable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


@dataclass
class Solution:
    status: str
    objective: float
    values: dict[str, float]

    @property
    def ok(self) -> bool:
        return self.status == "optimal"

    def __getitem__(self, name: str) -> float:
        return self.values[name]


@dataclass
class Model:
    names: list[str] = field(default_factory=list)
    index: dict[str, int] = field(default_factory=dict)
    lb: list[float] = field(default_factory=list)
    ub: list[float] = field(default_factory=list)
    integer: list[int] = field(default_factory=list)
    cost: dict[str, float] = field(default_factory=dict)
    rows: list[tuple[dict[str, float], float, float]] = field(default_factory=list)

    def var(self, name: str, lb: float = 0.0, ub: float = np.inf, integer: bool = False) -> str:
        if name in self.index:
            raise ValueError(f"duplicate variable {name}")
        self.index[name] = len(self.names)
        self.names.append(name)
        self.lb.append(lb)
        self.ub.append(ub)
        self.integer.append(1 if integer else 0)
        return name

    def binary(self, name: str) -> str:
        return self.var(name, 0.0, 1.0, integer=True)

    def minimize(self, terms: dict[str, float]) -> None:
        for name, coeff in terms.items():
            self.cost[name] = self.cost.get(name, 0.0) + coeff

    def add(self, terms: dict[str, float], lo: float = -np.inf, hi: float = np.inf) -> None:
        self.rows.append((terms, lo, hi))

    def eq(self, terms: dict[str, float], rhs: float) -> None:
        self.add(terms, rhs, rhs)

    def solve(self, time_limit: float = 10.0) -> Solution:
        n = len(self.names)
        c = np.zeros(n)
        for name, coeff in self.cost.items():
            c[self.index[name]] = coeff
        constraints = []
        if self.rows:
            a = lil_matrix((len(self.rows), n))
            lo = np.empty(len(self.rows))
            hi = np.empty(len(self.rows))
            for r, (terms, l, h) in enumerate(self.rows):
                for name, coeff in terms.items():
                    a[r, self.index[name]] += coeff
                lo[r], hi[r] = l, h
            constraints.append(LinearConstraint(a.tocsr(), lo, hi))
        res = milp(
            c,
            constraints=constraints,
            integrality=np.array(self.integer),
            bounds=Bounds(np.array(self.lb), np.array(self.ub)),
            options={"time_limit": time_limit},
        )
        if res.x is None:
            return Solution("infeasible" if res.status == 2 else f"failed:{res.status}", np.inf, {})
        values = {name: float(res.x[i]) for i, name in enumerate(self.names)}
        return Solution("optimal" if res.status == 0 else f"status:{res.status}", float(res.fun), values)
