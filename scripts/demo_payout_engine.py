"""The paying arm end to end: Mete -> Bulwark -> Clearwright -> Tollgate -> Keystone."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arms.payout_engine import Contribution, Party, run_payout_engine  # noqa: E402
from paypal import Ledger, PayPalClient  # noqa: E402


def main() -> None:
    client, ledger = PayPalClient(), Ledger()
    pot = 1000.0

    # Mete: three affiliates whose conversions overlap
    contributions = [
        Contribution("A", {"c1", "c2", "c3", "c4"}),
        Contribution("B", {"c3", "c4", "c5"}),
        Contribution("C", {"c5", "c6"}),
    ]
    # Bulwark: the same honest cast, plus a cheater who will try to game the split
    honest = [Party("A", 400), Party("B", 300), Party("C", 150)]
    cheater = Party("Z", 500, cluster="Z", honest=False)
    meta = {
        "A": {"email": "a@ex.com", "country": "US"},
        "B": {"email": "b@ex.com", "country": "IN"},
        "C": {"email": "c@ex.com", "country": "BR"},
        "Z": {"email": "z@ex.com", "country": "US"},
    }

    res = run_payout_engine(
        pot, contributions, honest, cheater, meta, client, ledger,
        sender_batch_id="demo-payengine-001", purpose="COMMISSION",
        fail_items={"c@ex.com"},   # simulate one processor failure to show reconciliation
        approved=True,
    )

    print("1) Mete (fair split by contribution, Shapley):")
    for p, amt in res.mete.shares.items():
        print(f"   {p}: ${amt}  (shapley {res.mete.shapley[p]})")

    print("\n2) Bulwark (harden until cheating earns nothing):")
    print(f"   cheater take, naive split : ${res.bulwark.naive_cheater_take}")
    print(f"   cheater take, hardened     : ${res.bulwark.hardened_cheater_take}")
    print(f"   honest share for that party: ${res.bulwark.honest_cheater_share}")
    print(f"   hardening applied          : {res.bulwark.hardening_applied}")
    print(f"   cheat defeated             : {res.bulwark.defeated}")

    print("\n3) Clearwright (legality pre-flight):")
    print(f"   plan legal: {res.clearwright.ok}  violations: {len(res.clearwright.violations)}")

    print("\n4) Tollgate (cross-border withholding):")
    for L in res.tollgate.lines:
        print(f"   {L.recipient} [{L.country}]: gross ${L.gross} rate {L.rate} "
              f"withheld ${L.withheld} net ${L.net}")
    print(f"   totals: gross ${res.tollgate.total_gross} withheld "
          f"${res.tollgate.total_withheld} net ${res.tollgate.total_net}")

    print("\n5) Keystone (atomic execution + reconciliation):")
    k = res.keystone
    print(f"   status {k.status}  batch {k.batch_id}")
    print(f"   intended ${k.intended_total} = paid ${k.paid_total} + unpaid "
          f"${k.unpaid_total}  conserved={k.conserved}")
    print(f"   {k.message}")


if __name__ == "__main__":
    main()
