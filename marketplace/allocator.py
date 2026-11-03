"""Multi-objective payout allocation across many global creators.

The thin version paid creators on one factor (settlement timing). This allocates
a cycle's safe budget across any number of creators on several competing factors
at once, the way the research says to do it: the agent sets WEIGHTS over the
objectives (validated and bounded, so one cannot be talked past), and this solver
computes the allocation. Per creator the factors are, each normalized to [0, 1]
so the weights are comparable (the failure mode is unnormalized terms letting one
objective dominate):

  priority         how much we want to pay them now (tenure, SLA, how long waited)
  net = 1 - tax    fraction the creator actually receives after withholding
  risk             chargeback / fraud probability (a penalty)
  fx               platform cost to pay in their currency (a penalty)

The value of a dollar paid to creator i is
    w.speed*priority_i + w.tax*net_i - w.risk*risk_i - w.fx*fx_i
and we maximize the total value paid, subject to the budget and to not paying any
creator more than they are owed. Risky, costly, low-priority creators score low
and are naturally held; the agent shifts that by moving the weights.

Solver: OR-Tools GLOP (linear programming), so it scales to thousands of payees.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ortools.linear_solver import pywraplp

# US non-resident withholding: 30% default, lower where a treaty applies. Mirrors
# the Tollgate module; US creators are domestic (0).
DEFAULT_WITHHOLDING = 0.30
TREATY_WITHHOLDING = {"US": 0.0, "IN": 0.15, "BR": 0.15, "CN": 0.10, "GB": 0.0,
                      "DE": 0.0, "CA": 0.0, "MX": 0.10, "NG": 0.30, "PH": 0.20}
CURRENCY = {"US": "USD", "IN": "INR", "BR": "BRL", "CN": "CNY", "GB": "GBP",
            "DE": "EUR", "CA": "CAD", "MX": "MXN", "NG": "NGN", "PH": "PHP"}
# rough platform FX cost to deliver in the local currency (0 for USD)
FX_COST = {"USD": 0.0, "INR": 0.012, "BRL": 0.02, "CNY": 0.015, "GBP": 0.008,
           "EUR": 0.008, "CAD": 0.01, "MXN": 0.02, "NGN": 0.03, "PHP": 0.02}


@dataclass
class AllocCreator:
    name: str
    country: str
    owed: float                 # payable amount available this cycle
    risk: float                 # 0..1 chargeback/fraud risk
    priority: float             # 0..1 urgency (higher = pay sooner)

    @property
    def currency(self) -> str:
        return CURRENCY.get(self.country, "USD")

    @property
    def withholding(self) -> float:
        return TREATY_WITHHOLDING.get(self.country, DEFAULT_WITHHOLDING)

    @property
    def fx_cost(self) -> float:
        return FX_COST.get(self.currency, 0.02)


@dataclass
class Weights:
    speed: float = 1.0
    tax: float = 1.0
    risk: float = 1.0
    fx: float = 1.0


@dataclass
class Constraints:
    """Hard rules the solver must obey, compiled from a plain-English policy.
    These bound the optimizer; the weights only tilt it."""
    max_fraction_per_creator: float = 1.0    # no creator gets more than this x budget
    exclude_countries: tuple = ()            # pay no one from these countries this cycle
    max_risk: float = 1.0                    # never pay a creator riskier than this
    min_priority: float = 0.0                # only pay creators at least this urgent

    def allows(self, c: "AllocCreator") -> bool:
        return (c.country not in self.exclude_countries
                and c.risk <= self.max_risk + 1e-9
                and c.priority >= self.min_priority - 1e-9)


@dataclass
class AllocResult:
    status: str
    total_paid: float
    lines: list[dict] = field(default_factory=list)   # {name,country,currency,amount,net}
    net_delivered: float = 0.0        # sum amount*(1-withholding)
    tax_withheld: float = 0.0
    fx_cost: float = 0.0
    risk_exposure: float = 0.0        # sum amount*risk
    paid_count: int = 0


def validate_weights(raw: dict, lo: float = 0.0, hi: float = 3.0) -> tuple[Weights, list[str]]:
    """Clamp each weight to [lo, hi] and guarantee at least one is positive, so the
    agent cannot hand the solver a degenerate or out-of-range objective."""
    violations: list[str] = []

    def _clip(name: str, default: float) -> float:
        try:
            v = float(raw.get(name, default))
        except (TypeError, ValueError):
            v = default
        if v < lo or v > hi:
            violations.append(f"{name} weight {round(v, 2)} out of [{lo},{hi}]; clamped")
            v = max(lo, min(hi, v))
        return v

    w = Weights(speed=_clip("speed", 1.0), tax=_clip("tax", 1.0),
                risk=_clip("risk", 1.0), fx=_clip("fx", 1.0))
    if w.speed + w.tax + w.risk + w.fx <= 1e-9:
        violations.append("all weights were zero; reset speed to 1.0")
        w.speed = 1.0
    return w, violations


def allocate(creators: list[AllocCreator], budget: float, weights: Weights,
             constraints: "Constraints | None" = None) -> AllocResult:
    budget = max(0.0, float(budget))
    con = constraints or Constraints()
    solver = pywraplp.Solver.CreateSolver("GLOP")
    if solver is None:  # pragma: no cover
        raise RuntimeError("OR-Tools GLOP solver unavailable")

    cap = con.max_fraction_per_creator * budget
    x = {}
    for c in creators:
        ub = min(max(0.0, c.owed), cap) if con.allows(c) else 0.0   # held if policy forbids
        x[c.name] = solver.NumVar(0.0, ub, f"x_{c.name}")
    solver.Add(solver.Sum(list(x.values())) <= budget)

    obj = []
    for c in creators:
        net = 1.0 - c.withholding
        value = (weights.speed * c.priority + weights.tax * net
                 - weights.risk * c.risk - weights.fx * c.fx_cost)
        obj.append(value * x[c.name])
    solver.Maximize(solver.Sum(obj))

    result = solver.Solve()
    status = {pywraplp.Solver.OPTIMAL: "Optimal", pywraplp.Solver.FEASIBLE: "Feasible"}.get(
        result, "Infeasible")
    if status not in ("Optimal", "Feasible"):
        return AllocResult(status=status, total_paid=0.0)

    lines, total, net_d, tax, fx, risk = [], 0.0, 0.0, 0.0, 0.0, 0.0
    for c in creators:
        amt = x[c.name].solution_value()
        if amt <= 1e-6:
            continue
        lines.append({"name": c.name, "country": c.country, "currency": c.currency,
                      "amount": round(amt, 2), "net": round(amt * (1 - c.withholding), 2)})
        total += amt
        net_d += amt * (1 - c.withholding)
        tax += amt * c.withholding
        fx += amt * c.fx_cost
        risk += amt * c.risk
    lines.sort(key=lambda l: l["amount"], reverse=True)
    return AllocResult(status=status, total_paid=round(total, 2), lines=lines,
                       net_delivered=round(net_d, 2), tax_withheld=round(tax, 2),
                       fx_cost=round(fx, 2), risk_exposure=round(risk, 2),
                       paid_count=len(lines))


# Rough share of creators by country, reflecting where creator populations
# actually concentrate (India, US and Brazil large; a long international tail).
_COUNTRY_WEIGHTS = {"IN": 22, "US": 20, "BR": 11, "PH": 9, "NG": 8, "MX": 7,
                    "CN": 8, "GB": 6, "DE": 5, "CA": 4}


def make_global_creators(n: int, seed: int = 0) -> list[AllocCreator]:
    """A realistic creator population at scale.

    Earnings owed follow a heavy long tail (a few creators owed a lot, most owed
    little), the creator economy's actual shape. Country mix follows real creator
    populations. Risk is mostly low but higher for brand-new creators and those
    with recent disputes; priority rises the longer a creator has been waiting.
    Not real people, but the right shape, so the allocation behaves like the real
    problem rather than uniform noise.
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    countries = list(_COUNTRY_WEIGHTS.keys())
    probs = np.array([_COUNTRY_WEIGHTS[c] for c in countries], dtype=float)
    probs /= probs.sum()

    out: list[AllocCreator] = []
    for i in range(n):
        country = str(rng.choice(countries, p=probs))
        # long-tail earnings owed (log-normal): median ~$90, tail into the thousands
        owed = float(np.clip(rng.lognormal(mean=np.log(90), sigma=1.1), 5, 20000))
        tenure_days = float(rng.lognormal(mean=np.log(150), sigma=1.0))   # many new, some veteran
        is_new = tenure_days < 30
        disputes = int(rng.poisson(0.3))
        risk = float(rng.beta(2, 10))                       # baseline low
        if is_new:
            risk += 0.35
        risk += min(0.4, 0.12 * disputes)
        risk = float(np.clip(risk, 0.0, 1.0))
        days_waiting = float(rng.exponential(9))            # most paid recently, some waiting
        priority = float(np.clip(1.0 - np.exp(-days_waiting / 12.0), 0.0, 1.0))
        out.append(AllocCreator(name=f"c{i:05d}_{country}", country=country,
                                owed=round(owed, 2), risk=round(risk, 3),
                                priority=round(priority, 3)))
    return out
