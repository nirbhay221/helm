"""The tools the money-out operator agent is allowed to call.

This is the inversion: the language model is the operator and runs the loop; the
deterministic pieces are tools it invokes and guardrails it is bounded by. The
model decides the risk posture and which creators to release versus hold (the
judgment only it can do from messy per-creator context); the solver sizes the
safe release (the math it must not guess); PayPal moves the money; and the pay
tool hard-clamps the model to the solver's safe cap, the AUP purpose, and the
human-approval threshold, so a reckless model cannot overspend or under-reserve.

  observe            -> the cycle's state: cash, reserve, each creator's owed + context
  interpret_signal   -> read the unstructured signal into a risk read (signal desk)
  size_safe_release  -> the controller's maximum safe total to release this cycle
  pay_creators       -> release money to chosen creators (guarded + clamped), advance

Every tool returns a JSON-serializable dict; the grounded journal is built from
these results, never from the model's prose.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from marketplace import CashPayoutController, CreatorMarketplace
from marketplace.creator_ledger import CreatorLedger
from marketplace.forecast import ETSForecaster
from paypal import Ledger, PayPalClient
from paypal.mcp_payouts_tool import ALLOWED_PAYOUT_PURPOSES, create_payout

from .signals import SignalDesk


@dataclass
class OperatorCreator:
    name: str
    email: str
    weight: float
    context: str = ""        # the messy human context the model judges risk from
    owed: float = 0.0


TOOL_SCHEMAS: list[dict] = [
    {"type": "function", "function": {
        "name": "observe",
        "description": ("Read the current cycle: period, cash, the cash floor, the reserve "
                        "required against chargebacks, total owed to creators, and for each "
                        "creator their owed balance and the context you judge their risk from. "
                        "Call this first."),
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "interpret_signal",
        "description": ("Read this cycle's unstructured signal (a note about virality, fraud, a "
                        "dispute wave) into a demand/risk read via the model panel. Use it to "
                        "choose your risk posture."),
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "size_safe_release",
        "description": ("Ask the controller for the maximum total it is safe to release to "
                        "creators this cycle while keeping cash above floor+reserve. Pass a "
                        "risk_multiplier >= 1.0 to be more conservative (hold more reserve) when "
                        "the signal warns of risk; 1.0 is neutral."),
        "parameters": {"type": "object", "properties": {
            "risk_multiplier": {"type": "number", "description": "1.0 neutral; higher = hold more reserve."}},
            "required": ["risk_multiplier"]}}},
    {"type": "function", "function": {
        "name": "pay_creators",
        "description": ("Release money to specific creators now. Provide allocations as a list of "
                        "{creator, amount}. Pay the creators you judge low-risk and hold the ones "
                        "you judge risky. The total is hard-clamped to the safe release size, to "
                        "cash, and to what each creator is owed; amounts above the approval "
                        "threshold are held for a human. This also closes the cycle."),
        "parameters": {"type": "object", "properties": {
            "allocations": {"type": "array", "items": {"type": "object", "properties": {
                "creator": {"type": "string"}, "amount": {"type": "number"}},
                "required": ["creator", "amount"]}}},
            "required": ["allocations"]}}},
]


class OperatorTools:
    def __init__(self, sim: CreatorMarketplace, controller: CashPayoutController,
                 creators: list[OperatorCreator], signal_desk: SignalDesk,
                 client: PayPalClient, ledger: Ledger,
                 approval_threshold: float = 1500.0) -> None:
        self.sim = sim
        self.controller = controller
        self.creators = {c.name: c for c in creators}
        self.signals = signal_desk
        self.client = client
        self.ledger = ledger
        self.approval_threshold = approval_threshold
        self.current_signal = ""
        self._safe_release: float | None = None
        self._total_weight = sum(c.weight for c in creators) or 1.0
        # per-creator balances with hold-until-window and recoupment
        self.led = CreatorLedger(sim.p.chargeback_window)

    # --- read ---------------------------------------------------------------
    def observe(self) -> dict:
        s, now = self.sim, self.sim.t
        return {
            "period": now,
            "cash": round(s.cash, 2),
            "cash_floor": s.p.cash_floor,
            "reserve_required": round(s.reserve_required(), 2),
            "total_owed": round(sum(self.led.total_unpaid(n) for n in self.creators), 2),
            "signal": self.current_signal or "(none)",
            # owed = all unpaid; settled_owed = past its chargeback window (safe to pay);
            # releasing more than settled_owed is an early release you judge low-risk.
            # recoup_due = debt this creator owes from a reversed sale.
            "creators": [{"creator": c.name, "context": c.context,
                          "owed": self.led.total_unpaid(c.name),
                          "settled_owed": self.led.settled_unpaid(c.name, now),
                          "recoup_due": self.led.recoup_due(c.name)}
                         for c in self.creators.values()],
        }

    def interpret_signal(self) -> dict:
        adj = self.signals.interpret(self.current_signal or "no notable signal",
                                     current_period=self.sim.t,
                                     baseline_demand=self.sim.p.baseline_gmv, horizon=6)
        implies_risk = (not adj.is_empty()) or ("fraud" in (self.current_signal or "").lower()) \
            or ("chargeback" in (self.current_signal or "").lower())
        return {
            "assessment": adj.rationale or "no quantifiable change",
            "cited": adj.cited_signal,
            "confidence": adj.confidence,
            "suggests_caution": bool(implies_risk),
        }

    def size_safe_release(self, risk_multiplier: float = 1.0, service_z: float = 1.65) -> dict:
        s, c = self.sim, self.controller
        mult = max(1.0, float(risk_multiplier))
        H = c.p.horizon
        # time-series forecast of GMV (ETS) instead of a flat line, with an
        # uncertainty band that sizes a safety buffer on the reserve: hold more
        # when the forecast is less certain (the chance-constrained upgrade).
        hist = list(s._gmv_history[-12:]) or [s.p.baseline_gmv]
        means, sigmas = ETSForecaster().fit(hist).forecast(H)
        recent = list(s._gmv_history[-s.p.chargeback_window:])
        reserve_floor = [s.p.reserve_rate * mult * s.exposure()]
        for i in range(H):
            window = (recent + means[: i + 1])[-s.p.chargeback_window:]
            base_reserve = s.p.reserve_rate * mult * sum(window)
            buffer = service_z * sigmas[i] * s.p.reserve_rate
            reserve_floor.append(base_reserve + buffer)
        owed0 = sum(self.led.total_unpaid(n) for n in self.creators)
        dec = c.plan(owed0=owed0, cash0=s.cash,
                     forecast_gmv=means, reserve_floor=reserve_floor,
                     cash_floor=s.p.cash_floor)
        self._safe_release = max(0.0, float(dec.payout))
        return {"safe_release_total": round(self._safe_release, 2),
                "risk_multiplier": mult,
                "forecast_gmv_next": round(means[0], 2),
                "forecast_sigma_next": round(sigmas[0], 2),
                "reserve_required_effective": round(reserve_floor[0], 2),
                "cash": round(s.cash, 2), "cash_floor": s.p.cash_floor}

    # --- act ----------------------------------------------------------------
    def pay_creators(self, allocations: Any, approved: bool = False) -> dict:
        overrides: list[str] = []
        alloc = self._clean_allocations(allocations, overrides)

        # guardrail 1: safe-release cap (size it at neutral if the model skipped sizing)
        cap = self._safe_release if self._safe_release is not None else \
            self.size_safe_release(1.0)["safe_release_total"]
        requested = round(sum(alloc.values()), 2)
        if requested > cap + 1e-6 and requested > 0:
            scale = cap / requested
            alloc = {k: round(v * scale, 2) for k, v in alloc.items()}
            overrides.append(f"requested {requested} exceeds safe release {round(cap,2)}; "
                             f"scaled down to fit")

        total = round(sum(alloc.values()), 2)
        recipients = [{"email": self.creators[n].email, "amount": a,
                       "note": f"creator earnings wk{self.sim.t}"}
                      for n, a in alloc.items() if a > 0 and n in self.creators]

        status, batch_id, demo = "nothing_to_pay", None, self.client.demo
        if recipients:
            # guardrails 2+3: AUP purpose + approval threshold live inside create_payout
            res = create_payout(self.client, self.ledger, recipients,
                                sender_batch_id=f"helm-op-{self.sim.t}", purpose="COMMISSION",
                                approval_threshold=self.approval_threshold, approved=bool(approved))
            status, batch_id, demo = res.status, res.batch_id, res.demo
            if status == "completed":
                for n, a in alloc.items():
                    self.led.pay(n, a, self.sim.t)

        paid = total if status == "completed" else 0.0
        obs = self.sim.step(paid)                      # advance time; accrue inflows
        # attribute this period's new earnings and chargebacks to creators by weight,
        # through the ledger: earnings held until their window closes, chargebacks
        # eating unpaid first and clawing back the rest.
        for c in self.creators.values():
            share = c.weight / self._total_weight
            self.led.accrue(c.name, obs.creator_earnings * share, obs.period)
            if obs.chargebacks > 1e-9:
                self.led.chargeback(c.name, obs.chargebacks * share, obs.period)
        self._safe_release = None                       # must re-size next cycle

        return {
            "status": status, "batch_id": batch_id, "demo": demo,
            "paid_total": round(paid, 2),
            "paid": [{"creator": n, "amount": a} for n, a in alloc.items() if a > 0],
            "cash_after": round(self.sim.cash, 2),
            "reserve_ok_after": obs.reserve_ok,
            "guardrail_overrides": overrides,
            "period_closed": obs.period,
        }

    # --- helpers ------------------------------------------------------------
    def _clean_allocations(self, allocations: Any, overrides: list[str]) -> dict[str, float]:
        if isinstance(allocations, str):
            try:
                allocations = json.loads(allocations)
            except Exception:
                allocations = []
        out: dict[str, float] = {}
        for item in allocations or []:
            if not isinstance(item, dict):
                continue
            name = item.get("creator")
            try:
                amt = float(item.get("amount", 0))
            except (TypeError, ValueError):
                continue
            if name not in self.creators:
                overrides.append(f"unknown creator '{name}'; dropped")
                continue
            owed = self.led.total_unpaid(name)
            if amt > owed + 1e-6:
                overrides.append(f"{name}: requested {round(amt,2)} > owed {round(owed,2)}; capped")
                amt = owed
            if amt > 1e-6:
                out[name] = round(amt, 2)
        return out

    def call(self, name: str, arguments: dict) -> dict:
        if name == "observe":
            return self.observe()
        if name == "interpret_signal":
            return self.interpret_signal()
        if name == "size_safe_release":
            return self.size_safe_release(float(arguments.get("risk_multiplier", 1.0)))
        if name == "pay_creators":
            # The agent can never approve its own payout. Approval above the
            # threshold is a human action injected out of band (loopjacking:
            # the gate must not be a field the model controls), so the agent
            # path always runs unapproved and a large batch is held.
            return self.pay_creators(arguments.get("allocations", []), approved=False)
        return {"error": f"unknown tool '{name}'"}
