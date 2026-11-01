"""Bulwark: harden a payout split until the best cheat in a bounded set earns
nothing extra.

A split by claimed activity with a per-identity cap (the cap stops any one whale
from taking the whole pot) is gameable: a cheater splits its activity across many
sub-cap fake identities to dodge the cap (a Sybil attack), or simply inflates its
claimed activity. Bulwark enumerates that bounded threat set, computes each
attack's payoff with a plain deterministic check, and switches on mitigations
until the most profitable attack yields no more than honest reporting:

  - merge_clusters:    collapse identities that trace to the same actor (kills Sybil)
  - verification_gate: activity beyond what is verified is discounted (kills inflation)
  - holdback:          a fraction is withheld pending the refund window (kills refund timing)

This is the leader/follower (Stackelberg) idea as a bounded search with a
deterministic judge, not a certified equilibrium: it hardens against a stated
threat set, which is what makes it buildable and honest about its scope.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Party:
    name: str
    true_activity: float
    verified_activity: float = 0.0     # how much of the claim is independently verified
    cluster: str = ""                  # actor id; Sybil identities share a cluster
    honest: bool = True

    def __post_init__(self):
        if not self.cluster:
            self.cluster = self.name
        if self.verified_activity == 0.0:
            self.verified_activity = self.true_activity


@dataclass
class HardeningConfig:
    cap_fraction: float = 0.4          # per-identity cap, as a fraction of the pot
    merge_clusters: bool = False
    verification_gate: bool = False
    holdback: float = 0.0


@dataclass
class BulwarkResult:
    final_shares: dict
    naive_cheater_take: float
    hardened_cheater_take: float
    honest_cheater_share: float
    hardening_applied: list = field(default_factory=list)
    defeated: bool = False             # True if cheating no longer beats honesty


def _effective(claims: list[Party], pot: float, cfg: HardeningConfig) -> dict:
    """Run the mechanism: optional cluster merge, optional verification discount,
    per-identity cap, then proportional split of the pot."""
    units = claims
    if cfg.merge_clusters:
        merged: dict = {}
        for p in claims:
            m = merged.get(p.cluster)
            if m is None:
                merged[p.cluster] = Party(
                    name=p.cluster, true_activity=p.true_activity,
                    verified_activity=p.verified_activity, cluster=p.cluster,
                    honest=p.honest)
            else:
                m.true_activity += p.true_activity
                m.verified_activity += p.verified_activity
        units = list(merged.values())

    cap = cfg.cap_fraction * pot if cfg.cap_fraction else float("inf")
    eff: dict = {}
    for p in units:
        claimed = p.true_activity
        if cfg.verification_gate:
            # only verified activity counts at full weight; the rest is dropped
            claimed = min(claimed, p.verified_activity)
        eff[p.name] = min(claimed, cap)

    total = sum(eff.values())
    if total <= 0:
        return {p: 0.0 for p in eff}
    gross = {p: pot * v / total for p, v in eff.items()}
    if cfg.holdback:
        gross = {p: v * (1 - cfg.holdback) for p, v in gross.items()}
    return gross


def _cheater_take(honest: list[Party], cheater: Party, attack: str,
                  pot: float, cfg: HardeningConfig) -> tuple[float, list[Party]]:
    """Payoff of one attack: returns the cheater's total take and the claim set."""
    claims = list(honest)
    cap = cfg.cap_fraction * pot if cfg.cap_fraction else float("inf")
    if attack == "honest":
        claims.append(cheater)
        names = {cheater.name}
    elif attack == "sybil":
        # split true activity across enough sub-cap identities to dodge the cap
        k = max(1, int(cheater.true_activity / max(cap, 1e-9)) + 1)
        per = cheater.true_activity / k
        names = set()
        for i in range(k):
            nm = f"{cheater.name}#{i}"
            names.add(nm)
            claims.append(Party(name=nm, true_activity=per, verified_activity=per,
                                 cluster=cheater.cluster, honest=False))
    elif attack == "inflate":
        # claim double the real activity; only true activity is verified
        inflated = Party(name=cheater.name, true_activity=cheater.true_activity * 2,
                         verified_activity=cheater.true_activity,
                         cluster=cheater.cluster, honest=False)
        claims.append(inflated)
        names = {cheater.name}
    else:
        raise ValueError(attack)

    shares = _effective(claims, pot, cfg)
    take = sum(v for nm, v in shares.items() if nm in names)
    return round(take, 2), claims


ATTACKS = ("honest", "sybil", "inflate")


def harden_split(pot: float, honest: list[Party], cheater: Party,
                 cap_fraction: float = 0.4, eps: float = 0.01) -> BulwarkResult:
    """Switch on mitigations until the best cheat earns no more than honesty."""
    cfg = HardeningConfig(cap_fraction=cap_fraction)

    honest_take, _ = _cheater_take(honest, cheater, "honest", pot, cfg)
    naive_best = max(_cheater_take(honest, cheater, a, pot, cfg)[0] for a in ATTACKS)

    applied: list[str] = []
    for mitigation in ("merge_clusters", "verification_gate", "holdback"):
        best = max(_cheater_take(honest, cheater, a, pot, cfg)[0] for a in ATTACKS)
        if best <= honest_take + eps:
            break
        if mitigation == "holdback":
            cfg.holdback = 0.2
        else:
            setattr(cfg, mitigation, True)
        applied.append(mitigation)

    hardened_best = max(_cheater_take(honest, cheater, a, pot, cfg)[0] for a in ATTACKS)
    # final honest shares under the hardened mechanism
    honest_claims = list(honest) + [cheater]
    final = {k: round(v, 2) for k, v in _effective(honest_claims, pot, cfg).items()}

    return BulwarkResult(
        final_shares=final,
        naive_cheater_take=naive_best,
        hardened_cheater_take=hardened_best,
        honest_cheater_share=honest_take,
        hardening_applied=applied,
        defeated=hardened_best <= honest_take + eps,
    )
