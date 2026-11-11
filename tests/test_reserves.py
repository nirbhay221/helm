"""The zero-knowledge solvency proof verifies when solvent, fails when tampered,
cannot be produced when insolvent, and reveals no amount (commitments are random)."""
from __future__ import annotations

import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.reserves import prove_solvency, verify_solvency  # noqa: E402


def test_solvent_fund_proves_and_verifies():
    bundle = prove_solvency([12000.0, 3000.0, 500.0], liabilities=9000.0, bits=32)
    out = verify_solvency(bundle)
    assert out["solvent"] is True
    assert out["identity_ok"] and out["bits_ok"]


def test_tampering_breaks_the_proof():
    bundle = prove_solvency([10000.0], liabilities=4000.0, bits=32)
    bad = copy.deepcopy(bundle)
    bad["B"][0], bad["B"][1] = bad["B"][1], bad["B"][0]     # permute two bit commitments
    assert verify_solvency(bad)["solvent"] is False


def test_insolvent_fund_cannot_prove():
    with pytest.raises(ValueError):
        prove_solvency([1000.0], liabilities=5000.0, bits=32)


def test_generator_H_is_on_curve_and_not_G():
    # H must be a real curve point, independent of G, with unknown discrete log.
    from py_ecc.optimized_bn128 import G1, eq, is_on_curve
    from py_ecc.optimized_bn128 import b as CURVE_B
    from marketplace.reserves import HGEN
    assert is_on_curve(HGEN, CURVE_B)
    assert not eq(HGEN, G1)                       # not the base point itself


def test_bit_proof_rejects_a_non_bit_commitment():
    # a commitment to 2 must not pass a bit (0/1) proof: this is the soundness of the
    # range proof's building block. The honest prover's proof for it must fail to verify.
    from marketplace.reserves import _commit, _prove_bit, _rand, _verify_bit
    s = _rand()
    B2 = _commit(2, s)                            # commits to value 2, not a bit
    pr0 = _prove_bit(0, s, B2)                    # claim it is 0
    pr1 = _prove_bit(1, s, B2)                    # claim it is 1
    assert _verify_bit(B2, pr0) is False
    assert _verify_bit(B2, pr1) is False
    # and a genuine bit still verifies
    B1 = _commit(1, s)
    assert _verify_bit(B1, _prove_bit(1, s, B1)) is True


def test_proof_is_hiding_commitments_are_randomized():
    # two proofs of the identical balances must differ (fresh blinding each time),
    # so the proof leaks nothing about the amounts.
    b1 = prove_solvency([5000.0], liabilities=1000.0, bits=24)
    b2 = prove_solvency([5000.0], liabilities=1000.0, bits=24)
    assert b1["C_L"] != b2["C_L"]
    assert verify_solvency(b1)["solvent"] and verify_solvency(b2)["solvent"]


def test_a_prover_cannot_prove_against_smaller_liabilities_than_published():
    """Soundness: the liability commitment must open to the PUBLISHED liabilities. A fund owing
    9000 that proves solvency against 0 (or any smaller figure) is rejected."""
    honest = prove_solvency([12000.0], liabilities=9000.0, bits=24)
    assert verify_solvency(honest, liabilities=9000.0)["solvent"] is True
    understated = prove_solvency([5000.0], liabilities=0.0, bits=24)      # really owes 9000
    out = verify_solvency(understated, liabilities=9000.0)
    assert out["solvent"] is False and out["liabilities_bound"] is False
    forged = dict(honest, liabilities_cents=0)                         # lie about the opening
    assert verify_solvency(forged)["solvent"] is False
    stripped = {k: v for k, v in honest.items() if k not in ("liabilities_cents", "r_L")}
    assert verify_solvency(stripped)["solvent"] is False                # no opening, no proof
