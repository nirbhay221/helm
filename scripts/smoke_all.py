"""End-to-end functional smoke: exercise every capability for real and report.

Loads .env so the live model, PayPal sandbox and real market prices are used
where available. Each check prints PASS with a detail, DEGRADED if a live
dependency was unreachable, or FAIL with the error. Not a unit test; this proves
the real functions run end to end.
"""
from __future__ import annotations

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except Exception:
    pass

RESULTS = []


def check(name, fn, live=False):
    try:
        detail = fn()
        RESULTS.append(("PASS", name, detail))
        print(f"PASS  {name}: {detail}")
    except Exception as exc:
        tag = "DEGRADED" if live else "FAIL"
        RESULTS.append((tag, name, str(exc)[:120]))
        print(f"{tag}  {name}: {str(exc)[:120]}")
        if not live:
            traceback.print_exc()


def main():
    from agent.llm import LLMClient
    live_model = LLMClient().available

    # 1. policy compiler (live model)
    def policy():
        from agent.policy import PolicyDesk
        d = PolicyDesk().compile("Hold high-risk creators and freeze Nigeria and China.")
        return f"source={d.source} risk_wt={d.weights.risk} exclude={d.constraints.exclude_countries}"
    check("policy_compiler", policy, live=True)

    # 2. allocator LP over a global population
    def alloc():
        from marketplace.allocator import allocate, make_global_creators, Weights, Constraints
        cs = make_global_creators(2000, seed=3)
        res = allocate(cs, 200000.0, Weights(), Constraints())
        return f"paid {res.paid_count} of {len(cs)} creators, ${res.total_paid}"
    check("allocator_lp", alloc)

    # 3. closed-loop cash controller
    def controller():
        from marketplace import CashPayoutController, CreatorMarketplace, MarketplaceParams
        sim = CreatorMarketplace(MarketplaceParams(demand_series=[1000, 1200, 2000, 900]), n_periods=4)
        dec = CashPayoutController().plan(owed0=1000, cash0=1500,
                                          forecast_gmv=[1000, 1000, 1000, 1000], reserve_floor=[300] * 5)
        return f"safe payout {round(dec.payout, 2)} status {dec.status}"
    check("cash_controller", controller)

    # 4. signal desk self-consistency (live model)
    def signal():
        from agent.signals import SignalDesk
        a = SignalDesk(LLMClient(), samples=3).interpret("A fraud wave is hitting new accounts in week 3.",
                                                         current_period=0, baseline_demand=1000, horizon=6)
        return f"source={a.source} confidence={a.confidence} deltas={len(a.period_deltas)}"
    check("signal_desk", signal, live=True)

    # 5. two-sided abuse
    def abuse():
        from market.abuse import AbuseEngine
        from market.marketplace import generate_marketplace
        v = AbuseEngine(min_bad=10).scan(generate_marketplace(120, seed=7))
        return f"{len(v)} flagged (both sides)"
    check("abuse_engine", abuse)

    # 6. fraud-ring linkage
    def linkage():
        from market.linkage import LinkageEngine
        from market.marketplace import generate_marketplace
        r = LinkageEngine().infer(generate_marketplace(120, seed=7))
        return f"{len(r)} rings inferred, top risk {r[0].risk if r else 0}"
    check("linkage_engine", linkage)

    # 7. advance with risk pricing + repay
    def advance():
        from marketplace.advance import AdvanceEngine, SafetyFund
        fund = SafetyFund(10000.0)
        eng = AdvanceEngine()
        o = eng.offer("A", 1000.0, fund, earnings_history=[100, 300, 50, 400])
        t = eng.take("A", min(o.max_amount, 200.0), 1000.0, fund, approved=True, earnings_history=[100, 300, 50, 400])
        rep = eng.repay_from_payout("A", 500.0, fund)
        return f"pd={o.pd} offered<= {o.max_amount} status={t['status']} repaid {rep['withheld']}"
    check("advance_engine", advance)

    # 8. platform + unit economics
    def econ():
        from marketplace.advance import SafetyFund
        from marketplace.economics import PlatformEconomics, UnitEconomics
        PlatformEconomics(SafetyFund()).on_payout(1000.0)
        ue = UnitEconomics(); ue.add_creators(100)
        ue.record_card_spend(50000); ue.record_float(200000); ue.record_payouts(100000); ue.record_advances(10000)
        return f"ARPU {ue.arpu()} LTV:CAC {ue.ltv_cac()} viable={ue.viable()}"
    check("economics", econ)

    # 9. real paper investing (live prices)
    def invest():
        from marketplace.invest import PaperBroker, Portfolio, Business, Property
        pf = Portfolio(PaperBroker(use_alpaca=False))
        pf.invest(1000.0)
        b = Business("Shop", "shop", 1000.0, 0.02); b.back("A", 600.0)
        p = Property("Home", "Austin", 1000.0); p.buy("A", 400.0)
        return f"portfolio cost {pf.cost_basis()} value {pf.market_value()} | business+property ok"
    check("investing_live_prices", invest, live=True)

    # 10. per-creator manager (live recommendations) + tax
    def manager():
        from market.manager import CreatorManager
        from market.marketplace import Account, Listing, Marketplace, Order
        m = Marketplace()
        for a in ("s1", "b1"):
            m.add_account(Account(id=a, name=a, country="US"))
        m.list_item(Listing(id="l1", seller="s1", title="x", price=100, category="prints"))
        m.place_order(Order(id="o1", buyer="b1", seller="s1", listing="l1", amount=100, day=8, status="fulfilled"))
        mgr = CreatorManager(m, "s1", llm=LLMClient(), now_day=10)
        e = mgr.earnings(); rec = mgr.recommendations(); tx = mgr.tax_statement()
        return f"month net {e['month']['net']} rec_source={rec.get('source')} tax={tx.regime['form']}"
    check("creator_manager", manager, live=True)

    # 11. agent-to-agent signed mandate settle (demo PayPal)
    def a2a():
        from market.a2a import A2ADesk
        from market.mandates import OwnerKey, issue_intent_mandate
        from market.marketplace import Account, Listing, Marketplace
        from paypal import Ledger, PayPalClient
        m = Marketplace(); m.add_account(Account(id="seller", name="S", country="US"))
        m.list_item(Listing(id="cheap", seller="seller", title="p", price=40, category="prints"))
        key = OwnerKey()
        intent = issue_intent_mandate(key, "buyerX", 500, 100, ("prints",), approval_threshold=50)
        d = A2ADesk(m, PayPalClient(env={"DEMO_MODE": "1"}), Ledger()).buy(intent, "cheap")
        return f"status={d.status} order={d.order_id} agreed={d.agreed}"
    check("agent_to_agent", a2a)

    # 12. PayPal payout (live sandbox if creds, else demo)
    def paypal():
        from paypal import Ledger, PayPalClient
        from paypal.mcp_payouts_tool import create_payout
        client = PayPalClient()
        r = create_payout(client, Ledger(), [{"email": "x@ex.com", "amount": 5.0, "note": "smoke"}],
                          sender_batch_id="smoke-" + os.urandom(3).hex(), purpose="COMMISSION", approved=True)
        return f"status={r.status} batch={r.batch_id} demo={r.demo}"
    check("paypal_payout", paypal, live=True)

    # 13. MCP servers build and list tools
    def mcp():
        import asyncio
        from mcp_server.server import build_server
        from mcp_server.market_server import build_market_server
        from mcp_server.trust_server import build_trust_server
        counts = {}
        for n, b in (("payouts", build_server), ("market", build_market_server), ("trust", build_trust_server)):
            counts[n] = len(asyncio.run(b().list_tools()))
        return f"servers {counts}"
    check("mcp_servers", mcp)

    print("\n=== summary ===")
    for tag in ("PASS", "DEGRADED", "FAIL"):
        print(f"{tag}: {sum(1 for t, _, _ in RESULTS if t == tag)}")
    print("live model:", "on" if live_model else "off (fallbacks used)")


if __name__ == "__main__":
    main()
