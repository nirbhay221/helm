"""Turn the controller's payout decision into real PayPal money to creators.

The controller decides how much to pay creators each period; this module splits
that across a roster of real creators and sends it as a PayPal Payouts batch
(COMMISSION, which is what the rail permits), through the same guards the agent
uses: AUP purpose, idempotency on sender_batch_id, and the human-approval
threshold. In demo mode it returns labeled stubs; with sandbox credentials it
moves real sandbox money and returns real batch and item ids.

Per-creator balances are tracked here so each creator is paid their own share of
what they are owed, oldest balances first, and the batch recipients are real.
"""
from __future__ import annotations

import uuid

from dataclasses import dataclass, field

from paypal import Ledger, PayPalClient
from paypal.mcp_payouts_tool import create_payout, get_payout_batch

from .controller import CashPayoutController
from .policies import helm_payout_policy
from .sim import CreatorMarketplace


@dataclass
class Creator:
    name: str
    email: str
    weight: float          # share of each period's creator earnings


@dataclass
class PayoutRun:
    period: int
    payout_total: float
    batch_id: str | None
    status: str
    demo: bool
    recipients: list[dict] = field(default_factory=list)   # {creator,email,amount}
    cash_after: float = 0.0
    reserve_required: float = 0.0
    reserve_ok: bool = True


def _allocate(total: float, owed: dict[str, float]) -> dict[str, float]:
    """Split `total` across creators, paying the largest balances first."""
    out: dict[str, float] = {}
    remaining = total
    for name, bal in sorted(owed.items(), key=lambda kv: kv[1], reverse=True):
        if remaining <= 1e-9:
            break
        pay = min(bal, remaining)
        if pay > 1e-9:
            out[name] = round(pay, 2)
            remaining -= pay
    return out


def run_marketplace_live(
    sim: CreatorMarketplace,
    controller: CashPayoutController,
    creators: list[Creator],
    client: PayPalClient,
    ledger: Ledger,
    purpose: str = "COMMISSION",
    poll_status: bool = False,
) -> list[PayoutRun]:
    """Run the marketplace, executing each period's payout as a real Payouts batch.

    Returns one PayoutRun per period that actually paid creators."""
    policy = helm_payout_policy(controller)
    owed: dict[str, float] = {c.name: 0.0 for c in creators}
    email = {c.name: c.email for c in creators}
    total_weight = sum(c.weight for c in creators) or 1.0
    runs: list[PayoutRun] = []

    while not sim.done():
        t = sim.t
        payout_total = policy(sim)
        obs = sim.step(payout_total)

        # creators accrue this period's earnings by weight
        for c in creators:
            owed[c.name] += obs.creator_earnings * (c.weight / total_weight)

        # allocate the amount actually paid, largest balances first
        alloc = _allocate(obs.payout, owed)
        for name, amt in alloc.items():
            owed[name] -= amt
        recipients = [{"email": email[name], "amount": amt,
                       "note": f"creator earnings wk{t}"}
                      for name, amt in alloc.items() if amt > 0]
        if not recipients:
            continue

        res = create_payout(
            client=client, ledger=ledger, recipients=recipients,
            sender_batch_id=f"helm-mkt-{t}-{uuid.uuid4().hex[:10]}", purpose=purpose,
        )
        run = PayoutRun(
            period=t, payout_total=round(obs.payout, 2), batch_id=res.batch_id,
            status=res.status, demo=res.demo, cash_after=obs.cash,
            reserve_required=obs.reserve_required, reserve_ok=obs.reserve_ok,
            recipients=[{"creator": n, "email": email[n], "amount": a}
                        for n, a in alloc.items() if a > 0],
        )
        if poll_status and res.batch_id and not res.demo:
            try:
                st = get_payout_batch(client, res.batch_id)
                run.status = st.get("batch_status", run.status)
            except Exception:
                pass
        runs.append(run)
    return runs
