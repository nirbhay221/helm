"""Safe advances against future earnings, capped so no one default sinks the pool.

A creator can take cash now against earnings they have not been paid yet, repaid
automatically out of their future payouts. This is PayPal Working Capital's model
(an advance repaid as a percentage of future revenue). What makes it safe, and
genuinely novel inside a creator treasury, is a hard concentration cap taken from
bank regulation: no single creator may be advanced more than a small slice of the
shared safety fund (the RBI / Basel Large Exposure idea, a single borrower capped
at about 20% of capital), so one borrower's collapse cannot wipe out everyone
else. The advance is bounded by the SMALLER of what the creator has earned and
what the fund can safely expose to one borrower.

Every advance needs human approval; the engine never releases on its own. All
accounting is real; no real lending happens (that needs a license), so this
models the mechanism and its safety, not a live loan book.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from statistics import fmean, pstdev


def _heuristic_pd(history) -> float:
    """The original closed-form score, kept as a fallback when numpy or the fitted
    model is unavailable. Volatility plus a thin-file penalty, bounded [3%, 60%]."""
    xs = [float(x) for x in (history or []) if x is not None]
    if not xs:
        return 0.50
    mean = fmean(xs)
    if mean <= 0:
        return 0.60
    cv = (pstdev(xs) / mean) if len(xs) > 1 else 0.5
    thin = max(0.0, (6 - len(xs)) / 6.0)
    pd = 0.05 + 0.25 * min(1.0, cv) + 0.15 * thin
    return round(min(0.60, max(0.03, pd)), 3)


def _pd_features(history):
    """Observable risk features from a payout history, oriented so that a larger
    value always means more risk: income volatility, a downward trend, a low income
    floor, weak recent income, and a thin file."""
    import numpy as np
    xs = [float(x) for x in (history or []) if x is not None]
    n = len(xs)
    if n == 0:
        return None
    arr = np.asarray(xs, dtype=float)
    mean = float(arr.mean())
    if mean <= 0:
        return None
    cv = float(arr.std() / mean) if n > 1 else 0.5
    slope = float(np.polyfit(np.arange(n), arr, 1)[0] / mean) if n > 1 else 0.0
    floor = float(arr.min() / mean)
    recency = float(xs[-1] / mean)
    thin = max(0.0, (6 - n) / 6.0)
    # risk-oriented: high cv, negative trend, low floor, low recency, thin file
    return [cv, -slope, 1.0 - floor, 1.0 - recency, thin]


_PD_MODEL = None


def _pd_model():
    """A logistic PD scorecard fit once to a simulated advance book. There are no
    real defaults to learn from yet, so the training set is generated from a known
    default-generating process (volatility, trend and file-thinness drive default);
    the model learns to recover default risk from the OBSERVABLE features above.
    Swapping in real repay/default outcomes later means changing only this function.
    Deterministic: fixed seed, fixed iterations."""
    global _PD_MODEL
    if _PD_MODEL is not None:
        return _PD_MODEL
    import numpy as np
    from .models import LogisticModel
    rng = np.random.default_rng(42)
    X, y = [], []
    for _ in range(4000):
        n = int(rng.integers(1, 13))
        mean = float(rng.uniform(200, 5000))
        cv_true = float(rng.uniform(0.03, 1.2))
        trend_true = float(rng.normal(0.0, 0.14))          # per-period growth rate
        hist = [max(0.0, mean * (1 + trend_true * t) * (1 + rng.normal(0, cv_true)))
                for t in range(n)]
        feats = _pd_features(hist)
        if feats is None:
            continue
        thin = max(0.0, (6 - n) / 6.0)
        z = -2.0 + 3.2 * cv_true - 5.5 * trend_true + 1.4 * thin   # latent default logit
        default = 1.0 if rng.random() < 1.0 / (1.0 + np.exp(-z)) else 0.0
        X.append(feats)
        y.append(default)
    _PD_MODEL = LogisticModel(l2=1.0, lr=0.3, iters=4000).fit(X, y)
    return _PD_MODEL


def default_probability(history) -> float:
    """A creator's probability of default, scored by the fitted logistic scorecard
    over their own payout history (alternative-data, thin-file friendly). Falls back
    to the closed-form heuristic if the model cannot run. Bounded to a sane [3%, 60%]."""
    try:
        feats = _pd_features(history)
        if feats is None:
            return 0.50 if not history else 0.60
        pd = _pd_model().predict_proba(feats)
        return round(min(0.60, max(0.03, float(pd))), 3)
    except Exception:
        return _heuristic_pd(history)


@dataclass
class SafetyFund:
    """The shared reserve that backs advances, fed by platform fees and float."""
    balance: float = 0.0

    def add(self, amount: float) -> float:
        self.balance = round(self.balance + max(0.0, float(amount)), 2)
        return self.balance


@dataclass
class AdvanceOffer:
    creator: str
    eligible: bool
    max_amount: float
    fee_rate: float
    repay_pct: float
    binding_cap: str           # "earnings" | "fund-concentration" | "already-borrowing" | "none"
    reason: str
    pd: float = 0.0            # the creator's estimated probability of default


@dataclass
class Advance:
    creator: str
    principal: float
    fee: float
    outstanding: float
    repay_pct: float


@dataclass
class AdvanceEngine:
    advance_rate: float = 0.80        # up to 80% of proven (unpaid) earnings
    concentration: float = 0.20       # per-borrower cap: no one above 20% of the fund (large-exposure rule)
    loss_rate: float = 0.10           # assumed default rate on the advance book (MCA data ~10-15%)
    coverage_ratio: float = 1.2       # the fund must cover 1.2x expected losses (RateSetter provision-fund idea)
    fee_rate: float = 0.06            # base fee on the advance (creator-friendly end of RBF)
    pd_fee_premium: float = 0.30      # risk premium added to the fee, scaled by the creator's PD
    repay_pct: float = 0.25           # share of each future payout withheld to repay
    loans: dict = field(default_factory=dict)      # creator -> Advance

    def total_outstanding(self) -> float:
        return round(sum(l.outstanding for l in self.loans.values()), 2)

    def portfolio_capacity(self, fund: SafetyFund) -> float:
        """How much more the whole book can grow while the fund still covers expected
        losses at the target coverage ratio. fund >= coverage x loss_rate x book."""
        if self.loss_rate <= 0:
            return float("inf")
        backable = fund.balance / (self.coverage_ratio * self.loss_rate)
        return max(0.0, round(backable - self.total_outstanding(), 2))

    def offer(self, creator: str, proven_earnings: float, fund: SafetyFund,
              earnings_history=None) -> AdvanceOffer:
        if creator in self.loans:
            return AdvanceOffer(creator, False, 0.0, self.fee_rate, self.repay_pct,
                                "already-borrowing", "An advance is already outstanding for this creator.", 0.0)
        # per-creator risk: a riskier creator is lent a smaller share of earnings and
        # pays a higher fee. The caps below are unchanged, this prices WITHIN them.
        pd = default_probability(earnings_history) if earnings_history else 0.0
        eff_rate = self.advance_rate * (1.0 - pd)
        fee = round(self.fee_rate + self.pd_fee_premium * pd, 4)
        caps = {
            "earnings": eff_rate * max(0.0, float(proven_earnings)),
            "fund-concentration": self.concentration * max(0.0, fund.balance),
            "fund-coverage": self.portfolio_capacity(fund),
        }
        binding = min(caps, key=caps.get)
        max_amount = round(max(0.0, caps[binding]), 2)
        risk_note = (f" Risk-priced: PD {int(pd * 100)}%, so up to {int(eff_rate * 100)}% of earnings "
                     f"at a {fee * 100:.1f}% fee." if earnings_history else "")
        reason = (f"Capped by the smallest of: {int(eff_rate * 100)}% of proven earnings "
                  f"(${caps['earnings']:,.0f}), {int(self.concentration * 100)}% of the fund per borrower "
                  f"(${caps['fund-concentration']:,.0f}), and what the fund can still cover at "
                  f"{self.coverage_ratio}x expected losses (${caps['fund-coverage']:,.0f}); "
                  f"the {binding} limit binds.{risk_note}")
        return AdvanceOffer(creator, max_amount > 0, max_amount, fee,
                            self.repay_pct, binding if max_amount > 0 else "none", reason, pd)

    def take(self, creator: str, amount: float, proven_earnings: float,
             fund: SafetyFund, approved: bool = False, earnings_history=None) -> dict:
        offer = self.offer(creator, proven_earnings, fund, earnings_history)
        if not approved:
            return {"status": "needs_approval", "offer": asdict(offer)}
        if not offer.eligible or float(amount) > offer.max_amount + 1e-6 or float(amount) <= 0:
            return {"status": "rejected",
                    "reason": f"requested {amount} exceeds the safe cap {offer.max_amount} or is not eligible",
                    "offer": asdict(offer)}
        amount = round(float(amount), 2)
        fee = round(amount * offer.fee_rate, 2)          # risk-priced fee from the offer
        self.loans[creator] = Advance(creator, amount, fee, round(amount + fee, 2), self.repay_pct)
        fund.balance = round(fund.balance - amount, 2)       # the fund fronts the cash
        return {"status": "advanced", "amount": amount, "fee": fee,
                "outstanding": round(amount + fee, 2), "repay_pct": self.repay_pct,
                "fund_after": fund.balance}

    def repay_from_payout(self, creator: str, payout_amount: float, fund: SafetyFund) -> dict:
        ln = self.loans.get(creator)
        payout_amount = float(payout_amount)
        if not ln or ln.outstanding <= 0:
            return {"withheld": 0.0, "net": round(payout_amount, 2), "outstanding": 0.0}
        withheld = round(min(ln.outstanding, payout_amount * ln.repay_pct), 2)
        ln.outstanding = round(ln.outstanding - withheld, 2)
        fund.balance = round(fund.balance + withheld, 2)      # repayment returns to the fund
        remaining = ln.outstanding
        if ln.outstanding <= 1e-6:
            del self.loans[creator]
            remaining = 0.0
        return {"withheld": withheld, "net": round(payout_amount - withheld, 2), "outstanding": remaining}
