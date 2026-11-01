"""The payout engine end to end: Mete -> Bulwark -> Clearwright -> Tollgate ->
Keystone on one pot.

Mete fixes the fair split by contribution; Bulwark hardens an activity split so a
cheater gains nothing; Clearwright proves every resulting money edge is legal;
Tollgate withholds cross-border tax; Keystone executes the net batch atomically
through the Payouts tool. The result object carries every stage so the dashboard
can show the whole chain, including Bulwark's before/after money shot.
"""
from __future__ import annotations

from dataclasses import dataclass

from paypal import Ledger, PayPalClient

from .bulwark import BulwarkResult, Party, harden_split
from .clearwright import ClearwrightResult, MoneyEdge, check_plan
from .keystone import KeystoneResult, execute_batch
from .mete import Contribution, MeteResult, shapley_split
from .tollgate import TollgateResult, withhold


@dataclass
class PayoutEngineResult:
    mete: MeteResult
    bulwark: BulwarkResult
    clearwright: ClearwrightResult
    tollgate: TollgateResult
    keystone: KeystoneResult


def run_payout_engine(
    pot: float,
    contributions: list[Contribution],
    honest_parties: list[Party],
    cheater: Party,
    meta: dict,                        # party name -> {"email":..., "country":...}
    client: PayPalClient,
    ledger: Ledger,
    sender_batch_id: str,
    purpose: str = "COMMISSION",
    fail_items: set | None = None,
    approved: bool = True,
) -> PayoutEngineResult:
    mete = shapley_split(pot, contributions)
    bulwark = harden_split(pot, honest_parties, cheater)

    shares = {n: a for n, a in bulwark.final_shares.items() if a > 0}
    edges = [MoneyEdge("operator", meta.get(n, {}).get("email", n), amt, purpose, "payouts")
             for n, amt in shares.items()]
    clearwright = check_plan(edges)

    payouts_meta = [
        {"recipient": meta.get(n, {}).get("email", n),
         "email": meta.get(n, {}).get("email", n),
         "amount": amt, "country": meta.get(n, {}).get("country", "US")}
        for n, amt in shares.items()
    ]
    tollgate = withhold(payouts_meta)

    recipients = [{"email": L.recipient, "amount": L.net, "note": purpose}
                  for L in tollgate.lines if L.net > 0]
    keystone = execute_batch(client, ledger, recipients, sender_batch_id, purpose,
                             fail_items=fail_items, approved=approved)

    return PayoutEngineResult(mete, bulwark, clearwright, tollgate, keystone)
