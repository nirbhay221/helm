"""The money-out operator: the LLM agent that steers the payout loop.

Each cycle the agent observes the platform's state, reads the signal, asks the
controller how much is safe to release, then decides which creators to pay and
which to hold based on their risk, and pays. The deterministic tools size the
money and hard-clamp the agent; the agent supplies the judgment. This is the
inversion: the model runs the loop and the solver, signal desk and PayPal are
its tools.

With a model key it genuinely decides; with no key a scripted fallback runs the
same four steps so the system works end to end. Either way the journal is built
from tool RESULTS (authoritative), with the model's prose kept separate.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .llm import LLMClient
from .operator_tools import TOOL_SCHEMAS, OperatorTools

SYSTEM_PROMPT = (
    "You are Helm, the autonomous money-out operator for a creator platform. Your "
    "job each cycle is to pay creators as fast as is SAFE. Steps: (1) observe, "
    "(2) interpret_signal, (3) size_safe_release with a risk_multiplier you choose "
    "(raise it above 1.0 when the signal warns of fraud or a chargeback wave), "
    "(4) pay_creators, releasing to creators you judge low-risk (long-tenured, "
    "steady, clean history) and HOLDING creators you judge risky (brand new, just "
    "went viral, flagged for fraud or disputes), with total within the safe "
    "release. Each creator shows owed (all unpaid), settled_owed (past its "
    "chargeback window, safe to pay) and recoup_due (debt from a reversed sale). "
    "Paying settled_owed is safest; paying above it is an early release you should "
    "do only for a creator you judge low-risk. Call pay_creators exactly once to "
    "close the cycle. You never compute the safe amount yourself; the tools "
    "enforce every limit. Be decisive."
)

_RISKY_WORDS = ("fraud", "new", "viral", "dispute", "chargeback", "suspicious", "spike")


@dataclass
class CycleRecord:
    period: int
    driver: str                       # "model" | "fallback"
    tool_calls: list = field(default_factory=list)
    facts: dict = field(default_factory=dict)
    narration: str = ""


class MoneyOutOperator:
    def __init__(self, tools: OperatorTools, llm: LLMClient | None = None,
                 signal_schedule: dict | None = None, max_steps: int = 8) -> None:
        self.tools = tools
        self.llm = llm or LLMClient()
        self.signals = signal_schedule or {}
        self.max_steps = max_steps

    def run(self, n_cycles: int) -> list[CycleRecord]:
        records: list[CycleRecord] = []
        for _ in range(n_cycles):
            if self.tools.sim.done():
                break
            t = self.tools.sim.t
            self.tools.current_signal = self.signals.get(t, "")
            rec = (self._run_llm_cycle(t) if self.llm.available else None) or self._run_fallback_cycle(t)
            records.append(rec)
        return records

    # --- model-driven cycle -------------------------------------------------
    def _run_llm_cycle(self, period: int) -> CycleRecord | None:
        rec = CycleRecord(period=period, driver="model")
        # Seed the real state and creator names so the model never invents them.
        obs = self.tools.observe()
        self._record_fact(rec, "observe", obs)
        rec.tool_calls.append("observe")
        user = (f"Cycle {period}. Current state (use these exact creator names):\n"
                f"{json.dumps(obs)}\n\nInterpret the signal, choose a risk posture, size the "
                f"safe release, then pay the creators you judge low-risk and hold the risky ones. "
                f"Call pay_creators exactly once.")
        messages = [{"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user}]
        paid = False
        try:
            for _ in range(self.max_steps):
                msg = self.llm.chat(messages, tools=TOOL_SCHEMAS, tool_choice="auto")
                calls = (msg or {}).get("tool_calls") or []
                if not calls:
                    rec.narration = (msg or {}).get("content") or ""
                    break
                messages.append({"role": "assistant", "content": msg.get("content"),
                                 "tool_calls": calls})
                for tc in calls:
                    name = tc.get("function", {}).get("name", "")
                    args = self._parse_args(tc.get("function", {}).get("arguments", "{}"))
                    result = self.tools.call(name, args)
                    rec.tool_calls.append(name)
                    self._record_fact(rec, name, result)
                    messages.append({"role": "tool", "tool_call_id": tc.get("id", name),
                                     "content": json.dumps(result)})
                    if name == "pay_creators":
                        paid = True
                if paid:
                    break
        except Exception:
            return None  # fall back to the scripted cycle for this period
        if not paid:
            # the model never closed the cycle; close it deterministically
            self._fallback_pay(rec)
        return rec

    # --- scripted fallback --------------------------------------------------
    def _run_fallback_cycle(self, period: int) -> CycleRecord:
        rec = CycleRecord(period=period, driver="fallback")
        self._record_fact(rec, "observe", self.tools.observe())
        sig = self.tools.interpret_signal()
        self._record_fact(rec, "interpret_signal", sig)
        mult = 1.4 if sig.get("suggests_caution") else 1.0
        self._record_fact(rec, "size_safe_release", self.tools.size_safe_release(mult))
        self._fallback_pay(rec)
        rec.narration = ("held risky creators, released the rest within the safe cap "
                         "(scripted fallback)")
        return rec

    def _fallback_pay(self, rec: CycleRecord) -> None:
        cap = self.tools._safe_release
        if cap is None:
            cap = self.tools.size_safe_release(1.0)["safe_release_total"]
        # release only SETTLED balances (past the chargeback window) to low-risk
        # creators, skipping any whose context looks risky. Holding until settled is
        # the safe default; the model may release earlier when it judges it safe.
        now = self.tools.sim.t
        payable = {c.name: self.tools.led.settled_unpaid(c.name, now) for c in self.tools.creators.values()}
        creators = sorted(self.tools.creators.values(), key=lambda c: payable[c.name], reverse=True)
        alloc, remaining = [], cap
        for c in creators:
            risky = any(w in (c.context or "").lower() for w in _RISKY_WORDS)
            avail = payable[c.name]
            if risky or remaining <= 1e-6 or avail <= 1e-6:
                continue
            pay = min(avail, remaining)
            alloc.append({"creator": c.name, "amount": round(pay, 2)})
            remaining -= pay
        result = self.tools.pay_creators(alloc)
        rec.tool_calls.append("pay_creators")
        self._record_fact(rec, "pay_creators", result)

    # --- helpers ------------------------------------------------------------
    @staticmethod
    def _parse_args(raw) -> dict:
        if isinstance(raw, dict):
            return raw
        try:
            return json.loads(raw or "{}")
        except Exception:
            return {}

    @staticmethod
    def _record_fact(rec: CycleRecord, name: str, result: dict) -> None:
        if name == "pay_creators":
            rec.facts["paid_total"] = result.get("paid_total")
            rec.facts["paid"] = result.get("paid")
            rec.facts["status"] = result.get("status")
            rec.facts["batch_id"] = result.get("batch_id")
            rec.facts["cash_after"] = result.get("cash_after")
            rec.facts["reserve_ok_after"] = result.get("reserve_ok_after")
            if result.get("guardrail_overrides"):
                rec.facts["guardrail_overrides"] = result["guardrail_overrides"]
        elif name == "size_safe_release":
            rec.facts["safe_release_total"] = result.get("safe_release_total")
            rec.facts["risk_multiplier"] = result.get("risk_multiplier")
            rec.facts["forecast_gmv_next"] = result.get("forecast_gmv_next")
            rec.facts["forecast_sigma_next"] = result.get("forecast_sigma_next")
        elif name == "interpret_signal":
            rec.facts["signal_assessment"] = result.get("assessment")
            rec.facts["suggests_caution"] = result.get("suggests_caution")
        elif name == "observe":
            rec.facts["creators_snapshot"] = result.get("creators")
            rec.facts["reserve_required_observed"] = result.get("reserve_required")
            rec.facts["signal_text"] = result.get("signal")
