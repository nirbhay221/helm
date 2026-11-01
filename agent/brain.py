"""Helm's agent loop: a language model that drives the deterministic tools.

Given a plain-language instruction for one operating cycle (for example "demand
spiked, restock and keep cash above the floor, then pay this month's affiliate
commissions"), the agent runs a tool-calling loop: it senses, plans with the
optimizer, sources suppliers, executes the purchase, and pays partners through
the AUP-gated PayPal tool, then writes a short journal narration citing the real
numbers the tools returned.

If no model key is configured, `run` falls back to a scripted policy that calls
the same tools in a sensible fixed order, so the whole system still runs and is
demonstrable with no key. When a key is present, the model genuinely decides.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .llm import LLMClient
from .tools import HelmTools, parse_arguments

SYSTEM_PROMPT = (
    "You are Helm, an autonomous operations controller for a single-product "
    "business that runs on PayPal. You manage one operating cycle at a time.\n\n"
    "Work in this order using the tools:\n"
    "1. observe the current state.\n"
    "2. plan_replenishment to get the optimizer's recommended order quantity.\n"
    "3. source_suppliers for that quantity to see the cheapest supplier split.\n"
    "4. execute_purchase to place the order and advance the period.\n"
    "5. if (and only if) the instruction asks you to pay partners/affiliates "
    "commissions, rebates, rewards or incentives, call pay_partners.\n\n"
    "You are not the decision authority for quantities. The controller's "
    "recommended order quantity is authoritative; pass it to execute_purchase "
    "as-is. If you send a different number it will be overruled and the override "
    "recorded. Every payout is checked against policy and cash before it moves.\n\n"
    "Rules: never invent quantities, costs, or balances; use the numbers the "
    "tools return. Never attempt payroll or supplier-goods payouts. When the "
    "cycle is complete, reply with a 2 to 3 sentence journal entry stating what "
    "you did and the key numbers (order quantity, cost, resulting inventory and "
    "cash, and any payout). Do not call more tools once you write that entry."
)


@dataclass
class ToolCallRecord:
    name: str
    arguments: dict
    result: dict


@dataclass
class AgentRun:
    instruction: str
    driver: str                                  # "llm" or "fallback"
    model: str | None
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    narration: str = ""                          # model prose: readable, NOT authoritative
    steps: int = 0

    @property
    def facts(self) -> dict:
        """The authoritative journal, assembled from tool RESULTS (not model
        prose). This is what the control journal and the UI should show: the
        model can misstate a number in free text, but these are the numbers the
        deterministic tools actually produced and executed."""
        f: dict = {}
        for tc in self.tool_calls:
            r = tc.result
            if tc.name == "execute_purchase" and "inventory" in r:
                f["period_closed"] = r.get("period_closed")
                f["proposed_qty"] = r.get("proposed_qty")
                f["ordered_qty"] = r.get("ordered_qty")
                if r.get("verifier_overrides"):
                    f.setdefault("verifier_overrides", []).extend(r["verifier_overrides"])
                f["order_cost"] = r.get("order_cost")
                f["supplier_split"] = r.get("supplier_split", [])
                f["realized_demand"] = r.get("realized_demand")
                f["sales"] = r.get("sales")
                f["inventory_after"] = r.get("inventory")
                f["cash_after"] = r.get("cash")
                f["deviation_from_target"] = r.get("deviation_from_target")
            elif tc.name == "source_suppliers" and r.get("savings_vs_naive") is not None:
                f["savings_vs_naive"] = r.get("savings_vs_naive")
            elif tc.name == "pay_partners":
                f.setdefault("payouts", []).append({
                    "status": r.get("status"), "batch_id": r.get("batch_id"),
                    "amount": r.get("total_amount"), "purpose": r.get("purpose"),
                })
                if r.get("verifier_overrides"):
                    f.setdefault("verifier_overrides", []).extend(r["verifier_overrides"])
        return f


class HelmAgent:
    def __init__(self, tools: HelmTools, llm: LLMClient | None = None) -> None:
        self.tools = tools
        self.llm = llm or LLMClient()

    def run(self, instruction: str, max_steps: int = 8) -> AgentRun:
        if self.llm.available:
            return self._run_llm(instruction, max_steps)
        return self._run_fallback(instruction)

    # --- model-driven -------------------------------------------------------
    def _run_llm(self, instruction: str, max_steps: int) -> AgentRun:
        run = AgentRun(instruction=instruction, driver="llm", model=self.llm.model)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ]
        for _ in range(max_steps):
            run.steps += 1
            msg = self.llm.chat(messages, tools=self.tools.schemas)
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                run.narration = (msg.get("content") or "").strip()
                break
            # record the assistant turn verbatim so the thread stays valid
            messages.append({
                "role": "assistant",
                "content": msg.get("content") or "",
                "tool_calls": tool_calls,
            })
            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                args = parse_arguments(fn.get("arguments"))
                result = self.tools.call(name, args)
                run.tool_calls.append(ToolCallRecord(name=name, arguments=args, result=result))
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", name),
                    "name": name,
                    "content": _json(result),
                })
        if not run.narration:
            run.narration = "(cycle ran; model did not return a closing narration)"
        return run

    # --- scripted fallback (no key) ----------------------------------------
    def _run_fallback(self, instruction: str) -> AgentRun:
        run = AgentRun(instruction=instruction, driver="fallback", model=None)

        def do(name, **args):
            res = self.tools.call(name, args)
            run.tool_calls.append(ToolCallRecord(name=name, arguments=args, result=res))
            run.steps += 1
            return res

        obs = do("observe")
        plan = do("plan_replenishment")
        target = float(plan.get("recommended_order_qty", 0.0))
        src = do("source_suppliers", target_qty=target)
        exe = do("execute_purchase", order_qty=target)

        payout_line = ""
        low = instruction.lower()
        if any(w in low for w in ("commission", "affiliate", "partner", "reward", "rebate", "incentive")):
            pay = do(
                "pay_partners",
                sender_batch_id=f"cycle-{obs['period']}-partners",
                purpose="COMMISSION",
                recipients=[{"email": "affiliate@example.com", "amount": 25.0,
                             "note": "cycle commission"}],
            )
            payout_line = (f" Paid partners: {pay['status']} "
                           f"(${pay['total_amount']}, batch {pay['batch_id']}).")

        run.narration = (
            f"Period {obs['period']}: ordered {exe.get('ordered_qty', 0)} units "
            f"for ${exe.get('order_cost', 0)} across "
            f"{len(exe.get('supplier_split', []))} supplier(s) "
            f"(saved ${src.get('savings_vs_naive')} vs a single-supplier buy). "
            f"Inventory now {exe.get('inventory')} (target "
            f"{obs['target_inventory']}), cash {exe.get('cash')}." + payout_line
        )
        return run


def _json(obj) -> str:
    import json
    return json.dumps(obj, default=str)
