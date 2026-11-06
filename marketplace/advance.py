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


def default_probability(history) -> float:
    """Estimate a creator's probability of default from their own payout history,
    the thin-file alternative-data approach: steadier, longer income is safer.
    Driven by income volatility (coefficient of variation) and a thin-file penalty
    when there are few periods to judge. Bounded to a sane [3%, 60%]."""
    xs = [float(x) for x in (history or []) if x is not None]
    if not xs:
        return 0.50
    mean = fmean(xs)
    if mean <= 0:
        return 0.60
    cv = (pstdev(xs) / mean) if len(xs) > 1 else 0.5      # income volatility
    thin = max(0.0, (6 - len(xs)) / 6.0)                   # fewer than 6 periods seen
    pd = 0.05 + 0.25 * min(1.0, cv) + 0.15 * thin          # base + volatility + thin-file
    return round(min(0.60, max(0.03, pd)), 3)


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
