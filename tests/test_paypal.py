import json
from datetime import date

from langgraph.checkpoint.memory import InMemorySaver

from helm import graph
from helm.model import Action, Order, Payout
from helm.paypal.client import PayPalClient
from helm.paypal.executor import PayPalExecutor
from helm.year import build_year, runtime

MONDAY = date(2026, 1, 5)


class FakePayPal:
    """Mimics the sandbox responses seen live on 31 Oct 2026, including duplicate batch refusal."""

    def __init__(self):
        self.batches: set[str] = set()
        self.request_ids: dict[str, dict] = {}
        self.log: list[tuple[str, str]] = []

    def __call__(self, method, url, headers, body):
        path = url.split(".com", 1)[1]
        self.log.append((method, path))
        data = json.loads(body) if body and body[:1] == b"{" else {}
        if path == "/v1/oauth2/token":
            return 200, {"access_token": "TOKEN", "expires_in": 32400}
        if path == "/v1/payments/payouts":
            bid = data["sender_batch_header"]["sender_batch_id"]
            if bid in self.batches:
                return 400, {"name": "USER_BUSINESS_ERROR", "message": "User business error."}
            self.batches.add(bid)
            return 201, {"batch_header": {"payout_batch_id": f"B{len(self.batches):012d}", "batch_status": "PENDING",
                                          "sender_batch_header": data["sender_batch_header"]}}
        if path == "/v2/checkout/orders":
            rid = headers.get("PayPal-Request-Id")
            if rid in self.request_ids:  # PayPal returns the original order for a repeated request id
                return 200, self.request_ids[rid]
            vaulted = "payment_source" in data
            order = {"id": f"O{len(self.request_ids):012d}", "status": "COMPLETED" if vaulted else "CREATED"}
            self.request_ids[rid] = order
            return 201, order
        return 404, {"name": "NOT_FOUND"}


def _executor(storefront=True):
    y = build_year()
    fake = FakePayPal()
    helm_app = PayPalClient("id", "secret", transport=fake)
    store = PayPalClient("sid", "ssecret", transport=fake) if storefront else None
    ex = PayPalExecutor(
        y.world, helm_app,
        affiliate_emails={h: f"{h.strip('@')}@personal.example.com" for h in y.affiliates},
        supplier_emails={"fastfab": "fastfab@business.example.com", "harborwhole": "harbor@business.example.com"},
        storefront=store, vault_id="VAULT-123" if storefront else "",
    )
    return y, ex, fake


def test_payouts_and_vaulted_orders_reach_paypal_and_the_ledger():
    y, ex, fake = _executor()
    action = Action(orders=[Order("fastfab", 60, 9.8, 25.0)], commission_rate=0.1,
                    payouts=[Payout("@pawsandprints", 30.0, "commission"), Payout("@tailwagtips", 20.0, "commission")])
    receipts = ex.execute(MONDAY, action, key="fy:2026-01-05")
    assert [r["kind"] for r in receipts] == ["order", "payout", "payout"]
    assert all(r["new"] and r["paypal_id"] for r in receipts)
    assert sum(1 for m, p in fake.log if p == "/v1/payments/payouts") == 1  # one batch for the week
    kinds = [e.kind for e in y.world.ledger.events if e.day == MONDAY]
    assert kinds.count("purchase") == 1 and kinds.count("payout") == 2


def test_replaying_a_week_never_pays_twice():
    y, ex, fake = _executor()
    action = Action(orders=[Order("fastfab", 60, 9.8, 25.0)], payouts=[Payout("@pawsandprints", 30.0, "commission")])
    ex.execute(MONDAY, action, key="fy:2026-01-05")
    again = ex.execute(MONDAY, action, key="fy:2026-01-05")
    assert not any(r["new"] for r in again)
    assert len(fake.batches) == 1
    assert sum(1 for e in y.world.ledger.events if e.kind in ("purchase", "payout") and e.day == MONDAY) == 2


def test_purchases_are_not_faked_without_a_storefront_and_the_auditor_stops():
    y, ex, fake = _executor(storefront=False)
    receipts = ex.execute(MONDAY, Action(orders=[Order("fastfab", 60, 9.8, 25.0)]), key="k")
    assert receipts[0]["error"] and not receipts[0]["new"]
    assert not any(e.kind == "purchase" for e in y.world.ledger.events if e.day == MONDAY)

    rt = runtime(y, imagine_runs=30)
    rt.executor = ex
    app = graph.build(rt, InMemorySaver())
    out = graph.run_week(app, MONDAY, "t")
    # The first week's plan orders stock, which cannot execute yet, so the read-back pauses the week.
    assert out["proposal"]["orders"]
    assert out["__interrupt__"][0].value["kind"] == "readback_mismatch"
