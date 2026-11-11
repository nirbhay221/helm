"""Tollgate: cross-border withholding on partner payouts.

For recipients outside the operator's jurisdiction, a share of the payout must be
withheld and remitted, and the filing data prepared. This is reuse of established
tax logic, not core: a default non-resident rate with treaty-reduced rates where a
treaty applies, and the net paid to the recipient. The numbers are illustrative
defaults for the demo, not tax advice.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from marketplace.allocator import DEFAULT_WITHHOLDING, TREATY_WITHHOLDING

DEFAULT_NRA_RATE = DEFAULT_WITHHOLDING  # default US non-resident withholding
# One treaty table for the whole system: the allocator plans with the same rates Tollgate
# withholds, so a creator's planned net and paid net can never disagree.
TREATY_RATES = {**TREATY_WITHHOLDING, "FR": 0.0}


@dataclass
class WithholdingLine:
    recipient: str
    country: str
    gross: float
    rate: float
    withheld: float
    net: float


@dataclass
class TollgateResult:
    lines: list = field(default_factory=list)
    total_gross: float = 0.0
    total_withheld: float = 0.0
    total_net: float = 0.0

    def filing_rows(self) -> list[dict]:
        """1042-S-style rows for the amounts withheld (what gets remitted/filed)."""
        return [
            {"recipient": L.recipient, "country": L.country,
             "gross_income": L.gross, "withholding_rate": L.rate,
             "tax_withheld": L.withheld}
            for L in self.lines if L.withheld > 0
        ]


def withhold(payouts: list[dict], home_country: str = "US") -> TollgateResult:
    """payouts: [{recipient, amount, country}]. Returns per-line withholding."""
    lines: list[WithholdingLine] = []
    for p in payouts:
        gross = float(p.get("amount", 0.0))
        country = (p.get("country") or home_country).upper()
        if country == home_country:
            rate = 0.0
        else:
            rate = TREATY_RATES.get(country, DEFAULT_NRA_RATE)
        withheld = round(gross * rate, 2)
        lines.append(WithholdingLine(
            recipient=p.get("recipient") or p.get("email", "?"),
            country=country, gross=round(gross, 2), rate=rate,
            withheld=withheld, net=round(gross - withheld, 2)))

    return TollgateResult(
        lines=lines,
        total_gross=round(sum(L.gross for L in lines), 2),
        total_withheld=round(sum(L.withheld for L in lines), 2),
        total_net=round(sum(L.net for L in lines), 2),
    )
