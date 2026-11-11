"""Reconciliation: does what we think settled match what PayPal actually did.

An agent that moves money must not trust its own belief about what happened. This desk
matches the platform's internal expectation (what the ledger says should have settled)
against the processor's own record (what PayPal reports), by reference, and flags every
discrepancy deterministically before anything is written back or reported as done:

  - missing: we expected a settlement the processor has no record of (do NOT report done);
  - amount_mismatch: the processor settled a different amount than expected;
  - unexpected: the processor shows a settlement we never initiated (investigate);
  - duplicate: the same reference settled more than once (possible double charge).

The matching is deterministic; a model may only narrate the discrepancies, never decide
them. This is the "never say done until the processor's ledger agrees" rule, enforced.
"""
from __future__ import annotations

from collections import Counter
from typing import List


def _index(rows: List[dict]) -> dict:
    out = {}
    for r in rows or []:
        out.setdefault(str(r.get("ref")), []).append(r)
    return out


def reconcile(expected: List[dict], actual: List[dict], tol: float = 0.01) -> dict:
    """Match expected settlements against the processor's actual records by reference.
    Each row is {ref, amount} (actual rows may also carry a status). Returns the matched
    set and a typed list of discrepancies."""
    exp_by, act_by = _index(expected), _index(actual)
    matched, discrepancies = [], []

    act_counts = Counter(str(r.get("ref")) for r in actual or [])
    for ref, n in act_counts.items():
        if n > 1:
            discrepancies.append({"type": "duplicate", "ref": ref, "count": n,
                                  "detail": "settled %d times for the same reference" % n})

    for ref, exp_rows in exp_by.items():
        exp_amt = round(sum(float(r.get("amount", 0)) for r in exp_rows), 2)
        if ref not in act_by:
            discrepancies.append({"type": "missing", "ref": ref, "expected": exp_amt,
                                  "detail": "expected to settle but the processor has no record; do not report done"})
            continue
        act_amt = round(sum(float(r.get("amount", 0)) for r in act_by[ref]), 2)
        if abs(act_amt - exp_amt) > tol:
            discrepancies.append({"type": "amount_mismatch", "ref": ref,
                                  "expected": exp_amt, "actual": act_amt,
                                  "detail": "processor settled %.2f, expected %.2f" % (act_amt, exp_amt)})
        else:
            matched.append({"ref": ref, "amount": exp_amt})

    for ref in act_by:
        if ref not in exp_by:
            amt = round(sum(float(r.get("amount", 0)) for r in act_by[ref]), 2)
            discrepancies.append({"type": "unexpected", "ref": ref, "actual": amt,
                                  "detail": "processor settled a reference we never initiated"})

    return {"matched": matched, "discrepancies": discrepancies,
            "matched_count": len(matched), "discrepancy_count": len(discrepancies),
            "clean": len(discrepancies) == 0,
            "matched_value": round(sum(m["amount"] for m in matched), 2)}
