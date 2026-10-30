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
    budget: Any = None  # AnnualBudget; enables the monthly level
    month_plans: dict[str, dict] = field(default_factory=dict)  # "2026-04" -> signed-off MonthPlan
    base_plan: Any = None  # the BusinessPlan read off the budget, before monthly rebalancing

    def state(self, monday: date):
        return self.world.weekly_state(monday, self.first_monday)

    def sync_plan(self) -> None:
        """Point the weekly Navigator at the signed-off monthly operating plans (budget elsewhere)."""
        if self.budget is None or self.base_plan is None:
            return
        from helm.calendar import WEEKDAY_PROFILE, split_exact
        cal = self.budget.cal
        daily: dict[date, int] = {}
        for key, plan in self.month_plans.items():
            y, m = int(key[:4]), int(key[5:])
            days = cal.month_days(y, m)
            for d, u in zip(days, split_exact(plan["units"], [WEEKDAY_PROFILE[x.weekday()] for x in days])):
                daily[d] = u
        targets = list(self.base_plan.sales_target)
        for k in range(len(targets)):
            monday = self.first_monday + timedelta(days=7 * k)
            week = [monday + timedelta(days=i) for i in range(7)]
            if any(d in daily for d in week):
                targets[k] = float(sum(daily.get(d, self.budget.day(d).units if cal.year_start <= d <= cal.year_end else 0)
                                       for d in week))
        self.brain.business = replace(self.base_plan, sales_target=tuple(targets))

    def envelope(self, monday: date):
        """The owner's approved envelope for this week: weekly limit, capped by what is left of the month plan."""
        limits = self.brain.limits
        thursday = monday + timedelta(days=3)  # ISO rule: a week belongs to the month holding its Thursday
        plan = self.month_plans.get(f"{thursday.year:04d}-{thursday.month:02d}")
        if plan is None:
            return limits
        start = thursday.replace(day=1)
        spent = sum(d.purchase_cost + d.paid_out for d in self.world.ledger.days() if start <= d.day < monday) / 100
        left = plan["purchase_budget"] + plan["commission_budget"] - spent
        return replace(limits, max_spend_per_week=max(0.0, min(limits.max_spend_per_week, left)))


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
        rt.sync_plan()
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
        rt.sync_plan()
        verdicts = [ev] + rt.brain._validate(st, fc, vfc, action, limits, weights, rt.envelope(monday))
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
        why = "outside the owner's approved limits" if failed and failed["outcome"] == ESCALATE else "no plan passed the validator"
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


# ------------------------------------------------------------------------------ monthly level

class MonthState(TypedDict, total=False):
    month: str
    standing: dict
    targets: dict  # month key -> operating units for the rest of the year
    plan: dict
    problems: list[str]
    tries: int
    slack: float
    decision: dict
    outcome: str


def build_month(rt: Runtime, checkpointer=None, unit_cost: float = 8.6, slack: float = 1.35):
    """Strategist + Planner + plan validation + the owner's monthly sign-off.

        assess -> strategist -> plan -> check --problems, tries left--> plan (tighter)
                                          |--ok or out of tries------> signoff (interrupt) -> commit
    """
    from helm import planning
    from helm.forecast.conformal import forecast as _fc

    def _today(state):
        y, m = int(state["month"][:4]), int(state["month"][5:])
        return date(y, m, 1)

    def assess(state: MonthState) -> dict:
        first = _today(state)
        through = first - timedelta(days=1)
        hist = rt.state(first - timedelta(days=first.weekday())).demand_history
        weekly = float(_fc(hist, 0, 4).point.mean())
        st = planning.standing(rt.world.ledger, rt.budget, through, weekly, rt.world.price_cents)
        return {"standing": st.as_dict(), "tries": 0, "slack": slack, "problems": [], "decision": {}, "outcome": ""}

    def strategist(state: MonthState) -> dict:
        d = rt.world.demand
        max_lift = d.elasticity * d.affiliate_share * (rt.brain.limits.commission_max - d.baseline_commission)
        st = planning.Standing(**state["standing"])
        return {"targets": planning.strategist(st, rt.budget, _today(state), max_lift)}

    def plan(state: MonthState) -> dict:
        units = state["targets"].get(state["month"], rt.budget.months[state["month"]].units)
        p = planning.planner(state["month"], units, rt.budget, unit_cost, rt.world.commission_rate,
                             rt.world.price_cents, slack=state.get("slack", slack))
        return {"plan": p.as_dict(), "tries": state.get("tries", 0) + 1}

    def check(state: MonthState) -> dict:
        p = planning.MonthPlan(**state["plan"])
        low = int(p.units * 0.75)
        problems = planning.check_plan(p, rt.world.cash() / 100, rt.base_plan.cash_floor, low, rt.world.price_cents / 100)
        return {"problems": problems}

    def route_check(state: MonthState) -> Literal["tighten", "signoff"]:
        return "tighten" if state["problems"] and state["tries"] < 3 else "signoff"

    def tighten(state: MonthState) -> dict:
        return {"slack": round(state.get("slack", slack) * 0.8, 3)}

    def signoff(state: MonthState) -> dict:
        p = state["plan"]
        prev = rt.month_plans.get(_prev_month(state["month"]))
        answer = interrupt({
            "kind": "approve_month",
            "month": state["month"],
            "standing": state["standing"],
            "plan": p,
            "targets_rest_of_year": state["targets"],
            "change_vs_budget_units": p["rebalance_units"],
            "previous_month_plan": prev,
            "problems": state["problems"],
            "options": ["approve", "edit", "reject"],
        })
        decision = answer if isinstance(answer, dict) else {"decision": str(answer)}
        if decision.get("decision") == "edit":
            return {"decision": decision, "plan": {**p, **decision.get("plan", {})}, "outcome": "edited"}
        if decision.get("decision") == "approve":
            return {"decision": decision, "outcome": "approved"}
        return {"decision": decision, "outcome": "rejected"}

    def commit(state: MonthState) -> dict:
        if state["outcome"] in ("approved", "edited"):
            rt.month_plans[state["month"]] = state["plan"]
        return {}

    g = StateGraph(MonthState)
    for name, fn in [("assess", assess), ("strategist", strategist), ("plan", plan), ("check", check),
                     ("tighten", tighten), ("signoff", signoff), ("commit", commit)]:
        g.add_node(name, fn)
    g.add_edge(START, "assess")
    g.add_edge("assess", "strategist")
    g.add_edge("strategist", "plan")
    g.add_edge("plan", "check")
    g.add_conditional_edges("check", route_check)
    g.add_edge("tighten", "plan")
    g.add_edge("signoff", "commit")
    g.add_edge("commit", END)
    return g.compile(checkpointer=checkpointer)


def _prev_month(key: str) -> str:
    y, m = int(key[:4]), int(key[5:])
    return f"{y - (m == 1):04d}-{(m - 2) % 12 + 1:02d}"


# --------------------------------------------------------------------------------- the day graph

class DayState(TypedDict, total=False):
    day: str
    ran: list[str]
    month: dict
    week: dict


def build_day(rt: Runtime, checkpointer=None):
    """The parent graph: route each day to the levels that are due, each level a subgraph.

    The monthly and weekly graphs are compiled without their own checkpointer, so they run as
    subgraphs of this one and share its persistence; an interrupt in either pauses the whole
    day, and resuming the day resumes the subgraph exactly where it stopped.
    """
    month_app = build_month(rt)
    week_app = build(rt)

    def route(state: DayState) -> dict:
        return {"ran": [], "month": {}, "week": {}}

    def due(state: DayState) -> Literal["monthly", "weekly", "done"]:
        # Slow level first: on a day that is both the 1st and a Monday, the month is signed off
        # before the week plans inside it.
        d = date.fromisoformat(state["day"])
        if d.day == 1 and rt.budget is not None and d >= rt.budget.cal.year_start:
            return "monthly"
        return "weekly" if d.weekday() == 0 else "done"

    def monthly(state: DayState, config) -> dict:
        d = date.fromisoformat(state["day"])
        out = month_app.invoke({"month": f"{d.year:04d}-{d.month:02d}"}, config)
        return {"month": {k: out.get(k) for k in ("plan", "outcome", "standing")}, "ran": state.get("ran", []) + ["monthly"]}

    def after_monthly(state: DayState) -> Literal["weekly", "done"]:
        return "weekly" if date.fromisoformat(state["day"]).weekday() == 0 else "done"

    def weekly(state: DayState, config) -> dict:
        out = week_app.invoke({"monday": state["day"]}, config)
        return {"week": out.get("journal", {}), "ran": state.get("ran", []) + ["weekly"]}

    def done(state: DayState) -> dict:
        return {}

    g = StateGraph(DayState)
    for name, fn in [("route", route), ("monthly", monthly), ("weekly", weekly), ("done", done)]:
        g.add_node(name, fn)
    g.add_edge(START, "route")
    g.add_conditional_edges("route", due, ["monthly", "weekly", "done"])
    g.add_conditional_edges("monthly", after_monthly, ["weekly", "done"])
    g.add_edge("weekly", "done")
    g.add_edge("done", END)
    return g.compile(checkpointer=checkpointer)


def run_day(app, day: date, thread_id: str, owner=None) -> dict:
    cfg = {"configurable": {"thread_id": thread_id}}
    out = app.invoke({"day": day.isoformat()}, cfg)
    while "__interrupt__" in out:
        if owner is None:
            return out
        out = app.invoke(Command(resume=owner(out["__interrupt__"][0].value)), cfg)
    return out
