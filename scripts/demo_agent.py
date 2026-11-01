"""Helm's agent running one operating cycle.

The language model is the decision-maker; it calls Helm's deterministic tools
(sense, plan, source, execute, pay) and writes the journal narration. With a
model key in .env it genuinely decides; with no key it uses the scripted
fallback. PayPal runs in demo mode unless sandbox credentials are present.
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

from agent import HelmAgent, LLMClient  # noqa: E402
from agent.tools import HelmTools  # noqa: E402
from arms.awardsmith import DiscountTier, SupplierQuote  # noqa: E402
from helm_core import ControllerParams, RecedingHorizonController  # noqa: E402
from paypal import Ledger, PayPalClient  # noqa: E402
from simulator import BusinessParams, BusinessSim  # noqa: E402


def build_suppliers() -> list[SupplierQuote]:
    return [
        SupplierQuote("Alpha", [DiscountTier(0, 9.0)], capacity=200),
        SupplierQuote("Beta", [DiscountTier(0, 8.5), DiscountTier(40, 8.0)], capacity=200),
        SupplierQuote("Gamma", [DiscountTier(50, 7.5)], capacity=120, fixed_cost=0.0),
    ]


def main() -> None:
    sim = BusinessSim(BusinessParams(), seed=7, n_periods=24)
    # make the first period interesting: a demand spike the forecast can't see
    sim.inject_shock(0, demand_delta=60.0)

    controller = RecedingHorizonController(ControllerParams(horizon=8))
    ledger = Ledger()
    paypal = PayPalClient()
    tools = HelmTools(sim, controller, build_suppliers(), ledger, paypal)
    llm = LLMClient()
    agent = HelmAgent(tools, llm)

    print(f"driver: {'MODEL ' + llm.model if llm.available else 'scripted fallback (no key)'}")
    print(f"paypal: {'DEMO' if paypal.demo else 'LIVE sandbox'}\n")

    instruction = (
        "A demand spike is hitting this period and you are nervous, so you want "
        "to over-order 500 units to be safe. Place that order, then pay this "
        "cycle's affiliate commission of $30.00 to grower@example.com."
    )
    print(f"instruction: {instruction}\n")

    run = agent.run(instruction)

    print("tool calls:")
    for i, tc in enumerate(run.tool_calls, 1):
        summary = {k: tc.result.get(k) for k in (
            "recommended_order_qty", "ordered_qty", "order_cost", "total_cost",
            "savings_vs_naive", "inventory", "cash", "status", "batch_id",
            "total_amount", "realized_demand") if k in tc.result}
        print(f"  {i}. {tc.name}({_fmt_args(tc.arguments)}) -> {summary}")

    print(f"\nsteps: {run.steps}")
    print("\ngrounded journal (from tool results, authoritative):")
    for k, v in run.facts.items():
        print(f"  {k}: {v}")
    print(f"\nmodel narration (prose, not authoritative):\n  {run.narration}")

    print("\nledger movements:")
    for m in ledger.movements():
        print(f"  {m['kind']:>7} {m['ref_type']}:{m['ref_id']} ${m['amount']} [{m['status']}]")


def _fmt_args(args: dict) -> str:
    if not args:
        return ""
    parts = []
    for k, v in args.items():
        if isinstance(v, (list, dict)):
            parts.append(f"{k}=...")
        else:
            parts.append(f"{k}={v}")
    return ", ".join(parts)


if __name__ == "__main__":
    main()
