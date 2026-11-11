"""Predictive profit-and-loss for the platform, on real credit-risk mechanics.

The economics module only *accumulated realized fees*. It had no forward view and no
loss side, so it could not answer the question the operator actually needs: given what
we expect to earn and what we expect to lose, how much can we safely do? This module
adds that.

Revenue is projected from the conformal demand forecast (so it carries a band, not a
point). Losses are modelled the way a lender does: Expected Loss = PD x LGD x EAD per
advance, summed over the book, plus an expected chargeback loss on volume. Risk-adjusted
profit is expected revenue minus expected loss minus the cost of capital, reported with
a low/high band from the forecast interval. The fund is provisioned to the lifetime
expected credit loss (a CECL-style coverage multiple), and RAROC measures whether the
advance book earns its risk.

Grounded in Expected Loss = PD x LGD x EAD, CECL lifetime expected credit loss
provisioning, and RAROC risk-adjusted pricing. Deterministic; the uncertainty comes
from the conformal forecaster, not from randomness here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .economics import UnitEconomics


def expected_loss(pd: float, lgd: float, ead: float) -> float:
    """Expected Loss = PD x LGD x EAD (probability of default x loss given default x
    exposure at default). The atom of every provisioning and risk-pricing decision."""
    return round(max(0.0, pd) * max(0.0, lgd) * max(0.0, ead), 2)


@dataclass
class LoanExposure:
    creator: str
    pd: float                       # probability of default (from the scorecard)
    ead: float                      # exposure at default = current outstanding
    lgd: float = 0.55               # loss given default; unsecured consumer ~55-65%
    fee_rate: Optional[float] = None  # the fee this loan was priced at (risk-priced); None = flat rate

    def el(self) -> float:
        return expected_loss(self.pd, self.lgd, self.ead)


def risk_adjusted_price(pd: float, lgd: float, target_return: float = 0.03,
                        floor: float = 0.02) -> float:
    """Price an advance to cover its expected loss plus a target return (RAROC pricing):
    fee_rate = PD x LGD + target_return, never below a floor. A riskier borrower pays
    more because their expected loss is higher, not by an arbitrary premium."""
    el_rate = max(0.0, pd) * max(0.0, lgd)
    return round(max(floor, el_rate + target_return), 4)


@dataclass
class PlatformPnL:
    econ: UnitEconomics = field(default_factory=UnitEconomics)
    lgd: float = 0.55
    chargeback_rate: float = 0.004     # expected chargeback/fraud loss on GMV (~0.4%)
    cost_of_capital_monthly: float = 0.01
    coverage_ratio: float = 1.2        # CECL-style provision multiple on expected loss

    def _revenue_on(self, gmv: float, book_ead: float) -> float:
        """Project the revenue levers onto a GMV figure and the current advance book."""
        interchange = gmv * self.econ.interchange_rate
        payout_fees = gmv * self.econ.payout_fee_rate
        float_nim = gmv * (self.econ.float_apr - self.econ.cost_of_funds) / 12.0   # monthly NIM on held balances
        advance_spread = book_ead * self.econ.advance_fee_rate
        return interchange + payout_fees + float_nim + advance_spread

    def _spread(self, book) -> float:
        """Fee income on the advance book, each loan at the rate it was actually priced at."""
        return sum(l.ead * (l.fee_rate if l.fee_rate is not None else self.econ.advance_fee_rate)
                   for l in book)

    def forecast(self, gmv_steps: List[dict], advance_book: Optional[List[LoanExposure]] = None,
                 fund_balance: float = 0.0) -> dict:
        """Forward P&L. gmv_steps are the conformal forecast dicts ({mean, low, high});
        advance_book is the current exposures. Returns expected revenue (with a band),
        expected loss, risk-adjusted profit (with a band), the CECL provision, RAROC,
        and whether the fund covers the provision."""
        book = advance_book or []
        book_ead = round(sum(l.ead for l in book), 2)
        gmv_mean = sum(s["mean"] for s in gmv_steps)
        gmv_low = sum(s.get("low", s["mean"]) for s in gmv_steps)
        gmv_high = sum((s["high"] if s.get("high") is not None else s["mean"]) for s in gmv_steps)

        flat = book_ead * self.econ.advance_fee_rate
        priced = self._spread(book)
        rev_mean = self._revenue_on(gmv_mean, book_ead) - flat + priced
        rev_low = self._revenue_on(gmv_low, book_ead) - flat + priced
        rev_high = self._revenue_on(gmv_high, book_ead) - flat + priced

        advance_el = round(sum(l.el() for l in book), 2)
        chargeback_el = round(gmv_mean * self.chargeback_rate, 2)
        el = round(advance_el + chargeback_el, 2)
        coc = round(book_ead * self.cost_of_capital_monthly, 2)

        profit_mean = round(rev_mean - el - coc, 2)
        profit_low = round(rev_low - el - coc, 2)       # worst-case revenue, same expected loss
        profit_high = round(rev_high - el - coc, 2)

        provision = round(el * self.coverage_ratio, 2)   # lifetime expected credit loss provision
        # RAROC on the advance book: (spread earned - expected loss) / capital at risk
        spread = round(priced, 2)
        raroc = round((spread - advance_el) / book_ead, 4) if book_ead > 0 else None

        return {
            "gmv_forecast": {"mean": round(gmv_mean, 2), "low": round(gmv_low, 2), "high": round(gmv_high, 2)},
            "expected_revenue": {"mean": round(rev_mean, 2), "low": round(rev_low, 2), "high": round(rev_high, 2)},
            "expected_loss": {"total": el, "advances": advance_el, "chargebacks": chargeback_el,
                              "lgd": self.lgd, "chargeback_rate": self.chargeback_rate},
            "cost_of_capital": coc,
            "risk_adjusted_profit": {"mean": profit_mean, "low": profit_low, "high": profit_high},
            "provision_needed": provision,
            "fund_balance": round(fund_balance, 2),
            "fund_covers_provision": bool(fund_balance >= provision),
            "raroc": raroc,
            "book_exposure": book_ead,
            "method": "revenue from conformal GMV forecast; loss = sum(PD x LGD x EAD) + chargeback EL; "
                      "provision = coverage x EL (CECL-style); RAROC = (spread - EL)/exposure",
        }
