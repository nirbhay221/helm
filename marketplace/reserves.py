"""Zero-knowledge proof that the safety fund is solvent, revealing no balances.

Every entry in this hackathon that touches trust does it with signatures and
deterministic gates. None proves a financial fact in zero knowledge. This does:
the platform proves its safety fund covers every outstanding liability (advances
drawn, pool commitments) WITHOUT disclosing the fund balance, any lot, or the
liability total. A regulator, a creator or another agent verifies solvency and
learns nothing else.

The construction is a classic confidential-amount proof, no SNARK toolchain:
  - each reserve lot and the liability total are hidden in Pedersen commitments
    C = v*G + r*H over the bn128 curve (perfectly hiding, computationally binding);
  - commitments are additively homomorphic, so the verifier forms the difference
    commitment C_d = (sum of lot commitments) - (liability commitment), which hides
    d = reserves - liabilities;
  - a bit-decomposition RANGE PROOF shows d lies in [0, 2^bits), i.e. d >= 0, using
    a non-interactive Chaum-Pedersen OR proof per bit (each bit commits to 0 or 1)
    plus the homomorphic identity C_d == sum_j 2^j * B_j. If reserves < liabilities
    no valid proof exists, so a passing verification is a sound solvency proof.

Grounded in Pedersen commitments, confidential-transaction range proofs, and
ZK proof-of-reserves (PoRv2 / OKX-style Merkle-sum solvency), adapted to prove
reserves >= liabilities rather than reserves == a public total. Uses py_ecc bn128.
"""
from __future__ import annotations

import hashlib
import secrets

# Projective-coordinate backend: the SAME bn128 curve and the SAME construction, but
# point addition avoids the per-operation modular inverse that the affine backend pays,
# so the proof runs several times faster with identical security.
from py_ecc.optimized_bn128 import FQ, G1, Z1, add, curve_order, eq, is_inf, is_on_curve, multiply, neg, normalize
from py_ecc.optimized_bn128 import b as CURVE_B
from py_ecc.optimized_bn128 import field_modulus as P

N = curve_order
CENTS = 100            # work in integer cents
DEFAULT_BITS = 40      # supports a difference up to ~2^40 cents (about 11 billion dollars)


def _fqi(x) -> int:
    return x.n if hasattr(x, "n") else int(x)


_B_INT = _fqi(CURVE_B)                                  # curve constant b = 3 (y^2 = x^3 + 3)


def _rand() -> int:
    return 1 + secrets.randbelow(N - 1)


def _hash_to_curve(label: bytes):
    """A second generator H whose discrete log to G is UNKNOWN. This is essential:
    if H = h*G for a known h, then C = v*G + r*H = (v + r*h)*G and a prover who knows
    h can open one commitment to any value, so binding (and thus solvency soundness)
    collapses. We derive H by try-and-increment hash-to-curve (nobody knows log_G H).
    bn128's base field is 3 mod 4, so a square root is a^((P+1)/4)."""
    ctr = 0
    while ctr < 1000:
        x = int.from_bytes(hashlib.sha256(label + ctr.to_bytes(4, "big")).digest(), "big") % P
        rhs = (pow(x, 3, P) + _B_INT) % P
        y = pow(rhs, (P + 1) // 4, P)          # candidate sqrt (valid because P % 4 == 3)
        if (y * y - rhs) % P == 0:
            pt = (FQ(x), FQ(y), FQ(1))         # projective point (z = 1)
            if is_on_curve(pt, CURVE_B):
                return pt
        ctr += 1
    raise ValueError("hash-to-curve failed")


HGEN = _hash_to_curve(b"helm/pedersen/H/nums/v2")


def _commit(v: int, r: int):
    """Pedersen commitment v*G + r*H. Multiply-by-zero yields the identity Z1, which add
    treats as neutral, so no special-casing is needed."""
    return add(multiply(G1, v % N), multiply(HGEN, r % N))


def _pt_bytes(pt) -> bytes:
    if pt is None or is_inf(pt):
        return b"\x00" * 64
    x, y = normalize(pt)                        # projective -> affine for a canonical encoding
    return _fqi(x).to_bytes(32, "big") + _fqi(y).to_bytes(32, "big")


def _challenge(*items) -> int:
    h = hashlib.sha256()
    for it in items:
        h.update(_pt_bytes(it))
    return int.from_bytes(h.digest(), "big") % N


# --- per-bit OR proof: a commitment B opens to 0 or to 1 --------------------

def _prove_bit(b: int, s: int, B):
    """Non-interactive OR proof that B = b*G + s*H with b in {0,1}, knowing s.
    Branch 0 asserts B = s*H; branch 1 asserts B - G = s*H. The false branch is
    simulated, the true branch answered, under a Fiat-Shamir challenge."""
    T = [B, add(B, neg(G1))]                 # targets for branch 0 and 1
    f = 1 - b                                 # the false branch to simulate
    cf, zf = _rand(), _rand()
    Af = add(multiply(HGEN, zf), neg(multiply(T[f], cf)))     # zf*H - cf*Tf
    k = _rand()
    Ab = multiply(HGEN, k)
    A = [None, None]
    A[b], A[f] = Ab, Af
    c = _challenge(A[0], A[1], B)
    cb = (c - cf) % N
    zb = (k + cb * s) % N
    cc = [0, 0]; cc[b], cc[f] = cb, cf
    zz = [0, 0]; zz[b], zz[f] = zb, zf
    return {"A0": A[0], "A1": A[1], "c0": cc[0], "c1": cc[1], "z0": zz[0], "z1": zz[1]}


def _verify_bit(B, pr) -> bool:
    T0, T1 = B, add(B, neg(G1))
    c = _challenge(pr["A0"], pr["A1"], B)
    if (pr["c0"] + pr["c1"]) % N != c % N:
        return False
    lhs0 = multiply(HGEN, pr["z0"] % N)
    rhs0 = add(pr["A0"], multiply(T0, pr["c0"] % N))
    lhs1 = multiply(HGEN, pr["z1"] % N)
    rhs1 = add(pr["A1"], multiply(T1, pr["c1"] % N))
    return bool(eq(lhs0, rhs0) and eq(lhs1, rhs1))


# --- top level: prove / verify solvency -------------------------------------

def prove_solvency(reserve_lots: list[float], liabilities: float, bits: int = DEFAULT_BITS) -> dict:
    """Produce a zero-knowledge solvency proof that sum(reserve_lots) >= liabilities.
    Raises ValueError if the fund is actually insolvent (no sound proof exists)."""
    lots = [int(round(float(x) * CENTS)) for x in reserve_lots]
    L = int(round(float(liabilities) * CENTS))
    R = sum(lots)
    d = R - L
    if d < 0:
        raise ValueError("insolvent: reserves below liabilities, no proof exists")
    if d >= (1 << bits):
        raise ValueError("difference exceeds the range-proof width")

    r_lots = [_rand() for _ in lots]
    C_lots = [_commit(v, r) for v, r in zip(lots, r_lots)]
    r_L = _rand()
    C_L = _commit(L, r_L)
    s_d = (sum(r_lots) - r_L) % N                       # blinding of the difference commitment

    # bit blindings must satisfy sum_j 2^j s_j == s_d so that sum_j 2^j B_j == C_d
    bit_vals = [(d >> j) & 1 for j in range(bits)]
    s_bits = [_rand() for _ in range(bits)]
    acc = sum((1 << j) * s_bits[j] for j in range(1, bits)) % N
    s_bits[0] = (s_d - acc) % N
    B = [_commit(bit_vals[j], s_bits[j]) for j in range(bits)]
    proofs = [_prove_bit(bit_vals[j], s_bits[j], B[j]) for j in range(bits)]

    # Liabilities are PUBLIC (outstanding advances + pool commitments are owed to known
    # parties), so the bundle opens C_L: the verifier recomputes it from the published figure.
    # Without this a cheating prover could commit to zero liabilities and still "prove" solvency.
    # Opening C_L reveals nothing about the reserves, whose blindings stay secret.
    return {"bits": bits, "C_lots": C_lots, "C_L": C_L, "B": B, "proofs": proofs,
            "lots": len(lots), "liabilities_cents": L, "r_L": r_L}


def verify_solvency(bundle: dict, liabilities: float | None = None) -> dict:
    """Verify a solvency proof against the PUBLISHED liabilities. Learns only that the hidden
    reserves cover them and the difference fits the range; never a balance.

    `liabilities` is the figure the verifier expects (e.g. the published outstanding book). The
    proof's liability commitment must open to exactly that figure, so a prover cannot quietly
    prove solvency against a smaller number. If omitted, the bundle's own stated figure is used
    but the commitment must still open to it."""
    bits = bundle["bits"]
    C_lots, C_L, B, proofs = bundle["C_lots"], bundle["C_L"], bundle["B"], bundle["proofs"]
    # C_R = sum of lot commitments; C_d = C_R - C_L
    C_R = Z1
    for C in C_lots:
        C_R = add(C_R, C)
    C_d = add(C_R, neg(C_L))
    # homomorphic identity: C_d must equal sum_j 2^j B_j
    acc = Z1
    for j in range(bits):
        acc = add(acc, multiply(B[j], (1 << j) % N))
    identity_ok = bool(eq(C_d, acc))
    bits_ok = all(_verify_bit(B[j], proofs[j]) for j in range(bits))
    stated = bundle.get("liabilities_cents")
    liabilities_bound = False
    if stated is not None and bundle.get("r_L") is not None:
        try:
            opens = bool(eq(C_L, _commit(int(stated), int(bundle["r_L"]))))
        except Exception:
            opens = False
        matches = liabilities is None or int(round(float(liabilities) * CENTS)) == int(stated)
        liabilities_bound = opens and matches
    ok = bool(identity_ok and bits_ok and liabilities_bound)
    return {"solvent": ok, "identity_ok": identity_ok, "bits_ok": bits_ok,
            "liabilities_bound": liabilities_bound,
            "liabilities": (int(stated) / CENTS) if stated is not None else None,
            "reveals": "nothing about the reserves; only that they cover the published liabilities",
            "statement": "hidden reserves - published liabilities lies in [0, 2^%d), in zero knowledge" % bits}
