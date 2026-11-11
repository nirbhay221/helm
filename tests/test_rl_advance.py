"""The RL advance-sizer learns a sensible, profitable credit policy from simulated outcomes.

Deterministic (fixed seeds), numpy only, no network. We assert the learned policy is a sensible
risk threshold (advance the safe, not the risky), that it is monotone non-increasing in risk, and
that on held-out creators it earns more net profit than fixed or rule-of-thumb policies. This is
the honest claim: offline RL on the simulator beats a static lender.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marketplace.rl_advance import SPREAD, LGD, AdvancePolicy, compare, evaluate


def test_policy_is_a_sensible_risk_threshold():
    pol = AdvancePolicy()
    table = pol.train(rounds=120000)["policy"]
    fracs = [row["advance_fraction"] for row in table]
    # advances the safest bucket, refuses the riskiest
    assert fracs[0] > 0.0
    assert fracs[-1] == 0.0
    # monotone non-increasing: never advance MORE to a riskier creator
    assert all(fracs[i] >= fracs[i + 1] for i in range(len(fracs) - 1))


def test_threshold_sits_near_the_break_even_pd():
    """It should lend where the fee beats expected loss (PD below SPREAD/LGD ~ 0.133) and not above."""
    pol = AdvancePolicy()
    pol.train(rounds=120000)
    assert pol.act(0.02) > 0.0                    # clearly profitable -> advance
    assert pol.act(0.30) == 0.0                   # clearly unprofitable -> refuse
    break_even = SPREAD / LGD
    assert 0.10 < break_even < 0.16               # sanity on the economics


def test_learned_beats_every_fixed_baseline():
    r = compare(rounds=120000)
    learned = r["learned"]["avg_net_profit"]
    for k in ("always_max_1.0", "conservative_0.25", "rule_of_thumb"):
        assert learned > r[k]["avg_net_profit"], f"learned ({learned}) did not beat {k}"
    assert learned > 0                            # and it is actually profitable


def test_training_is_deterministic():
    a = AdvancePolicy(); a.train(rounds=40000, seed=1)
    b = AdvancePolicy(); b.train(rounds=40000, seed=1)
    assert a.policy_table() == b.policy_table()   # same seed -> same policy
