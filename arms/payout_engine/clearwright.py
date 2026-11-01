"""Clearwright: legality pre-flight as a deterministic rail-permission check.

Before any money moves, every planned money edge must map to an allowed purpose
on an allowed rail, nothing may pool in the operator (no custody), and the
operator must never sit in the middle of someone else's money (no transmitting).
This is a plain rule check against a permission table, not a theorem prover,
on purpose: the fragile part of such systems is always the over-ambitious proof,
not the simple reliable check. Clearwright returns the exact offending edge and a
suggested fix when a plan is illegal.
"""
from __future__ import annotations

from dataclasses import dataclass, field

OPERATOR = "operator"

# rail -> the purposes that rail is permitted to carry
RAIL_PERMISSIONS = {
    "payouts": {"COMMISSION", "REBATE", "REWARD", "INCENTIVE"},
    "orders": {"SUPPLIER_GOODS", "CUSTOMER_PAYMENT"},
}
# purposes that are never allowed on any rail here
FORBIDDEN_PURPOSES = {"PAYROLL", "WAGES", "SALARY", "LOAN", "INVESTMENT_RETURN"}


@dataclass
class MoneyEdge:
    src: str
    dst: str
    amount: float
    purpose: str
    rail: str


@dataclass
class Violation:
    edge: MoneyEdge
    reason: str
    fix: str


@dataclass
class ClearwrightResult:
    ok: bool
    violations: list = field(default_factory=list)


def check_plan(edges: list[MoneyEdge]) -> ClearwrightResult:
    violations: list[Violation] = []
    inflow_to_operator = 0.0
    outflow_from_operator = 0.0

    for e in edges:
        purpose = (e.purpose or "").upper()
        rail = (e.rail or "").lower()

        if purpose in FORBIDDEN_PURPOSES:
            violations.append(Violation(
                e, f"purpose '{purpose}' is never permitted",
                "remove this edge; this category cannot settle on these rails"))
            continue
        allowed = RAIL_PERMISSIONS.get(rail)
        if allowed is None:
            violations.append(Violation(
                e, f"unknown rail '{rail}'",
                f"use one of {sorted(RAIL_PERMISSIONS)}"))
        elif purpose not in allowed:
            violations.append(Violation(
                e, f"purpose '{purpose}' is not allowed on rail '{rail}'",
                f"allowed on '{rail}': {sorted(allowed)}"))

        # custody / transmitter accounting
        if e.dst == OPERATOR and purpose != "CUSTOMER_PAYMENT":
            inflow_to_operator += e.amount
        if e.src == OPERATOR:
            outflow_from_operator += e.amount
        if e.src != OPERATOR and e.dst != OPERATOR:
            violations.append(Violation(
                e, "money moves between two third parties through the plan",
                "every edge must originate from the operator's own account"))

    # no custody: the operator must not take in third-party money to re-disburse
    if inflow_to_operator > 1e-6:
        violations.append(Violation(
            MoneyEdge(OPERATOR, OPERATOR, round(inflow_to_operator, 2), "POOLING", "n/a"),
            "third-party funds would pool in the operator (custody / transmitting)",
            "pay each recipient directly from the operator; never collect-then-forward"))

    return ClearwrightResult(ok=not violations, violations=violations)
