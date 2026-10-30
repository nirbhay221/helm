import sqlite3
from datetime import date

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from helm import graph, planning
from helm.year import build_year, run_year_days, runtime


def test_month_plan_weeks_add_up_and_partial_weeks_count():
    y = build_year()
    p = planning.planner("2026-04", 600, y.budget, 8.6, 0.1, 2400)
    assert sum(p.weekly_units.values()) == 600
    assert "2026-W14" in p.weekly_units  # Wed 1 Apr starts mid-week; its partial week is kept
    assert not planning.check_plan(p, opening_cash=20_000, cash_floor=1_500, low_units=450, price=24.0)


def test_plan_check_catches_a_cash_floor_breach():
    y = build_year()
    p = planning.planner("2026-04", 600, y.budget, 8.6, 0.1, 2400, slack=10.0)  # absurd purchase budget
    assert planning.check_plan(p, opening_cash=2_000, cash_floor=1_500, low_units=450, price=24.0)


def test_strategist_never_promises_more_than_the_lever_can_deliver():
    y = build_year()
    st = planning.standing(y.world.ledger, y.budget, date(2026, 3, 31), weekly_forecast=60.0, price_cents=2400)
    targets = planning.strategist(st, y.budget, date(2026, 4, 1), max_lift=0.06)
    for k, units in targets.items():
        assert units <= round(y.budget.months[k].units * 1.06) + 1


def test_standing_outlook_adds_actuals_and_forecast():
    y = build_year()
    st = planning.standing(y.world.ledger, y.budget, date(2025, 12, 31), weekly_forecast=120.0, price_cents=2400)
    assert st.ytd_units == 0
    assert abs(st.outlook_units - 120 / 7 * 365) < 30


def test_day_graph_pauses_for_monthly_signoff_and_resumes_after_restart(tmp_path):
    y = build_year()
    rt = runtime(y, imagine_runs=30)
    db = str(tmp_path / "cp.db")
    cfg = {"configurable": {"thread_id": "fy2026"}}
    app = graph.build_day(rt, SqliteSaver(sqlite3.connect(db, check_same_thread=False)))
    out = app.invoke({"day": "2026-01-01"}, cfg)
    ask = out["__interrupt__"][0].value
    assert ask["kind"] == "approve_month" and ask["month"] == "2026-01"
    assert "2026-01" not in rt.month_plans

    app2 = graph.build_day(rt, SqliteSaver(sqlite3.connect(db, check_same_thread=False)))
    done = app2.invoke(Command(resume={"decision": "approve"}), cfg)
    assert done["ran"] == ["monthly"]
    assert rt.month_plans["2026-01"]["units"] == ask["plan"]["units"]


def test_rejected_month_plan_is_not_used():
    y = build_year()
    rt = runtime(y, imagine_runs=30)
    app = graph.build_day(rt, InMemorySaver())
    graph.run_day(app, date(2026, 1, 1), "t", owner=lambda p: {"decision": "reject"})
    assert "2026-01" not in rt.month_plans


def test_week_belongs_to_the_month_holding_its_thursday():
    y = build_year()
    rt = runtime(y, imagine_runs=30)
    rt.month_plans["2026-07"] = {"purchase_budget": 5000.0, "commission_budget": 500.0, "units": 513}
    lim = rt.envelope(date(2026, 6, 29))  # Mon 29 Jun, Thu 2 Jul: July's budget applies
    assert lim.max_spend_per_week == min(y.limits.max_spend_per_week, 5500.0)


def test_signed_off_month_plan_steers_the_weekly_sales_targets():
    y = build_year()
    rt = runtime(y, imagine_runs=30)
    rt.month_plans["2026-02"] = {"units": 800, "purchase_budget": 9000.0, "commission_budget": 900.0}
    rt.sync_plan()
    k = (date(2026, 2, 9) - rt.first_monday).days // 7  # a week fully inside February
    assert rt.brain.business.sales_target[k] > rt.base_plan.sales_target[k]


def test_a_full_quarter_through_the_day_graph():
    y = build_year()
    rt = runtime(y, imagine_runs=30)
    app = graph.build_day(rt, InMemorySaver())
    asks = []
    out = run_year_days(y, app, date(2026, 1, 1), date(2026, 3, 31), "fy",
                        owner=lambda p: (asks.append(p["kind"]), {"decision": "approve"})[1])
    assert asks.count("approve_month") == 3
    assert sum(1 for r in out if "weekly" in r["ran"]) == 13
    assert set(rt.month_plans) == {"2026-01", "2026-02", "2026-03"}


def test_daily_tripwire_replans_midweek_when_a_stockout_is_coming():
    from helm.ledger import Event
    y = build_year()
    rt = runtime(y, imagine_runs=30)
    app = graph.build_day(rt, InMemorySaver())
    rt.month_plans["2026-01"] = {"units": 556, "purchase_budget": 9000.0, "commission_budget": 900.0}
    # Wednesday with almost no stock and nothing arriving: Helm must not wait for Monday.
    y.world.ledger.append(Event(date(2025, 12, 31), "sale", units=y.world.stock() - 5, cents=0))
    y.world.pipeline.clear()
    out = graph.run_day(app, date(2026, 1, 7), "t", owner=lambda p: {"decision": "approve"})
    assert out["ran"] == ["tripwire:stockout"]
    assert out["week"]["orders"]
