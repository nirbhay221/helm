"""The model panel: consensus, and the humility to not bet on a vague signal.

Several models read the same signal. We act on their consensus (per-period
median) scaled by how much they agree. The payoff is not a clear signal, where
one model would also be right; it is a VAGUE signal, where a single confident
model would invent a demand change and the controller would over-order on noise.
A panel that cannot agree shrinks its bet toward zero on its own.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:
    pass

from agent import LLMClient, SignalDesk  # noqa: E402

PANEL = [
    "qwen/qwen-2.5-72b-instruct",
    "deepseek/deepseek-chat",
    "mistralai/mistral-large",
    "meta-llama/llama-3.3-70b-instruct",
]

CLEAR = ("Marketing booked a major promotion for week 24; in past promos this "
         "product sold roughly triple its normal weekly volume that week.")
VAGUE = ("There's been some buzz about this product on social media lately, "
         "though it's hard to say whether it will move sales at all.")
NOISY_MEMBER = "meta-llama/llama-3.1-8b-instruct"  # a weak model that mis-reads


def _show(desk: SignalDesk, text: str) -> None:
    adj = desk.interpret(text, current_period=22, baseline_demand=17.0, horizon=8)
    for m, vote in adj.model_votes.items():
        print(f"    {m:<34} {vote['deltas']}")
    print(f"  disagreement={adj.disagreement}  confidence={adj.confidence}")
    print(f"  consensus action (scaled by confidence): "
          f"{ {k: round(v,1) for k,v in adj.period_deltas.items()} or 'no bet'}")
    print()


def main() -> None:
    desk = SignalDesk(LLMClient(), models=PANEL)
    print(f"panel: {', '.join(PANEL)}\n")

    print(f"[CLEAR] signal: {CLEAR}")
    _show(desk, CLEAR)

    print(f"[VAGUE] signal: {VAGUE}")
    _show(desk, VAGUE)

    print(f"[CLEAR, but with a weak model ({NOISY_MEMBER}) on the panel]")
    _show(SignalDesk(LLMClient(), models=PANEL + [NOISY_MEMBER]), CLEAR)

    print("Read-out: on the clear signal the panel agrees and acts. On the vague "
          "signal every model declines to invent a number, so the panel makes no "
          "bet. And when a weak model emits noise, the median outvotes it and the "
          "extra disagreement trims confidence, so one bad model cannot drag the "
          "controller into a bad order. That is the failure the research warns "
          "about, handled by consensus rather than trust in any single model.")


if __name__ == "__main__":
    main()
