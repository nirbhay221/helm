"""The single source of truth for the dashboard: the creator-marketplace story.

Runs the whole system once and returns a JSON-serializable payload the charts
read: the GMV variance (a viral spike the flat plan never saw), cash against the
floor-plus-reserve line, how fast creators get paid, the payout frontier (Helm
versus the naive extremes), a sample of real-shaped payout batches to creators,
and the payout engine (fair split, fraud hardening, cross-border withholding).
"""
from __future__ import annotations

import functools

from arms.payout_engine import Contribution, Party, run_payout_engine
from marketplace import (CashPayoutController, CashPayoutParams, Creator,
                         CreatorMarketplace, MarketplaceParams, helm_payout_policy,
                         pay_all_now_policy, pay_monthly_policy, run_marketplace,
                         run_marketplace_live)
from paypal import Ledger, PayPalClient

# a viral spike, then a collapse while the spike's chargebacks land
GMV = [1000]*5 + [1800, 2600, 3000, 2600, 1800] + [350, 300, 350, 450, 600] + [900]*9

CREATORS = [
    Creator("Ava", "ava-creator@personal.example.com", weight=3.0),
    Creator("Ben", "ben-creator@personal.example.com", weight=2.0),
    Creator("Cy", "cy-creator@personal.example.com", weight=1.0),
]

# cited context for the headline (see the research in the README)
CONTEXT = {"market_size_b": 314, "creators_m": 207, "late_pct": 87}


def _params() -> MarketplaceParams:
    return MarketplaceParams(
        baseline_gmv=1000.0, take_rate=0.12, refund_rate=0.05, chargeback_rate=0.12,
        chargeback_lag=2, chargeback_window=4, reserve_rate=0.30, cash_floor=300.0,
        init_cash=900.0, demand_series=[float(x) for x in GMV])


def _controller() -> CashPayoutController:
    return CashPayoutController(CashPayoutParams(
        horizon=8, take_rate=0.12, refund_rate=0.05, chargeback_rate=0.12))


def _sim() -> CreatorMarketplace:
    return CreatorMarketplace(_params(), seed=7, n_periods=len(GMV))


def _payout_engine_panel() -> dict:
    client, ledger = PayPalClient(env={"DEMO_MODE": "1"}), Ledger()
    pe = run_payout_engine(
        1000.0,
        [Contribution("Ava", {"c1", "c2", "c3", "c4"}),
         Contribution("Ben", {"c3", "c4", "c5"}),
         Contribution("Cy", {"c5", "c6"})],
        [Party("Ava", 400), Party("Ben", 300), Party("Cy", 150)],
        Party("Sybil", 500, cluster="Sybil", honest=False),
        {"Ava": {"email": "ava@ex.com", "country": "US"},
         "Ben": {"email": "ben@ex.com", "country": "IN"},
         "Cy": {"email": "cy@ex.com", "country": "BR"},
         "Sybil": {"email": "z@ex.com", "country": "US"}},
        client, ledger, sender_batch_id="dash-payengine", purpose="COMMISSION",
        fail_items=set(), approved=True)
    return {
        "bulwark": {
            "naive_cheater_take": pe.bulwark.naive_cheater_take,
            "hardened_cheater_take": pe.bulwark.hardened_cheater_take,
            "honest_share": pe.bulwark.honest_cheater_share,
            "hardening_applied": pe.bulwark.hardening_applied,
            "defeated": pe.bulwark.defeated,
        },
        "clearwright_ok": pe.clearwright.ok,
        "tollgate": {"gross": pe.tollgate.total_gross,
                     "withheld": pe.tollgate.total_withheld,
                     "net": pe.tollgate.total_net},
        "keystone": {"status": pe.keystone.status, "batch_id": pe.keystone.batch_id,
                     "conserved": pe.keystone.conserved},
    }


def build_dashboard_data() -> dict:
    floor = _params().cash_floor

    # Helm run, keeping the per-period trajectory for the charts
    sim_h = _sim()
    helm_metrics = run_marketplace(sim_h, helm_payout_policy(_controller()))
    hist = sim_h.history
    periods = [o.period for o in hist]

    gmv = {
        "periods": periods,
        "forecast": [o.forecast_gmv for o in hist],
        "actual": [o.gmv for o in hist],
    }
    cashflow = {
        "periods": periods,
        "cash": [o.cash for o in hist],
        "floor_plus_reserve": [round(floor + o.reserve_required, 2) for o in hist],
        "owed": [o.owed for o in hist],
    }
    creator_wait = {"periods": periods, "oldest_wait": [o.oldest_wait for o in hist]}

    # the payout frontier: Helm vs the naive extremes
    pay_all = run_marketplace(_sim(), pay_all_now_policy())
    monthly = run_marketplace(_sim(), pay_monthly_policy(4))

    def _m(m):
        return {"avg_wait": m.avg_wait, "reserve_breaches": m.reserve_breaches,
                "reserve_shortfall": m.reserve_shortfall, "cash_floor_breaches": m.cash_floor_breaches,
                "total_paid": m.total_paid}
    frontier = {"pay_all": _m(pay_all), "monthly": _m(monthly), "helm": _m(helm_metrics)}

    # a sample of real-shaped payout batches to creators (demo mode, no network)
    client, ledger = PayPalClient(env={"DEMO_MODE": "1"}), Ledger()
    runs = run_marketplace_live(_sim(), _controller(), CREATORS, client, ledger)
    payout_runs = [{
        "period": r.period, "total": r.payout_total, "batch_id": r.batch_id,
        "status": r.status,
        "recipients": [{"creator": x["creator"], "amount": x["amount"]} for x in r.recipients],
    } for r in runs[:8]]

    return {
        "context": CONTEXT,
        "gmv": gmv,
        "cashflow": cashflow,
        "creator_wait": creator_wait,
        "frontier": frontier,
        "payout_runs": payout_runs,
        "payout_engine": _payout_engine_panel(),
        "headline": {
            "creators_paid_total": round(sum(r.payout_total for r in runs), 2),
            "helm_avg_wait": helm_metrics.avg_wait,
            "shortfall_helm": helm_metrics.reserve_shortfall,
            "shortfall_pay_all": pay_all.reserve_shortfall,
            "floor_breaches_helm": helm_metrics.cash_floor_breaches,
        },
    }


@functools.lru_cache(maxsize=1)
def dashboard_data_cached() -> dict:
    """The dashboard payload, computed once and reused (a full system run). The
    inputs are fixed, so the result is identical every time; the server warms
    this at startup and serves the cached payload thereafter."""
    return build_dashboard_data()
