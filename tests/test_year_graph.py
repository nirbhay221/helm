import sqlite3
from dataclasses import replace
from datetime import date

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from helm import graph
from helm.budget import revenue_bridge
from helm.calendar import split_exact, week_key
from helm.ledger import Event, Ledger
from helm.year import build_year, run_days, runtime

MONDAY = date(2026, 1, 5)


def test_split_exact_always_sums_to_the_total():
    for total in (0, 1, 7, 1000, 123457):
        for w in ([1], [1, 1, 1], [0.92, 0.95, 0.98, 1.0, 1.08, 1.12, 0.95]):
            assert sum(split_exact(total, w)) == total


def test_budget_days_weeks_months_and_year_agree_to_the_cent():
    y = build_year()
    b = y.budget
    year = b.rollup("year")["2026"]
    for f in ("units", "revenue", "purchases", "commission"):
        assert sum(getattr(t, f) for t in b.days()) == year[f]
        assert sum(m[f] for m in b.rollup("month").values()) == year[f]
        assert sum(w[f] for w in b.rollup("week").values()) == year[f]
        assert sum(getattr(l, f) for l in b.months.values()) == year[f]


def test_week_spanning_two_months_is_split_by_day():
    y = build_year()
    # Mon 26 Jan to Sun 1 Feb 2026 is one ISO week across two months.
    wk = y.budget.rollup("week")[week_key(date(2026, 1, 26))]
    jan = y.budget.to_date(date(2026, 1, 31), start=date(2026, 1, 26))
    feb = y.budget.to_date(date(2026, 2, 1), start=date(2026, 2, 1))
    assert wk["units"] == jan["units"] + feb["units"]


def test_ledger_rollups_match_days_and_reject_duplicate_keys():
    led = Ledger()
    led.append(Event(date(2026, 1, 30), "opening", units=10, cents=10_000))
    led.append(Event(date(2026, 1, 30), "sale", units=3, cents=7_200))
    assert led.append(Event(date(2026, 2, 2), "purchase", units=5, cents=4_000, idempotency_key="k1"))
    assert not led.append(Event(date(2026, 2, 2), "purchase", units=5, cents=4_000, idempotency_key="k1"))
    led.append(Event(date(2026, 2, 3), "sale", units=1, cents=2_400))
    months = led.rollup("month")
    assert months["2026-01"]["revenue"] == 7_200 and months["2026-02"]["revenue"] == 2_400
    assert months["2026-02"]["purchase_cost"] == 4_000  # counted once
    assert led.days()[-1].cash_end == 10_000 + 7_200 - 4_000 + 2_400


def test_ledger_survives_save_and_load(tmp_path):
    y = build_year()
    path = str(tmp_path / "ledger.db")
    y.world.ledger.save(path)
    again = Ledger.load(path)
    assert again.rollup("month") == y.world.ledger.rollup("month")


def test_revenue_bridge_adds_up():
    b = revenue_bridge(actual_units=700, actual_revenue=1_610_000, budget_units=600, budget_revenue=1_440_000)
    assert b["volume"] + b["price"] == b["total"] == 170_000


def _escalating_year():
    y = build_year()
    y.limits = replace(y.limits, max_payout_per_affiliate=1.0)  # any payout will need the owner
    rt = runtime(y, imagine_runs=30)
    return y, rt


def test_graph_pauses_for_the_owner_and_resumes_after_a_restart(tmp_path):
    y, rt = _escalating_year()
    db = str(tmp_path / "checkpoints.db")
    cfg = {"configurable": {"thread_id": "fy2026"}}

    app = graph.build(rt, SqliteSaver(sqlite3.connect(db, check_same_thread=False)))
    paused = app.invoke({"monday": MONDAY.isoformat()}, cfg)
    assert "__interrupt__" in paused
    ask = paused["__interrupt__"][0].value
    assert ask["kind"] == "approve_week" and "cap" in ask["reason"]
    assert not any(e.kind == "purchase" and e.day == MONDAY for e in y.world.ledger.events)  # nothing moved yet

    # Simulate a restart: a brand new graph object on the same checkpoint database.
    app2 = graph.build(rt, SqliteSaver(sqlite3.connect(db, check_same_thread=False)))
    done = app2.invoke(Command(resume={"decision": "approve", "by": "owner"}), cfg)
    assert done["outcome"] == "approved"
    assert done["journal"]["decision"]["by"] == "owner"
    bought = [e for e in y.world.ledger.events if e.kind in ("purchase", "payout") and e.day == MONDAY]
    assert len(bought) == len(done["receipts"]) > 0


def test_owner_reject_holds_and_moves_no_money():
    y, rt = _escalating_year()
    app = graph.build(rt, InMemorySaver())
    out = graph.run_week(app, MONDAY, "t", owner=lambda p: {"decision": "reject", "reason": "wait a week"})
    assert out["outcome"] == "held" and out["receipts"] == []
    assert not any(e.kind in ("purchase", "payout") and e.day == MONDAY for e in y.world.ledger.events)


def test_owner_edit_executes_the_edited_plan():
    y, rt = _escalating_year()
    app = graph.build(rt, InMemorySaver())

    def owner(p):
        edited = dict(p["proposal"], payouts=[])  # approve the orders, pay commissions later
        return {"decision": "edit", "proposal": edited}

    out = graph.run_week(app, MONDAY, "t", owner=owner)
    assert out["outcome"] == "edited"
    assert not any(e.kind == "payout" and e.day == MONDAY for e in y.world.ledger.events)


def test_execution_is_idempotent_on_replay():
    y, rt = _escalating_year()
    ex = graph._WorldExecutor(y.world)
    action = graph.dict_to_action({"orders": [{"supplier_id": "fastfab", "qty": 60, "unit_price": 9.8, "fixed_fee": 25.0}],
                                   "commission_rate": 0.1, "payouts": []})
    first = ex.execute(MONDAY, action, key="fy:w1")
    again = ex.execute(MONDAY, action, key="fy:w1")
    assert first[0]["new"] and not again[0]["new"]
    assert sum(1 for e in y.world.ledger.events if e.kind == "purchase" and e.day == MONDAY) == 1


def test_auditor_stops_money_on_a_readback_mismatch():
    y, rt = _escalating_year()

    class Lossy(graph._WorldExecutor):
        def execute(self, monday, action, key):
            return []  # claims success but records nothing

    rt.executor = Lossy(y.world)
    app = graph.build(rt, InMemorySaver())
    cfg = {"configurable": {"thread_id": "t"}}
    out = app.invoke({"monday": MONDAY.isoformat()}, cfg)
    out = app.invoke(Command(resume={"decision": "approve"}), cfg)  # first pause: over the cap
    assert out["__interrupt__"][0].value["kind"] == "readback_mismatch"


def test_a_quarter_runs_end_to_end_inside_limits():
    y = build_year()
    rt = runtime(y, imagine_runs=30)
    app = graph.build(rt, InMemorySaver())
    j = run_days(y, app, rt, date(2026, 1, 1), date(2026, 3, 31), "fy", owner=lambda p: {"decision": "approve"})
    assert len(j) == 13
    days = y.world.ledger.days()
    assert min(d.cash_end for d in days if d.day >= date(2026, 1, 1)) >= 150_000  # never below the $1,500 floor
