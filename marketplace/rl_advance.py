"""A reinforcement-learning advance-sizer, trained OFFLINE on simulated outcomes.

How much of a creator's eligible earnings to advance is a credit-limit decision: advance more and
earn more fee, but lose the advanced principal if the creator defaults (a reversed/charged-back
sale they cannot repay). This is exactly the problem the RL-in-finance literature studies for
dynamic credit limits and consumer-credit pricing -- not stock-picking, where LLM agents lose. The
tradeoff is clean: for a low-risk creator the fee beats the expected loss, so advance the most; for
a high-risk one the expected loss dominates, so advance little or nothing.

The agent sees only a NOISY risk estimate (as a real lender does, not the true default
probability) and learns, from outcomes alone, a policy that earns more net profit per creator than
any fixed advance fraction -- advancing aggressively to the safe and sparingly to the risky. It is
trained offline on simulated episodes (no real defaults exist to learn from), which the code is
honest about. Tabular Q-learning, numpy only, so it runs on the box. And it keeps Helm's thesis:
the agent PROPOSES an advance fraction; the deterministic advance engine still applies the
per-borrower concentration cap and the provision-fund coverage check, so a mis-trained policy can
never over-lend.
"""
from __future__ import annotations

import numpy as np

# advance fractions of the eligible amount the agent may propose
ACTIONS = (0.0, 0.25, 0.5, 0.75, 1.0)
N_RISK_BUCKETS = 8               # the observable (noisy) risk estimate, in 5-point buckets
_BUCKET_WIDTH = 0.05             # each risk bucket spans 5 percentage points of PD
SPREAD = 0.12                    # fee earned on the advanced principal (a short-term advance)
LGD = 0.9                        # loss given default (share of principal lost)
# break-even default probability is SPREAD / LGD ~= 0.133: advancing pays below it, loses above.


def _risk_bucket(est_pd: float) -> int:
    return min(N_RISK_BUCKETS - 1, max(0, int(est_pd / _BUCKET_WIDTH)))


def _draw_creator(rng):
    """A creator with a hidden true default probability and the NOISY estimate a lender sees.
    Most creators are low-risk with a heavier-risk tail (beta(2, 12), mean ~0.14)."""
    true_pd = float(np.clip(rng.beta(2.0, 12.0), 0.0, 0.95))
    est_pd = float(np.clip(true_pd + rng.normal(0.0, 0.04), 0.0, 1.0))  # observed with noise
    eligible = float(rng.uniform(200, 2000))
    return true_pd, est_pd, eligible


def _outcome(fraction: float, true_pd: float, eligible: float, rng) -> float:
    """Net profit from one advance: fee earned, minus the lost principal if it defaults."""
    advanced = fraction * eligible
    if advanced <= 0:
        return 0.0
    fee = SPREAD * advanced
    defaulted = rng.random() < true_pd
    loss = LGD * advanced if defaulted else 0.0
    return fee - loss


class AdvancePolicy:
    """Tabular Q-learning (a contextual bandit over the risk estimate) for the advance fraction."""

    def __init__(self):
        self.Q = np.zeros((N_RISK_BUCKETS, len(ACTIONS)), dtype=float)
        self.N = np.zeros((N_RISK_BUCKETS, len(ACTIONS)), dtype=float)
        self.trained = False

    def train(self, rounds: int = 120000, eps: float = 0.2, seed: int = 0) -> dict:
        """Contextual bandit with sample-average updates (step 1/count), which converge to the
        true expected per-dollar margin of each (risk bucket, advance fraction), so the greedy
        policy is the profit-maximizing one. eps-greedy keeps every cell sampled."""
        rng = np.random.default_rng(seed)
        for _ in range(rounds):
            true_pd, est_pd, _eligible = _draw_creator(rng)
            s = _risk_bucket(est_pd)
            a = int(rng.integers(len(ACTIONS))) if rng.random() < eps else int(np.argmax(self.Q[s]))
            # reward is the margin PER ELIGIBLE DOLLAR (fee minus any default loss); normalizing out
            # the advance size removes its variance so the risk economics are learned cleanly.
            defaulted = rng.random() < true_pd
            reward = ACTIONS[a] * (SPREAD - (LGD if defaulted else 0.0))
            self.N[s, a] += 1.0
            self.Q[s, a] += (reward - self.Q[s, a]) / self.N[s, a]            # running mean
        self.trained = True
        return {"rounds": rounds, "policy": self.policy_table()}

    def act(self, est_pd: float) -> float:
        return ACTIONS[int(np.argmax(self.Q[_risk_bucket(est_pd)]))]

    def policy_table(self) -> list:
        def lbl(b):
            lo = int(100 * b * _BUCKET_WIDTH)
            return f"{lo}%+" if b == N_RISK_BUCKETS - 1 else f"{lo}-{int(100 * (b + 1) * _BUCKET_WIDTH)}%"
        return [{"risk_estimate": lbl(b), "advance_fraction": ACTIONS[int(np.argmax(self.Q[b]))]}
                for b in range(N_RISK_BUCKETS)]


def evaluate(policy_fn, episodes: int = 8000, seed: int = 999) -> dict:
    """Average net profit per creator under a policy est_pd -> fraction, on held-out draws."""
    rng = np.random.default_rng(seed)
    total = 0.0
    for _ in range(episodes):
        true_pd, est_pd, eligible = _draw_creator(rng)
        total += _outcome(policy_fn(est_pd), true_pd, eligible, rng)
    return {"avg_net_profit": round(total / episodes, 2)}


_CACHE: dict = {}


def cached_compare(rounds: int = 120000) -> dict:
    """Train-and-compare once per process, then serve the cached result (the policy is
    deterministic for a fixed seed, so caching changes nothing but latency)."""
    if "result" not in _CACHE:
        _CACHE["result"] = compare(rounds)
    return _CACHE["result"]


def compare(rounds: int = 120000) -> dict:
    """Train the RL advance-sizer and compare its net profit, on held-out creators, to fixed
    policies and to a risk-blind lender. The learned policy should earn the most by lending
    aggressively to safe creators and sparingly to risky ones."""
    pol = AdvancePolicy()
    train = pol.train(rounds=rounds)
    # fixed baselines use the SAME held-out stream (same seed) for a fair comparison
    learned = evaluate(lambda est: pol.act(est))
    always_max = evaluate(lambda est: 1.0)
    conservative = evaluate(lambda est: 0.25)
    # a simple rule-of-thumb lender: advance iff estimated PD is low
    rule = evaluate(lambda est: 0.75 if est < 0.2 else (0.25 if est < 0.4 else 0.0))
    return {"trained_rounds": rounds, "policy": train["policy"],
            "learned": learned, "always_max_1.0": always_max,
            "conservative_0.25": conservative, "rule_of_thumb": rule,
            "note": ("RL proposes the advance fraction; the advance engine still applies the "
                     "concentration cap and fund-coverage check. Trained offline on simulated "
                     "defaults, no real money.")}
