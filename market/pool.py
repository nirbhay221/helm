"""Pools: several people band together to own an asset or buy in bulk.

Pooling is a capability of any person-account, not a separate class of user. The
same person who sells can also join a pool to co-own an investment position or to
buy in bulk with others. Two things keep it safe and fair, and both are
deterministic, so this obeys the repo's rule: the pool PROPOSES, signatures and
plain math DISPOSE.

  - Every contribution is authorized by the member's own SIGNED mandate (the same
    ES256 intent mandate used for agent-to-agent commerce). The pool can never
    pull more from a member than they signed for, nor spend it outside the
    categories they allowed; a tampered or over-cap mandate is rejected or capped,
    not honoured.
  - The economics are shared by rules with known fairness guarantees. Ownership is
    pro-rata in money contributed, which for the group-buying game lies in the
    CORE (no member or subgroup does better by leaving). The bulk-discount SAVING,
    the surplus the coalition creates by clearing a volume tier, is split by the
    SHAPLEY VALUE, the unique allocation that is efficient (the shares sum to the
    whole saving) and rewards each member by their average marginal contribution
    to reaching the tier.

An investment pool places ONE real fractional order through the paper broker and
splits the units pro-rata, so each member genuinely owns their slice at the live
price. A group buy unlocks a volume discount the members could not reach alone.

Because a pool is coordinated accounts by design, it is exactly what the fraud
linkage engine would flag; the signed per-member mandates are what tell an honest
circle apart from a sybil ring wearing a pool's clothes.

Grounded in the buyer-coalition / group-buying literature (coalition formation and
cost sharing under volume discounts; proportional allocation is core-stable; the
Shapley value splits coalition surplus fairly) and in Google's AP2 signed
mandates, reusing this repo's own `market.mandates`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from math import factorial

from .mandates import verify_credential

# A volume-discount schedule keyed on the pooled quantity. Buying together clears
# tiers a lone buyer never reaches; this is the group-buy "help each other" lever.
DISCOUNT_TIERS = [(1, 0.0), (3, 0.05), (5, 0.10), (10, 0.15), (25, 0.20)]


def discount_rate(total_qty: float, tiers=DISCOUNT_TIERS) -> float:
    """The fraction off unlocked once the pooled quantity reaches a tier. Monotone
    non-decreasing in the pooled quantity, so pooling never hurts."""
    r = 0.0
    for thr, d in tiers:
        if total_qty >= thr:
            r = d
    return r


def _authorize(credential: dict | None, category: str, amount: float) -> tuple[bool, float, bool, str]:
    """Decide what a member's signed mandate actually authorizes for this pool.

    Returns (ok, funded, signed, reason). A verified intent mandate funds up to its
    signed budget for an allowed category; an unsigned contribution is accepted at
    its stated amount in the sandbox but marked unsigned; a tampered or wrong-key
    mandate, or a category the owner did not allow, funds nothing."""
    amount = round(float(amount), 2)
    if amount <= 0:
        return False, 0.0, False, "contribution must be positive"
    if credential is None:
        return True, amount, False, "unsigned (sandbox): accepted at stated amount"
    ok, p, reason = verify_credential(credential)
    if not ok or p.get("type") != "IntentMandate":
        return False, 0.0, False, f"mandate did not verify: {reason}"
    cats = tuple(p.get("allowed_categories") or ())
    if cats and category not in cats:
        return False, 0.0, True, f"category '{category}' is not in the signed mandate"
    cap = float(p.get("max_total", 0.0))
    if cap <= 0:
        return False, 0.0, True, "signed budget is zero"
    funded = round(min(amount, cap), 2)
    reason = ("authorized by signed mandate" if funded + 1e-6 >= amount
              else f"capped to the signed budget {cap:.2f}")
    return True, funded, True, reason


@dataclass
class Member:
    name: str
    requested: float            # what they asked to put in (investment) or wanted to spend (group buy)
    funded: float               # what their mandate actually authorized
    signed: bool                # was it backed by a verified signature
    ok: bool                    # did it count toward the pool
    reason: str


# --- pooled investment: co-own one real position ----------------------------

@dataclass
class InvestmentPool:
    """Several people pool cash to co-own one position. One real fractional order
    buys the whole amount; units are split pro-rata to money each member funded."""
    asset: str = "SPY"
    label: str = "US stocks (S&P 500 ETF)"
    category: str = "stocks"
    members: list = field(default_factory=list)      # Member

    def join(self, name: str, amount: float, credential: dict | None = None) -> Member:
        ok, funded, signed, reason = _authorize(credential, self.category, amount)
        m = Member(name, round(float(amount), 2), funded, signed, ok, reason)
        self.members.append(m)
        return m

    def funded_total(self) -> float:
        return round(sum(m.funded for m in self.members if m.ok), 2)

    def execute(self, broker) -> dict:
        """Place ONE order for the pooled total and split the units pro-rata. The
        broker is the same PaperBroker the solo invest path uses, so with Alpaca
        keys this is a real paper order at the live price."""
        total = self.funded_total()
        fill = broker.buy(self.asset, total) if total > 0 else {
            "price": round(broker.quote(self.asset), 2), "units": 0.0, "routed_to_alpaca": False}
        price = fill["price"]
        total_units = fill["units"]
        allocations = []
        for m in self.members:
            share = (m.funded / total) if (m.ok and total > 0) else 0.0
            allocations.append({
                "member": m.name, "funded": m.funded, "signed": m.signed, "ok": m.ok,
                "share": round(share, 4), "units": round(share * total_units, 6),
                "value": round(share * total_units * price, 2), "reason": m.reason})
        return {
            "asset": self.asset, "label": self.label, "backend": broker.backend,
            "price": price, "routed_to_alpaca": fill.get("routed_to_alpaca", False),
            "funded_total": total, "total_units": round(total_units, 6),
            "members": len([m for m in self.members if m.ok]),
            "allocations": allocations}


# --- group buy: unlock a volume discount together ---------------------------

def shapley_discount_split(demands: dict[str, float], unit_price: float,
                           rate_fn=discount_rate) -> dict[str, float]:
    """Split the total bulk-discount saving by the Shapley value: each member's
    average marginal contribution to the saving across all join orders. Efficient
    (the shares sum to the grand coalition's saving) and symmetric. Exact over
    subsets, which is fine for demo-sized pools."""
    names = list(demands)
    n = len(names)
    if n == 0:
        return {}

    def v(group) -> float:
        q = sum(demands[g] for g in group)
        return q * unit_price * rate_fn(q)

    phi = {m: 0.0 for m in names}
    for m in names:
        rest = [x for x in names if x != m]
        for k in range(len(rest) + 1):
            w = factorial(k) * factorial(n - k - 1) / factorial(n)
            for combo in combinations(rest, k):
                phi[m] += w * (v(set(combo) | {m}) - v(set(combo)))
    return {m: round(phi[m], 2) for m in names}


@dataclass
class GroupBuy:
    """Several people buy the same item together to clear a volume-discount tier
    none could reach alone. Each pays pro-rata of the discounted total; the saving
    is also attributed by the Shapley value so the fairness split is explicit."""
    item: str
    unit_price: float
    category: str = "goods"
    members: list = field(default_factory=list)      # Member, with requested = desired qty
    _qty: dict = field(default_factory=dict)         # name -> funded qty

    def join(self, name: str, qty: float, credential: dict | None = None) -> Member:
        qty = float(qty)
        solo_cost = round(qty * self.unit_price, 2)            # authorize against the worst case (no discount)
        ok, funded_cost, signed, reason = _authorize(credential, self.category, solo_cost)
        funded_qty = round(funded_cost / self.unit_price, 4) if (ok and self.unit_price > 0) else 0.0
        m = Member(name, qty, funded_qty, signed, ok, reason)
        self.members.append(m)
        if ok and funded_qty > 0:
            self._qty[name] = funded_qty
        return m

    def allocate(self) -> dict:
        demands = dict(self._qty)
        pooled_qty = round(sum(demands.values()), 4)
        rate = discount_rate(pooled_qty)
        disc_price = round(self.unit_price * (1.0 - rate), 4)
        total_list = round(pooled_qty * self.unit_price, 2)
        total_paid = round(pooled_qty * disc_price, 2)
        total_saved = round(total_list - total_paid, 2)
        shapley = shapley_discount_split(demands, self.unit_price)
        lines = []
        for m in self.members:
            q = demands.get(m.name, 0.0)
            solo = round(q * self.unit_price, 2)
            pooled_cost = round(q * disc_price, 2)
            lines.append({
                "member": m.name, "qty": q, "signed": m.signed, "ok": m.ok,
                "solo_cost": solo, "pooled_cost": pooled_cost,
                "saving_prorata": round(solo - pooled_cost, 2),
                "saving_shapley": shapley.get(m.name, 0.0), "reason": m.reason})
        return {
            "item": self.item, "unit_price": round(self.unit_price, 2),
            "pooled_qty": pooled_qty, "discount_rate": rate,
            "discounted_unit_price": disc_price, "members": len(demands),
            "total_list": total_list, "total_paid": total_paid, "total_saved": total_saved,
            "lines": lines}
