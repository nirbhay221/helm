"""A creator earnings-and-tax statement, generated from real marketplace activity.

The platform knows exactly what a creator sold, so it can hand them the statement
a tax authority expects, which today most creators assemble by hand. Two regimes:

  US, Form 1099-K: reports GROSS payments (Box 1a) and the transaction count, with
  no subtraction of fees or refunds. Federal threshold for 2025 to 2026 is over
  $20,000 AND over 200 transactions (OBBBA restored it); some states set it as low
  as $600. We compute the gross and count and say whether a 1099-K would issue.

  EU, DAC7: the platform reports each seller's total consideration, the number of
  activities, and the fees it withheld. A goods seller is exempt only if BOTH under
  30 activities AND under 2,000 euros in the period.

The numbers are deterministic, because a tax figure must be exact, not an AI guess.
The creator's manager writes the plain-English explanation on top.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from market.marketplace import Marketplace

EU_DAC7 = {"DE", "FR", "ES", "IT", "NL", "IE", "BE", "AT", "PT", "PL", "SE", "FI", "DK"}
US_FED_THRESHOLD = (20000.0, 200)      # (gross, transactions) for 2025-2026
DAC7_DEMINIMIS = (30, 2000.0)          # under 30 activities AND under EUR 2000 -> exempt


@dataclass
class TaxStatement:
    creator: str
    country: str
    period: str
    gross: float
    transactions: int
    fees: float
    refunds_amount: float
    refunds_count: int
    net: float
    regime: dict = field(default_factory=dict)
    summary: str = ""


def build_statement(market: Marketplace, creator_id: str, country: str,
                    fee_rate: float = 0.10, period: str = "year") -> TaxStatement:
    sold = [o for o in market.orders_as_seller(creator_id) if o.status == "fulfilled"]
    refunded = [o for o in market.orders_as_seller(creator_id)
                if o.status in ("returned", "charged_back")]
    gross = round(sum(o.amount for o in sold), 2)        # 1099-K Box 1a is gross, no deductions
    count = len(sold)
    fees = round(gross * fee_rate, 2)
    refunds_amount = round(sum(o.amount for o in refunded), 2)
    net = round(gross - fees, 2)

    c = (country or "").upper()
    if c == "US":
        g_thr, t_thr = US_FED_THRESHOLD
        issues = gross > g_thr and count > t_thr
        regime = {"form": "US 1099-K", "box_1a_gross": gross, "transactions": count,
                  "federal_threshold": "over $20,000 and over 200 transactions",
                  "reportable_federally": issues,
                  "note": "Some states report from $600; 1099-K is gross, you still deduct fees and refunds yourself."}
    elif c in EU_DAC7 or c == "GB":
        n_thr, v_thr = DAC7_DEMINIMIS
        exempt = count < n_thr and gross < v_thr
        regime = {"form": "DAC7" if c != "GB" else "UK platform reporting (DAC7-equivalent)",
                  "total_consideration": gross, "activities": count, "fees_withheld": fees,
                  "de_minimis_exempt": exempt,
                  "note": "Exempt only if under 30 activities and under 2,000 euros; otherwise the platform reports you."}
    else:
        regime = {"form": "earnings statement", "gross": gross, "transactions": count,
                  "note": "No marketplace reporting form here; keep this for your own filing."}

    summary = (f"For the {period}, you sold {count} times for ${gross:,.2f} gross, "
               f"paid ${fees:,.2f} in platform fees, had {len(refunded)} refunds (${refunds_amount:,.2f}), "
               f"netting ${net:,.2f}. Regime: {regime['form']}.")
    return TaxStatement(creator_id, c, period, gross, count, fees, refunds_amount,
                        len(refunded), net, regime, summary)
