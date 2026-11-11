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
US_STATE_LOW = 600.0                    # several states (MD, MA, VA, VT, DC, ...) report from $600
BACKUP_WITHHOLDING = 0.24              # 24% withheld if the payee gives no valid TIN
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
    quarters: list = field(default_factory=list)
    summary: str = ""


def regime_for(country: str, gross: float, transactions: int, fees: float,
               has_tin: bool = True, quarters: list | None = None) -> dict:
    """The reporting regime for a creator given their gross, transaction count and
    fees. Pure function, so it serves the full statement, the endpoint and the MCP
    tool. `quarters` (optional) carries a per-quarter breakdown for DAC7."""
    c = (country or "").upper()
    if c == "US":
        g_thr, t_thr = US_FED_THRESHOLD
        issues = gross > g_thr and transactions > t_thr
        out = {"form": "US 1099-K", "box_1a_gross": round(gross, 2), "transactions": transactions,
               "federal_threshold": "over $20,000 and over 200 transactions",
               "reportable_federally": issues,
               "reportable_in_low_threshold_states": gross >= US_STATE_LOW,
               "state_threshold": "$600 in several states (MD, MA, VA, VT, DC and others)",
               "net_after_platform_fees": round(gross - fees, 2),
               "note": "1099-K reports GROSS; you still deduct fees and refunds and pay quarterly estimated tax yourself."}
        if not has_tin:
            out["backup_withholding_24pct"] = round(gross * BACKUP_WITHHOLDING, 2)
            out["note"] += " No valid TIN on file, so 24% backup withholding applies until you provide one."
        return out
    if c in EU_DAC7 or c == "GB":
        n_thr, v_thr = DAC7_DEMINIMIS
        exempt = transactions < n_thr and gross < v_thr
        out = {"form": "DAC7" if c != "GB" else "UK platform reporting (DAC7-equivalent)",
               "total_consideration": round(gross, 2), "activities": transactions,
               "fees_withheld": round(fees, 2), "de_minimis_exempt": exempt,
               "note": "Exempt only if under 30 activities AND under 2,000 euros; otherwise the platform reports you each quarter."}
        if quarters:
            out["quarterly"] = quarters      # DAC7 is reported per calendar quarter
        return out
    return {"form": "earnings statement", "gross": round(gross, 2), "transactions": transactions,
            "net_after_platform_fees": round(gross - fees, 2),
            "note": "No marketplace reporting form here; keep this for your own filing."}


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

    # per-quarter breakdown (the sim's 0-120 day window maps to four 30-day quarters),
    # which DAC7 requires reported separately.
    qbuckets: dict = {}
    for o in sold:
        q = min(3, max(0, int(o.day) // 30))
        agg = qbuckets.setdefault(q, {"consideration": 0.0, "activities": 0})
        agg["consideration"] += o.amount
        agg["activities"] += 1
    quarters = [{"quarter": f"Q{q + 1}",
                 "consideration": round(qbuckets.get(q, {}).get("consideration", 0.0), 2),
                 "activities": qbuckets.get(q, {}).get("activities", 0)} for q in range(4)]

    regime = regime_for(country, gross, count, fees, quarters=quarters)

    summary = (f"For the {period}, you sold {count} times for ${gross:,.2f} gross, "
               f"paid ${fees:,.2f} in platform fees, had {len(refunded)} refunds (${refunds_amount:,.2f}), "
               f"netting ${net:,.2f}. Regime: {regime['form']}.")
    return TaxStatement(creator_id, c, period, gross, count, fees, refunds_amount,
                        len(refunded), net, regime, quarters, summary)
