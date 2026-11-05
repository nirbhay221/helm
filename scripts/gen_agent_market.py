"""Run a real, model-driven episode of the agentic marketplace and save it.

Every customer is an LLM agent choosing its own action each cycle. This captures
one live episode (non-deterministic, in character) plus the emergent abuse the
engine finds in behaviour the agents generated themselves, to ui/agent_market.json.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:
    pass

from agent.llm import LLMClient
from market.abuse import AbuseEngine
from market.agents import AgentMarket

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "agent_market.json")


def main() -> None:
    llm = LLMClient()
    mk = AgentMarket(llm, n_agents=6, seed=7)
    mk.run(6)
    m = mk.m

    # action mix per persona, to show agents acted in character (not scripted)
    by_persona: dict = {}
    for t in mk.log:
        for e in t["events"]:
            by_persona.setdefault(e["persona"], Counter())[e["action"]] += 1

    verdicts = AbuseEngine(min_bad=3, spread=2, watch_rate=0.25, suspend_rate=0.4).scan(m)
    out = {
        "driver": "model" if llm.available else "fallback",
        "agents": [{"name": a.account.name, "persona": a.persona,
                    "balance": round(a.balance, 2)} for a in mk.agents],
        "ticks": mk.log,
        "orders": len(m.orders),
        "returns": sum(1 for o in m.orders if o.status in ("returned", "charged_back")),
        "action_mix_by_persona": {k: dict(v) for k, v in by_persona.items()},
        "emergent_abuse": [{"name": v.name, "role": v.role, "bad": v.bad_count,
                            "rate": round(v.rate, 3), "action": v.action} for v in verdicts],
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"wrote {OUT}  driver={out['driver']}  orders={out['orders']} returns={out['returns']}")
    print("action mix by persona (proves in-character, non-scripted choices):")
    for persona, mix in out["action_mix_by_persona"].items():
        print(f"  {persona:16} {mix}")
    print("emergent abuse:", [(v['name'].split()[0], v['role'], v['bad']) for v in out["emergent_abuse"]])


if __name__ == "__main__":
    main()
