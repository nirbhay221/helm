"""The weekly control loop as a LangGraph state graph, with real human approvals.

    sense -> produce -> validate --pass-------------------------> execute -> confirm -> journal
                ^          |--reject, attempts left------------^             |
                |          |--reject x3, or outside limits--> approval        |--mismatch--> stop
                +----------+                                   |approve/edit -> execute
                                                               |reject       -> hold -> journal

* State holds only plain data, so the checkpointer can persist it; the world, budget and
  solvers live in a Runtime the graph is built around.
* `approval` and `stop` call `interrupt()`: the run pauses, the checkpointer saves it, and a
  later `Command(resume=...)` on the same thread continues it, even after a restart.
* On resume LangGraph re-runs the paused node from its start, so approval nodes never move
  money. Only `execute` does, and every order and payout carries an idempotency key derived
  from the thread and week, so a replay can never pay twice.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from helm.forecast.conformal import DemandAdjustment, Forecast, baseline, forecast
from helm.loop import Helm
from helm.model import Action, Order, Payout
from helm.produce import navigator, paymaster
from helm.sim.world import DailyWorld
from helm.validate import gates
from helm.validate.gates import ESCALATE, Fact

MAX_ATTEMPTS = 3  # the first plan plus two re-plans


class WeekState(TypedDict, total=False):
    monday: str
    attempt: int
    adjust: dict  # what the producer changes after a reject
    proposal: dict  # orders, commission rate, payouts (plain data)
    verdicts: list[dict]
    history: list[dict]  # every attempt's proposal and verdicts
    outcome: str  # executed, approved, edited, held, stopped
    decision: dict
    receipts: list[dict]
    problems: list[str]
    journal: dict


@dataclass
class Runtime:
    world: DailyWorld
    brain: Helm  # producer and validator logic
    first_monday: date
    affiliates: dict[str, float]
    facts: dict[str, list[Fact]] = field(default_factory=dict)  # monday iso -> facts the Lookout read
    executor: Any = None  # defaults to executing against the world

    def state(self, monday: date):
        return self.world.weekly_state(monday, self.first_monday)


# ---------------------------------------------------------------------------------------- data

def action_to_dict(a: Action) -> dict:
    return {
        "orders": [o.__dict__ for o in a.orders],
        "commission_rate": a.commission_rate,
        "payouts": [p.__dict__ for p in a.payouts],
    }


def dict_to_action(d: dict) -> Action:
    return Action(
        orders=[Order(**o) for o in d.get("orders", [])],
        commission_rate=d.get("commission_rate"),
        payouts=[Payout(**p) for p in d.get("payouts", [])],
    )


def _verdict(v: gates.Verdict) -> dict:
    detail = {k: v for k, v in v.detail.items() if not k.startswith("_")}
    return {"gate": v.gate, "outcome": v.outcome, "reason": v.reason, "detail": detail}


# ---------------------------------------------------------------------------------------- graph

def build(rt: Runtime, checkpointer=None):
    def _forecasts(monday: date):
        st = rt.state(monday)
        facts = rt.facts.get(monday.isoformat(), [])
        ev = gates.evidence(facts)
        adj = [DemandAdjustment(f.value["start_week"], f.value["weeks"], f.value["multiplier"])
               for f in (facts if ev.passed else []) if f.kind == "demand_shift"]
        h = rt.brain.horizon
        return st, ev, forecast(st.demand_history, st.week, h, adjustments=adj), \
            baseline(st.demand_history, st.week, h, adjustments=adj)

    def sense(state: WeekState) -> dict:
        # A thread runs one cycle per week; clear last week's values so nothing stale carries over.
        return {"attempt": 0, "adjust": {}, "history": [], "problems": [], "receipts": [],
                "verdicts": [], "outcome": "", "decision": {}, "journal": {}}

    def produce(state: WeekState) -> dict:
        monday = date.fromisoformat(state["monday"])
        st, _, fc, _ = _forecasts(monday)
        adj = state.get("adjust", {})
        limits = rt.brain.limits
        if "max_spend" in adj:
            limits = replace(limits, max_spend_per_week=adj["max_spend"])
        weights = navigator.Weights(cash=navigator.Weights().cash * adj.get("cash_weight", 1.0))
        action, nav = rt.brain.produce(st, fc, limits, weights, conservative=adj.get("conservative", False))
        action.payouts = paymaster.batch(rt.world.commission_owed, rt.affiliates)
        return {"proposal": action_to_dict(action), "attempt": state.get("attempt", 0) + 1}

    def validate(state: WeekState) -> dict:
        monday = date.fromisoformat(state["monday"])
        st, ev, fc, vfc = _forecasts(monday)
        action = dict_to_action(state["proposal"])
        adj = state.get("adjust", {})
        limits = replace(rt.brain.limits, max_spend_per_week=adj.get("max_spend", rt.brain.limits.max_spend_per_week))
        weights = navigator.Weights(cash=navigator.Weights().cash * adj.get("cash_weight", 1.0))
        verdicts = [ev] + rt.brain._validate(st, fc, vfc, action, limits, weights)
        out = [_verdict(v) for v in verdicts]
        hist = state.get("history", []) + [{"proposal": state["proposal"], "verdicts": out}]
        return {"verdicts": out, "history": hist}

    def route_validate(state: WeekState) -> Literal["execute", "produce", "approval"]:
        failed = next((v for v in state["verdicts"] if v["outcome"] != "pass" and v["gate"] != "evidence"), None)
        if failed is None:
            return "execute"
        if failed["outcome"] == ESCALATE or state["attempt"] >= MAX_ATTEMPTS:
            return "approval"
        return "produce"

    def adjust(state: WeekState) -> dict:
        """Runs on the produce edge after a reject: answer the reason, evaluator-optimizer style."""
        failed = next(v for v in state["verdicts"] if v["outcome"] != "pass" and v["gate"] != "evidence")
        code = failed["detail"].get("code", "")
        adj = dict(state.get("adjust", {}))
        spend = dict_to_action(state["proposal"]).spend
        if code == "cash":
            adj["max_spend"] = round(0.6 * min(adj.get("max_spend", rt.brain.limits.max_spend_per_week), spend), 2)
        elif code == "unstable":
            adj["conservative"] = True
        else:
            adj["cash_weight"] = adj.get("cash_weight", 1.0) * 4
        return {"adjust": adj}

    def approval(state: WeekState) -> dict:
        failed = next((v for v in state["verdicts"] if v["outcome"] != "pass" and v["gate"] != "evidence"), None)
        why = "outside the owner's limits" if failed and failed["outcome"] == ESCALATE else "no plan passed the validator"
        answer = interrupt({
            "kind": "approve_week",
            "week": state["monday"],
            "why": why,
            "reason": failed["reason"] if failed else "",
            "proposal": state["proposal"],
            "attempts": state["attempt"],
            "options": ["approve", "edit", "reject"],
        })
        decision = answer if isinstance(answer, dict) else {"decision": str(answer)}
        if decision.get("decision") == "edit":
            return {"decision": decision, "proposal": decision["proposal"], "outcome": "edited"}
        if decision.get("decision") == "approve":
            return {"decision": decision, "outcome": "approved"}
        return {"decision": decision, "outcome": "held",
                "proposal": {"orders": [], "commission_rate": state["proposal"].get("commission_rate"), "payouts": []}}

    def route_approval(state: WeekState) -> Literal["execute", "journal"]:
        return "journal" if state["outcome"] == "held" else "execute"

    def execute(state: WeekState, config) -> dict:
        monday = date.fromisoformat(state["monday"])
        thread = config["configurable"]["thread_id"]
        action = dict_to_action(state["proposal"])
        ex = rt.executor or _WorldExecutor(rt.world)
        receipts = ex.execute(monday, action, key=f"{thread}:{state['monday']}")
        return {"receipts": receipts, "outcome": state.get("outcome") or "executed"}

    def confirm(state: WeekState, config) -> dict:
        """Auditor: read every intended move back from the ledger (and PayPal, in the PayPal executor)."""
        thread = config["configurable"]["thread_id"]
        key = f"{thread}:{state['monday']}"
        action = dict_to_action(state["proposal"])
        led = rt.world.ledger
        problems = []
        for i, o in enumerate(action.orders):
            if not led.has_key(f"{key}:order:{i}:{o.supplier_id}"):
                problems.append(f"order {i} to {o.supplier_id} is not in the ledger")
        for i, p in enumerate(action.payouts):
            if not led.has_key(f"{key}:payout:{i}:{p.receiver}"):
                problems.append(f"payout {i} to {p.receiver} is not in the ledger")
        return {"problems": problems}

    def route_confirm(state: WeekState) -> Literal["stop", "journal"]:
        return "stop" if state.get("problems") else "journal"

    def stop(state: WeekState) -> dict:
        answer = interrupt({"kind": "readback_mismatch", "week": state["monday"], "problems": state["problems"],
                            "options": ["resolved"]})
        return {"decision": answer if isinstance(answer, dict) else {"decision": str(answer)}, "outcome": "stopped"}

    def journal(state: WeekState) -> dict:
        p = state["proposal"]
        return {"journal": {
            "week": state["monday"],
            "outcome": state.get("outcome") or "executed",
            "attempts": state.get("attempt", 0),
            "orders": [(o["supplier_id"], o["qty"]) for o in p.get("orders", [])],
            "commission_rate": p.get("commission_rate"),
            "payouts": [(x["receiver"], x["amount"]) for x in p.get("payouts", [])],
            "verdicts": [(v["gate"], v["outcome"], v["reason"]) for v in state.get("verdicts", [])],
            "decision": state.get("decision"),
            "receipts": state.get("receipts", []),
        }}

    g = StateGraph(WeekState)
    for name, fn in [("sense", sense), ("produce", produce), ("validate", validate), ("adjust", adjust),
                     ("approval", approval), ("execute", execute), ("confirm", confirm), ("stop", stop),
                     ("journal", journal)]:
        g.add_node(name, fn)
    g.add_edge(START, "sense")
    g.add_edge("sense", "produce")
    g.add_edge("produce", "validate")
    g.add_conditional_edges("validate", route_validate, {"execute": "execute", "produce": "adjust", "approval": "approval"})
    g.add_edge("adjust", "produce")
    g.add_conditional_edges("approval", route_approval)
    g.add_edge("execute", "confirm")
    g.add_conditional_edges("confirm", route_confirm)
    g.add_edge("stop", "journal")
    g.add_edge("journal", END)
    return g.compile(checkpointer=checkpointer)


def _sim_id(key: str) -> str:
    return "SIM-" + hashlib.sha256(key.encode()).hexdigest()[:12].upper()


class _WorldExecutor:
    """Executes against the simulated world. The PayPal executor has the same shape and returns PayPal IDs."""

    def __init__(self, world: DailyWorld):
        self.world = world

    def execute(self, monday: date, action: Action, key: str) -> list[dict]:
        if action.commission_rate is not None:
            self.world.set_commission(action.commission_rate)
        receipts = []
        for i, o in enumerate(action.orders):
            k = f"{key}:order:{i}:{o.supplier_id}"
            fresh = self.world.place_order(monday, o, key=k, paypal_id=_sim_id(k))
            receipts.append({"key": k, "kind": "order", "to": o.supplier_id, "qty": o.qty, "new": fresh})
        for i, p in enumerate(action.payouts):
            k = f"{key}:payout:{i}:{p.receiver}"
            fresh = self.world.pay(monday, p, key=k, paypal_id=_sim_id(k))
            receipts.append({"key": k, "kind": "payout", "to": p.receiver, "amount": p.amount, "new": fresh})
        return receipts


# ------------------------------------------------------------------------------------- driving

def run_week(app, monday: date, thread_id: str, owner=None) -> dict:
    """Run one weekly cycle. If it pauses for approval, ask `owner(payload)`; with no owner, return the pause."""
    cfg = {"configurable": {"thread_id": thread_id}}
    out = app.invoke({"monday": monday.isoformat()}, cfg)
    while "__interrupt__" in out:
        payload = out["__interrupt__"][0].value
        if owner is None:
            return out
        out = app.invoke(Command(resume=owner(payload)), cfg)
    return out
