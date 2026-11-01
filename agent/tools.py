"""The tools Helm's brain is allowed to call.

The language model never touches inventory, cash, optimization or PayPal
directly. It can only call these tools, and each tool runs the deterministic
code that actually does the work:

  observe             -> read the real business state and forecast
  plan_replenishment  -> the receding-horizon LP decides an order target
  source_suppliers    -> the Awardsmith MILP finds the cheapest supplier split
  execute_purchase    -> place + pay the order, advance the business one period
  pay_partners        -> send a PayPal Payouts batch, through the AUP-gated tool

So the model decides WHAT to do and the deterministic layer decides whether and
how it is allowed to happen. Costs and quantities the model would otherwise have
to guess are recomputed here from the solvers, so the numbers in the journal are
always the real ones. Every tool returns a JSON-serializable dict.
"""
from __future__ import annotations

import json
from typing import Any

from arms.awardsmith import AwardsmithSolver, SupplierQuote, naive_single_supplier_cost
from helm_core import RecedingHorizonController
from paypal import PayPalClient, Ledger, create_payout
from simulator import BusinessSim

from .verifier import ActionVerifier

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "observe",
            "description": (
                "Read the current business state: period, inventory on hand, cash, "
                "target inventory, the demand forecast for the planning horizon, and "
                "orders already in transit. Call this first to sense before deciding."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plan_replenishment",
            "description": (
                "Run the receding-horizon optimizer on the current state. It returns "
                "the recommended order quantity for this period that keeps inventory "
                "near target and cash above the floor. Use its 'recommended_order_qty' "
                "as the amount to source unless you have a specific reason to override."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "source_suppliers",
            "description": (
                "Given a target quantity, find the cheapest way to buy it across the "
                "available supplier quotes (respecting minimum order quantities, "
                "capacity and all-units volume discounts). Returns the supplier split, "
                "the total cost, and the cost a naive single-supplier buy would incur."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target_qty": {
                        "type": "number",
                        "description": "Units to acquire this period (>= 0).",
                    }
                },
                "required": ["target_qty"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_purchase",
            "description": (
                "Place and pay for this period's supplier order of the given quantity, "
                "then advance the business one period. The actual cost and supplier "
                "split are recomputed from the sourcing optimizer, so you cannot "
                "misprice it. Returns the realized demand, sales, and the new "
                "inventory and cash. Pass 0 to order nothing this period."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_qty": {
                        "type": "number",
                        "description": "Units to order this period (>= 0).",
                    }
                },
                "required": ["order_qty"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pay_partners",
            "description": (
                "Send a PayPal Payouts batch to partners by email. Only AUP-permitted "
                "purposes are allowed (commission, rebate, reward, incentive); payroll "
                "and paying suppliers for goods are refused. Batches above the approval "
                "threshold are held until re-sent with approved=true."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sender_batch_id": {"type": "string"},
                    "purpose": {
                        "type": "string",
                        "enum": ["COMMISSION", "REBATE", "REWARD", "INCENTIVE"],
                    },
                    "recipients": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "email": {"type": "string"},
                                "amount": {"type": "number"},
                                "note": {"type": "string"},
                            },
                            "required": ["email", "amount"],
                        },
                    },
                    "approved": {"type": "boolean"},
                },
                "required": ["sender_batch_id", "purpose", "recipients"],
            },
        },
    },
]


def _num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _normalize_recipients(recipients: Any) -> list[dict]:
    """Models emit `recipients` in assorted shapes (a JSON string, a single
    object, a list of objects, or bare email strings). Normalize to a list of
    {email, amount, note} dicts; malformed entries are dropped so the AUP gate
    and amount checks downstream do the real validation."""
    if isinstance(recipients, str):
        try:
            recipients = json.loads(recipients)
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(recipients, dict):
        recipients = [recipients]
    out: list[dict] = []
    for r in recipients or []:
        if isinstance(r, dict):
            out.append(r)
        elif isinstance(r, str):
            try:
                obj = json.loads(r)
                if isinstance(obj, dict):
                    out.append(obj)
                    continue
            except (json.JSONDecodeError, TypeError):
                pass
            out.append({"email": r})  # amount missing -> rejected downstream
    return out


class HelmTools:
    """Binds the tool names to the live objects and executes them safely."""

    def __init__(
        self,
        sim: BusinessSim,
        controller: RecedingHorizonController,
        suppliers: list[SupplierQuote],
        ledger: Ledger,
        paypal: PayPalClient,
    ) -> None:
        self.sim = sim
        self.controller = controller
        self.suppliers = suppliers
        self.awardsmith = AwardsmithSolver(suppliers)
        self.ledger = ledger
        self.paypal = paypal
        self.verifier = ActionVerifier(sim, controller, suppliers)

    @property
    def schemas(self) -> list[dict]:
        return TOOL_SCHEMAS

    # --- individual tools ---------------------------------------------------
    def observe(self) -> dict:
        H = self.controller.p.horizon
        forecast = [round(float(x), 2) for x in self.sim.forecast(H)]
        pending = {str(k): round(v, 2) for k, v in self.sim.pipeline_arrivals(H).items()}
        return {
            "period": self.sim.t,
            "inventory": round(self.sim.inventory, 2),
            "cash": round(self.sim.cash, 2),
            "target_inventory": self.sim.p.target_inventory,
            "cash_floor": self.sim.p.cash_floor,
            "forecast_demand": forecast,
            "in_transit_by_offset": pending,
            "periods_remaining": max(0, self.sim.n_periods - self.sim.t),
        }

    def plan_replenishment(self) -> dict:
        H = self.controller.p.horizon
        dec = self.controller.plan(
            inv0=self.sim.inventory,
            cash0=self.sim.cash,
            forecast=self.sim.forecast(H),
            target=self.sim.target_trajectory(H + 1),
            pending_arrivals=self.sim.pipeline_arrivals(H),
        )
        return {
            "recommended_order_qty": round(dec.order_qty, 2),
            "status": dec.status,
            "projected_total_deviation": dec.projected_dev,
        }

    def source_suppliers(self, target_qty: float) -> dict:
        Q = max(0.0, _num(target_qty))
        if Q <= 0:
            return {"target_qty": 0.0, "lines": [], "total_cost": 0.0,
                    "naive_cost": 0.0, "savings_vs_naive": 0.0,
                    "note": "Target is zero; nothing to source."}
        res = self.awardsmith.allocate(Q)
        naive = naive_single_supplier_cost(self.suppliers, Q)
        lines = [
            {"supplier": ln.supplier, "quantity": ln.quantity,
             "unit_price": ln.unit_price, "line_cost": ln.line_cost}
            for ln in res.lines
        ]
        savings = round(naive - res.total_cost, 2) if naive != float("inf") else None
        return {
            "target_qty": round(Q, 2),
            "status": res.status,
            "awarded_qty": res.total_quantity,
            "lines": lines,
            "total_cost": res.total_cost,
            "naive_cost": None if naive == float("inf") else naive,
            "savings_vs_naive": savings,
        }

    def execute_purchase(self, order_qty: float) -> dict:
        # The model's order_qty is only a proposal. The verifier overrules it
        # with the controller's authoritative quantity and clamps for the hard
        # cash floor, so the executed number is never the model's to invent.
        verdict = self.verifier.verify_order(_num(order_qty))
        qty = max(0.0, verdict.executed_value)
        cost = 0.0
        split: list[dict] = []
        awarded = 0.0
        if qty > 0:
            res = self.awardsmith.allocate(qty)
            if res.status in ("Optimal", "Feasible") and res.total_quantity > 0:
                awarded = res.total_quantity
                cost = res.total_cost
                split = [
                    {"supplier": ln.supplier, "quantity": ln.quantity,
                     "unit_price": ln.unit_price}
                    for ln in res.lines
                ]
            else:
                verdict.note(f"sourcing {qty} was {res.status}; ordered nothing")
                qty = 0.0
        obs = self.sim.step(awarded if qty > 0 else 0.0, order_cost=cost if qty > 0 else None)
        return {
            "proposed_qty": round(_num(order_qty), 2),
            "ordered_qty": round(awarded, 2),
            "order_cost": round(cost, 2),
            "supplier_split": split,
            "verifier_overrides": verdict.violations,
            **self._post_step(obs),
        }

    def _post_step(self, obs) -> dict:
        return {
            "period_closed": obs.period,
            "realized_demand": obs.demand,
            "sales": obs.sales,
            "inventory": obs.inventory,
            "cash": obs.cash,
            "deviation_from_target": round(obs.inv_deviation, 2),
            "order_arrived": obs.order_arrived,
        }

    def pay_partners(
        self,
        sender_batch_id: str,
        purpose: str,
        recipients: Any,
        approved: bool = False,
    ) -> dict:
        clean = _normalize_recipients(recipients)
        # verifier gate: AUP purpose, positive amounts, and never pay out more
        # than cash on hand. (Idempotency + approval threshold are enforced in
        # the Payouts tool itself.)
        verdict = self.verifier.verify_payout(clean, str(purpose))
        if not verdict.ok:
            return {"status": "blocked", "message": "; ".join(verdict.violations),
                    "batch_id": None, "total_amount": verdict.executed_value,
                    "currency": "USD", "purpose": str(purpose).upper(),
                    "recipients": len(clean), "demo": self.paypal.demo,
                    "verifier_overrides": verdict.violations}
        res = create_payout(
            client=self.paypal,
            ledger=self.ledger,
            recipients=clean,
            sender_batch_id=str(sender_batch_id),
            purpose=str(purpose),
            approved=bool(approved),
        )
        return {
            "status": res.status,
            "message": res.message,
            "batch_id": res.batch_id,
            "total_amount": res.total_amount,
            "currency": res.currency,
            "purpose": res.purpose,
            "recipients": res.recipients,
            "demo": res.demo,
            "verifier_overrides": verdict.violations,
        }

    # --- dispatch -----------------------------------------------------------
    def call(self, name: str, arguments: dict) -> dict:
        args = arguments or {}
        if name == "observe":
            return self.observe()
        if name == "plan_replenishment":
            return self.plan_replenishment()
        if name == "source_suppliers":
            return self.source_suppliers(args.get("target_qty", 0))
        if name == "execute_purchase":
            return self.execute_purchase(args.get("order_qty", 0))
        if name == "pay_partners":
            return self.pay_partners(
                sender_batch_id=args.get("sender_batch_id", ""),
                purpose=args.get("purpose", ""),
                recipients=args.get("recipients", []),
                approved=bool(args.get("approved", False)),
            )
        return {"error": f"unknown tool '{name}'"}


def parse_arguments(raw: Any) -> dict:
    """Tool-call arguments arrive as a JSON string (or already a dict)."""
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
