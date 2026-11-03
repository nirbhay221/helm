"""The dashboard's single source of truth: Helm's agent running money-out.

Runs the operator agent over a creator-marketplace scenario and returns a
JSON-serializable payload the charts read: the ETS forecast against actual GMV
with its uncertainty band, cash held above the floor-plus-reserve line, the risk
posture the agent chose each cycle (raised when a fraud signal lands), the
agent's per-cycle decision journal (who it paid, who it held, guardrail
overrides), the payout frontier versus the naive policies, and the payout engine.

Built with the scripted (keyless) operator so the page needs no network or model
call at startup; the live model path is scripts/demo_operator.py.
"""
from __future__ import annotations

import functools

from agent import LLMClient, MoneyOutOperator, OperatorCreator, OperatorTools, SignalDesk
from arms.payout_engine import Contribution, Party, run_payout_engine
from marketplace import (CashPayoutController, CashPayoutParams, CreatorMarketplace,
                         MarketplaceParams, helm_payout_policy, pay_all_now_policy,
                         pay_monthly_policy, run_marketplace)
from paypal import Ledger, PayPalClient

GMV = [1000]*4 + [1800, 2600, 3000, 2200, 1500] + [400, 350, 500, 900, 900, 900]
SIGNAL_CYCLE = 5
SIGNALS = {SIGNAL_CYCLE: "Risk alert: a fraud and chargeback wave is hitting brand-new viral "
                         "accounts in this category this week."}
CONTEXT = {"market_size_b": 314, "creators_m": 207, "late_pct": 87}


def _params() -> MarketplaceParams:
    return MarketplaceParams(
        baseline_gmv=1000.0, take_rate=0.12, refund_rate=0.05, chargeback_rate=0.12,
        chargeback_lag=2, chargeback_window=4, reserve_rate=0.30, cash_floor=300.0,
        init_cash=900.0, demand_series=[float(x) for x in GMV])


def _controller() -> CashPayoutController:
    return CashPayoutController(CashPayoutParams(
        horizon=8, take_rate=0.12, refund_rate=0.05, chargeback_rate=0.12))


def _creators() -> list[OperatorCreator]:
    return [
        OperatorCreator("Ava", "ava@ex.com", 3.0, context="long-tenured, steady, clean history"),
        OperatorCreator("Ben", "ben@ex.com", 2.0, context="brand new this week, just went viral"),
        OperatorCreator("Cy", "cy@ex.com", 1.0, context="mid-tier, a year on platform"),
    ]


def _payout_engine_panel() -> dict:
    client, ledger = PayPalClient(env={"DEMO_MODE": "1"}), Ledger()
    pe = run_payout_engine(
        1000.0,
        [Contribution("Ava", {"c1", "c2", "c3", "c4"}), Contribution("Ben", {"c3", "c4", "c5"}),
         Contribution("Cy", {"c5", "c6"})],
        [Party("Ava", 400), Party("Ben", 300), Party("Cy", 150)],
        Party("Sybil", 500, cluster="Sybil", honest=False),
        {"Ava": {"email": "ava@ex.com", "country": "US"}, "Ben": {"email": "ben@ex.com", "country": "IN"},
         "Cy": {"email": "cy@ex.com", "country": "BR"}, "Sybil": {"email": "z@ex.com", "country": "US"}},
        client, ledger, sender_batch_id="dash-payengine", purpose="COMMISSION",
        fail_items=set(), approved=True)
    return {
        "bulwark": {"naive_cheater_take": pe.bulwark.naive_cheater_take,
                    "hardened_cheater_take": pe.bulwark.hardened_cheater_take,
                    "honest_share": pe.bulwark.honest_cheater_share,
                    "hardening_applied": pe.bulwark.hardening_applied, "defeated": pe.bulwark.defeated},
        "clearwright_ok": pe.clearwright.ok,
        "tollgate": {"gross": pe.tollgate.total_gross, "withheld": pe.tollgate.total_withheld,
                     "net": pe.tollgate.total_net},
        "keystone": {"status": pe.keystone.status, "batch_id": pe.keystone.batch_id,
                     "conserved": pe.keystone.conserved}}


def _frontier() -> dict:
    def _m(m):
        return {"avg_wait": m.avg_wait, "reserve_shortfall": m.reserve_shortfall,
                "cash_floor_breaches": m.cash_floor_breaches}
    return {
        "pay_all": _m(run_marketplace(CreatorMarketplace(_params(), seed=7, n_periods=len(GMV)), pay_all_now_policy())),
        "monthly": _m(run_marketplace(CreatorMarketplace(_params(), seed=7, n_periods=len(GMV)), pay_monthly_policy(4))),
        "helm": _m(run_marketplace(CreatorMarketplace(_params(), seed=7, n_periods=len(GMV)), helm_payout_policy(_controller()))),
    }


def build_dashboard_data() -> dict:
    sim = CreatorMarketplace(_params(), seed=7, n_periods=len(GMV))
    tools = OperatorTools(sim, _controller(), _creators(),
                          SignalDesk(LLMClient(env={})), PayPalClient(env={"DEMO_MODE": "1"}), Ledger())
    operator = MoneyOutOperator(tools, LLMClient(env={}), signal_schedule=SIGNALS)
    records = operator.run(len(GMV))

    hist = {o.period: o for o in sim.history}
    periods = [r.period for r in records]
    floor = _params().cash_floor

    gmv = {
        "periods": periods,
        "actual": [round(hist[p].gmv, 2) if p in hist else None for p in periods],
        "forecast": [r.facts.get("forecast_gmv_next") for r in records],
        "upper": [round((r.facts.get("forecast_gmv_next") or 0) + 1.65 * (r.facts.get("forecast_sigma_next") or 0), 2) for r in records],
        "lower": [round(max(0.0, (r.facts.get("forecast_gmv_next") or 0) - 1.65 * (r.facts.get("forecast_sigma_next") or 0)), 2) for r in records],
    }
    cashflow = {
        "periods": periods,
        "cash": [r.facts.get("cash_after") for r in records],
        "floor_plus_reserve": [round(floor + (hist[p].reserve_required if p in hist else 0), 2) for p in periods],
    }
    risk = {"periods": periods, "risk_multiplier": [r.facts.get("risk_multiplier") for r in records],
            "signal_cycle": SIGNAL_CYCLE}

    roster = [c.name for c in _creators()]
    journal = []
    recoup_seen = False
    for r in records:
        paid = r.facts.get("paid") or []
        paid_names = {p["creator"] for p in paid}
        snap = r.facts.get("creators_snapshot") or []
        held = [c["creator"] for c in snap if c.get("owed", 0) > 0.01 and c["creator"] not in paid_names]
        if any(c.get("recoup_due", 0) > 0.01 for c in snap):
            recoup_seen = True
        journal.append({
            "period": r.period,
            "signal": SIGNALS.get(r.period, ""),
            "forecast": r.facts.get("forecast_gmv_next"),
            "sigma": r.facts.get("forecast_sigma_next"),
            "risk_multiplier": r.facts.get("risk_multiplier"),
            "safe_release": r.facts.get("safe_release_total"),
            "paid": [{"creator": p["creator"], "amount": p["amount"]} for p in paid],
            "held": held,
            "status": r.facts.get("status"),
            "batch_id": r.facts.get("batch_id"),
            "overrides": r.facts.get("guardrail_overrides", []),
        })

    creators_paid_total = round(sum(r.facts.get("paid_total") or 0 for r in records), 2)
    caution_raised = sum(1 for r in records if (r.facts.get("risk_multiplier") or 1.0) > 1.0)

    return {
        "context": CONTEXT,
        "gmv": gmv,
        "cashflow": cashflow,
        "risk": risk,
        "journal": journal,
        "frontier": _frontier(),
        "payout_engine": _payout_engine_panel(),
        "headline": {
            "creators_paid_total": creators_paid_total,
            "cycles": len(records),
            "caution_raised": caution_raised,
            "recoupment_used": recoup_seen,
        },
    }


@functools.lru_cache(maxsize=1)
def dashboard_data_cached() -> dict:
    """The dashboard payload, computed once and reused (a full agent run). Fixed
    inputs, so identical every time; the server warms it at startup."""
    return build_dashboard_data()
