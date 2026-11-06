"""Platform economics: small cuts and float feed a safety fund, honestly.

The platform makes money the way a neobank does, on a fee per payout, the fee on
an advance, and the float yield on balances it holds. A fixed share of each goes
to the safety fund that backs advances; the rest is platform revenue. This is the
loop you described: make money on cuts, but keep a safe fund that pays creators
even if a borrower defaults. Every number here is deterministic, because these
are exact money movements.

The fund it fills is the same SafetyFund the advance engine caps against, so the
more the platform earns, the more it can safely advance, and the per-borrower and
coverage caps still bound exposure.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .advance import SafetyFund


@dataclass
class PlatformEconomics:
    fund: SafetyFund
    payout_fee_rate: float = 0.02         # fee charged on a payout
    fund_share: float = 0.5               # share of every cut routed to the safety fund
    float_apr: float = 0.04               # yearly yield on balances held
    revenue: float = 0.0                  # the platform's own retained earnings

    def _split(self, cut: float) -> dict:
        cut = round(max(0.0, cut), 2)
        to_fund = round(cut * self.fund_share, 2)
        to_revenue = round(cut - to_fund, 2)
        self.fund.add(to_fund)
        self.revenue = round(self.revenue + to_revenue, 2)
        return {"cut": cut, "to_fund": to_fund, "to_revenue": to_revenue, "fund_balance": self.fund.balance}

    def on_payout(self, amount: float) -> dict:
        """A payout settles; the platform takes a fee, split to fund and revenue."""
        return self._split(float(amount) * self.payout_fee_rate)

    def on_advance_fee(self, fee: float) -> dict:
        """The fee earned on an advance; it backs the fund that took the risk."""
        return self._split(float(fee))

    def on_float(self, balance: float, days: int) -> dict:
        """Yield earned on a balance held for `days`, split to fund and revenue."""
        return self._split(float(balance) * self.float_apr * (days / 365.0))


@dataclass
class UnitEconomics:
    """The real revenue model behind the platform, on the neobank levers: card
    interchange, net interest margin on held balances (yield minus cost of funds),
    fees on payouts, and the spread on advances. It tracks ARPU, LTV and the
    LTV:CAC ratio, the standard viability test (about 3x). Monthly figures.

    Grounded in neobank economics: interchange ~0.2-2%, net interest margin became
    meaningful at 4-5% rates, and the revenue mix has shifted from mostly
    interchange toward net interest and treasury spread.
    """
    interchange_rate: float = 0.015    # on card spend
    float_apr: float = 0.04            # gross yield on balances
    cost_of_funds: float = 0.01        # what holding balances costs us
    payout_fee_rate: float = 0.02
    advance_fee_rate: float = 0.06
    cac_per_creator: float = 20.0      # acquisition cost
    churn_monthly: float = 0.03        # 3%/mo churn -> ~33-month lifetime
    gross_margin: float = 0.80
    creators: int = 0
    rev: dict = field(default_factory=lambda: {"interchange": 0.0, "float_nim": 0.0,
                                               "payout_fees": 0.0, "advance_spread": 0.0})

    def add_creators(self, n: int) -> None:
        self.creators += int(n)

    def record_card_spend(self, volume: float) -> float:
        r = round(float(volume) * self.interchange_rate, 2)
        self.rev["interchange"] = round(self.rev["interchange"] + r, 2)
        return r

    def record_float(self, balance: float) -> float:
        nim = round(float(balance) * (self.float_apr - self.cost_of_funds) / 12.0, 2)  # monthly NIM
        self.rev["float_nim"] = round(self.rev["float_nim"] + nim, 2)
        return nim

    def record_payouts(self, volume: float) -> float:
        r = round(float(volume) * self.payout_fee_rate, 2)
        self.rev["payout_fees"] = round(self.rev["payout_fees"] + r, 2)
        return r

    def record_advances(self, volume: float) -> float:
        r = round(float(volume) * self.advance_fee_rate, 2)
        self.rev["advance_spread"] = round(self.rev["advance_spread"] + r, 2)
        return r

    def monthly_revenue(self) -> float:
        return round(sum(self.rev.values()), 2)

    def revenue_mix(self) -> dict:
        total = self.monthly_revenue() or 1.0
        return {k: round(v / total, 3) for k, v in self.rev.items()}

    def arpu(self) -> float:
        return round(self.monthly_revenue() / self.creators, 2) if self.creators else 0.0

    def lifetime_months(self) -> float:
        return round(1.0 / self.churn_monthly, 1) if self.churn_monthly > 0 else 0.0

    def ltv(self) -> float:
        return round(self.arpu() * self.lifetime_months() * self.gross_margin, 2)

    def ltv_cac(self) -> float:
        return round(self.ltv() / self.cac_per_creator, 2) if self.cac_per_creator else 0.0

    def viable(self) -> bool:
        return self.ltv_cac() >= 3.0       # the standard LTV:CAC viability benchmark
