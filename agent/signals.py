"""The signal desk: the one job that is genuinely the language model's.

Recent work on LLMs in inventory control is blunt about this. On InventoryBench
(Baek et al., 2026) a language model asked to choose order quantities is weak:
it "reads narratives into random demand swings" and barely responds to cost
structure. A solver alone does better. The combination that actually wins is the
optimizer informed by the model, not the model guessing numbers. And the thing a
solver cannot do at all is read an unstructured human signal: a supplier email
saying a shipment will slip two weeks, a note that a promotion lands next month,
a headline about a port closure. That text is invisible to the controller unless
something turns it into numbers.

That is this module. The LLM reads a free-text operational signal and proposes a
structured adjustment to the demand the controller plans against: a set of
per-period deltas with a rationale and the exact span of the signal it is acting
on. It never sets an order quantity. The controller re-optimizes against the
adjusted forecast and decides as it always does.

The research also names the failure mode (the model inventing a pattern in
noise), which is why every adjustment this desk proposes is passed to the
verifier (`ActionVerifier.verify_forecast_adjustment`) before it reaches the
controller: it is bounded in magnitude and span, and discarded entirely if it
does not cite the signal. The model informs; it cannot run wild.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .llm import LLMClient

ADJUST_FORECAST_TOOL = {
    "type": "function",
    "function": {
        "name": "adjust_forecast",
        "description": (
            "Translate an operational signal into a change to planned demand. "
            "Only emit deltas the signal actually justifies; emit nothing if the "
            "signal does not imply a demand change. You never set order quantities."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "period_deltas": {
                    "type": "array",
                    "description": "Per-period additive changes to planned demand (units).",
                    "items": {
                        "type": "object",
                        "properties": {
                            "period": {"type": "integer", "description": "Absolute period index the delta applies to."},
                            "delta": {"type": "number", "description": "Units to add (positive) or remove (negative) from planned demand that period."},
                        },
                        "required": ["period", "delta"],
                    },
                },
                "rationale": {"type": "string", "description": "Why the signal implies this change."},
                "cited_signal": {"type": "string", "description": "The exact phrase from the signal being acted on."},
            },
            "required": ["period_deltas", "cited_signal"],
        },
    },
}

_SYSTEM = (
    "You are the signal desk of an inventory controller. You read one operational "
    "signal and decide how planned demand should change, then call adjust_forecast. "
    "Rules: act only on what the signal clearly states; quote the exact phrase in "
    "cited_signal; put deltas on the specific periods the signal implicates; do NOT "
    "invent a demand change the signal does not support; never choose an order "
    "quantity. If the signal implies no demand change, return an empty period_deltas."
)


@dataclass
class ForecastAdjustment:
    """A structured, period-indexed change to planned demand proposed from a signal."""
    period_deltas: dict[int, float] = field(default_factory=dict)
    rationale: str = ""
    cited_signal: str = ""
    source: str = "model"          # "model" | "fallback"

    def is_empty(self) -> bool:
        return not any(abs(d) > 1e-9 for d in self.period_deltas.values())

    def delta_for(self, period: int) -> float:
        return float(self.period_deltas.get(period, 0.0))


class SignalDesk:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    @property
    def available(self) -> bool:
        return bool(self.llm and self.llm.available)

    def interpret(self, signal_text: str, current_period: int, baseline_demand: float,
                  horizon: int = 12) -> ForecastAdjustment:
        """Turn one free-text signal into a proposed forecast adjustment.

        Uses the model when a key is present; otherwise a small scripted parser so
        the pipeline still runs keyless. Either way the result is only a PROPOSAL;
        the verifier bounds it before the controller ever sees it.
        """
        if self.available:
            try:
                return self._interpret_llm(signal_text, current_period, baseline_demand, horizon)
            except Exception:
                pass  # fall through to the scripted parser
        return self._interpret_fallback(signal_text, current_period, baseline_demand, horizon)

    # --- model path ---------------------------------------------------------
    def _interpret_llm(self, signal_text: str, current_period: int,
                       baseline_demand: float, horizon: int) -> ForecastAdjustment:
        user = (
            f"Current period: {current_period}. Planned demand is about "
            f"{baseline_demand:.0f} units per period. Planning horizon reaches period "
            f"{current_period + horizon}.\n\nSignal: \"{signal_text.strip()}\"\n\n"
            "Call adjust_forecast with the demand change this signal implies."
        )
        msg = self.llm.chat(
            messages=[{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
            tools=[ADJUST_FORECAST_TOOL],
            tool_choice={"type": "function", "function": {"name": "adjust_forecast"}},
            temperature=0.0,
        )
        calls = (msg or {}).get("tool_calls") or []
        if not calls:
            return ForecastAdjustment(rationale="model returned no adjustment", source="model")
        args = calls[0].get("function", {}).get("arguments", "{}")
        data = args if isinstance(args, dict) else json.loads(args)
        deltas: dict[int, float] = {}
        for item in data.get("period_deltas", []) or []:
            try:
                deltas[int(item["period"])] = float(item["delta"])
            except (KeyError, TypeError, ValueError):
                continue
        return ForecastAdjustment(
            period_deltas=deltas,
            rationale=str(data.get("rationale", "")),
            cited_signal=str(data.get("cited_signal", "")),
            source="model",
        )

    # --- keyless fallback ---------------------------------------------------
    def _interpret_fallback(self, signal_text: str, current_period: int,
                            baseline_demand: float, horizon: int) -> ForecastAdjustment:
        """A deliberately minimal parser for running without a key. It looks for a
        'week N' / 'period N' and a magnitude ('+40', 'x3', 'triple', 'double'),
        and spreads the bump over that period. This is a stand-in, not the point;
        the model path is where real language understanding happens."""
        import re

        text = signal_text.lower()
        m_period = re.search(r"(?:week|period)\s+(\d+)", text)
        if not m_period:
            return ForecastAdjustment(rationale="fallback: no period found", source="fallback")
        period = int(m_period.group(1))

        delta = 0.0
        if "triple" in text:
            delta = 2.0 * baseline_demand
        elif "double" in text:
            delta = 1.0 * baseline_demand
        else:
            m_mult = re.search(r"x\s*(\d+(?:\.\d+)?)", text)
            m_abs = re.search(r"\+\s*(\d+(?:\.\d+)?)", text)
            m_pct = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
            if m_mult:
                delta = (float(m_mult.group(1)) - 1.0) * baseline_demand
            elif m_abs:
                delta = float(m_abs.group(1))
            elif m_pct:
                delta = (float(m_pct.group(1)) / 100.0) * baseline_demand
        if abs(delta) < 1e-9:
            return ForecastAdjustment(rationale="fallback: no magnitude found", source="fallback")

        span = {period: delta}
        if "week" in text and ("weeks" in text or "-" in text):
            span[period + 1] = delta  # crude two-period spread
        return ForecastAdjustment(
            period_deltas=span,
            rationale=f"fallback parse: +{delta:.0f} units at period {period}",
            cited_signal=signal_text.strip()[:120],
            source="fallback",
        )
