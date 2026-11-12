"""A personal AI money manager for each creator.

Every creator gets their own manager that does three things from real data:
  1. shows earnings this week, month and year, net of the platform fee;
  2. recommends what to sell or list, from the creator's own best categories, what
     the marketplace is buying right now, and the next festival that lifts demand;
  3. proposes money moves (take a safe advance, invest a surplus, save), each of
     which the CREATOR must approve before anything happens.

The numbers are computed deterministically from the marketplace; the model only
writes the plain-English briefing on top, and if there is no model key a scripted
briefing is used. The manager never moves money on its own: proposals carry
needs_approval, and the advance offer is already bounded by the safety fund.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass

from agent.llm import LLMClient
from marketplace.advance import AdvanceEngine, SafetyFund

from .marketplace import Marketplace

# a light festival calendar on the simulator's 0-120 day timeline; each festival
# lifts demand for certain creator categories.
FESTIVALS = [
    {"name": "New Year", "day": 5, "categories": ["merch", "templates"]},
    {"name": "Valentine's", "day": 20, "categories": ["prints", "presets"]},
    {"name": "Back to School", "day": 55, "categories": ["ebooks", "templates"]},
    {"name": "Diwali", "day": 85, "categories": ["prints", "merch"]},
    {"name": "Black Friday", "day": 100, "categories": ["merch", "beats", "presets"]},
    {"name": "Christmas", "day": 115, "categories": ["prints", "merch", "ebooks"]},
]


def _dollars(x):
    """Earnings facts as the creator reads them: $1,234 rather than 1234.0."""
    if isinstance(x, dict):
        return {k: _dollars(v) for k, v in x.items()}
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return f"${x:,.0f}"
    return x


def _plain(p: dict) -> dict:
    out = {"option": p["action"].replace("_", " ")}
    for k, v in p.items():
        if k in ("up_to", "suggested") and v is not None:
            out[k.replace("_", " ")] = f"${float(v):,.0f}"
        elif k == "fee_rate" and v is not None:
            out["fee"] = f"{float(v) * 100:.0f}%"
        elif k == "pd" and v is not None:
            out["chance of not repaying"] = f"{float(v) * 100:.0f}%"
    return out


@dataclass
class CreatorManager:
    market: Marketplace
    creator_id: str
    llm: LLMClient = None
    now_day: int = None
    take_rate: float = 0.10

    def __post_init__(self):
        if self.llm is None:
            self.llm = LLMClient()
        if self.now_day is None:
            self.now_day = max((o.day for o in self.market.orders), default=0)

    # --- earnings -----------------------------------------------------------
    def _good_sales(self):
        return [o for o in self.market.orders_as_seller(self.creator_id)
                if o.status not in ("returned", "charged_back")]

    def earnings(self) -> dict:
        sales = self._good_sales()

        def window(days: int) -> dict:
            gross = sum(o.amount for o in sales if 0 <= self.now_day - o.day <= days)
            return {"gross": round(gross, 2), "net": round(gross * (1 - self.take_rate), 2)}

        return {"week": window(7), "month": window(30), "year": window(400)}

    def earnings_series(self, bucket: int = 7) -> list:
        """Net earnings bucketed over time (weekly by default), the history the
        advance engine reads to score this creator's default risk."""
        sales = self._good_sales()
        if not sales:
            return []
        # count weeks back from today, so the newest bucket is a full week and not a partial
        # one that would read as a collapse in earnings
        buckets: dict = {}
        for o in sales:
            b = max(0, int(self.now_day) - int(o.day)) // bucket
            buckets[b] = buckets.get(b, 0.0) + o.amount * (1 - self.take_rate)
        return [round(buckets.get(b, 0.0), 2) for b in range(max(buckets), -1, -1)]

    # --- recommendations ----------------------------------------------------
    def _cat_of(self, order) -> str:
        lst = self.market.listings.get(order.listing)
        return lst.category if lst else ""

    def top_categories(self) -> list[str]:
        c = Counter(self._cat_of(o) for o in self._good_sales() if self._cat_of(o))
        return [k for k, _ in c.most_common(3)]

    def trending(self) -> list[str]:
        recent = [o for o in self.market.orders
                  if 0 <= self.now_day - o.day <= 14 and o.status not in ("returned", "charged_back")]
        c = Counter(self._cat_of(o) for o in recent if self._cat_of(o))
        return [k for k, _ in c.most_common(3)]

    def upcoming_festival(self) -> dict:
        d = self.now_day % 120
        ahead = [f for f in FESTIVALS if f["day"] >= d]
        return (ahead or FESTIVALS)[0]

    def forecast(self) -> dict:
        """Where this creator's weekly net earnings are heading, by exponential
        smoothing with a trend (Holt) over their own history. Lets the recommender
        look forward, not just at what already sold."""
        from marketplace.models import holt_winters
        return holt_winters(self.earnings_series(bucket=7), horizon=4)

    def recommendations(self) -> dict:
        # The SIGNALS are facts, computed deterministically. The RECOMMENDATION,
        # the judgment of what to do about them, is the model's and varies run to
        # run. The model never invents a category; it reasons over these inputs.
        mine, hot, fest = self.top_categories(), self.trending(), self.upcoming_festival()
        fc = self.forecast()
        base = {"your_best": mine, "trending_now": hot, "next_festival": fest["name"],
                "festival_lifts": fest["categories"],
                "earnings_trend": fc["direction"], "projected_next_week_net": fc["next"],
                "momentum_pct": fc["pct_change"]}
        if self.llm.available:
            try:
                ai = self._ai_recommend(base)
                base.update(ai)
                base["source"] = "model"
                return base
            except Exception:
                pass
        focus = [c for c in fest["categories"] if c in hot] or fest["categories"]
        trend_line = {"up": f"Your earnings are trending up, about ${fc['next']:,.0f} projected next week. ",
                      "down": f"Your earnings are softening, about ${fc['next']:,.0f} projected next week, so lean in now. ",
                      "flat": ""}[fc["direction"]]
        base.update({"suggested_focus": focus, "source": "fallback",
                     "text": (f"{trend_line}"
                              f"Your strongest categories are {', '.join(mine) or 'not established yet'}. "
                              f"The marketplace is buying {', '.join(hot) or 'little right now'}. "
                              f"{fest['name']} is coming, which lifts {', '.join(fest['categories'])}. "
                              f"Lean into {', '.join(focus)} next.")})
        return base

    def _ai_recommend(self, facts: dict) -> dict:
        allowed = set(facts["your_best"]) | set(facts["trending_now"]) | set(facts["festival_lifts"])
        try:
            from market.knowledge import ground
            grounding = "\n\n" + ground("creator earnings forecast sell categories viability advance tax")
        except Exception:
            grounding = ""
        msg = self.llm.chat(
            messages=[{"role": "system", "content":
                       "You advise a creator what to list or make next. Reason over the facts: their "
                       "best-selling categories, what the marketplace is buying now, the next festival "
                       "and the categories it lifts, and their earnings forecast (earnings_trend and "
                       "projected_next_week_net from exponential smoothing). If the trend is down, urge "
                       "acting now; if up, suggest scaling the winners. Reply ONLY as JSON: "
                       '{"suggested_focus": ["category", ...], "text": "one or two sentences"}. '
                       "Use only categories that appear in the facts." + grounding},
                      {"role": "user", "content": json.dumps(facts)}],
            temperature=0.7, max_tokens=200)
        raw = (msg or {}).get("content") or ""
        start, end = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[start:end + 1]) if start >= 0 and end > start else {}
        focus = [c for c in data.get("suggested_focus", []) if c in allowed]
        return {"suggested_focus": focus or facts["festival_lifts"],
                "text": str(data.get("text", "")).strip()[:300] or "Lean into the categories above."}

    # --- approval-gated money proposals -------------------------------------
    def proposals(self, fund: SafetyFund, engine: AdvanceEngine) -> list[dict]:
        month_net = self.earnings()["month"]["net"]
        offer = engine.offer(self.creator_id, proven_earnings=month_net, fund=fund,
                             earnings_history=self.earnings_series())
        out = []
        if offer.eligible and offer.max_amount > 0:
            out.append({"action": "take_advance", "up_to": offer.max_amount,
                        "fee_rate": offer.fee_rate, "pd": offer.pd,
                        "why": offer.reason, "needs_approval": True})
        if month_net > 0:
            out.append({"action": "invest_surplus", "suggested": round(month_net * 0.3, 2),
                        "why": "put a slice of this month's net to work at live market prices",
                        "needs_approval": True})
        out.append({"action": "save", "suggested": round(month_net * 0.2, 2),
                    "why": "keep a cushion in your balance", "needs_approval": True})
        return out

    # --- tax statement ------------------------------------------------------
    def tax_statement(self, period: str = "year"):
        from marketplace.tax import build_statement
        acc = self.market.accounts.get(self.creator_id)
        country = acc.country if acc else "US"
        return build_statement(self.market, self.creator_id, country,
                               fee_rate=self.take_rate, period=period)

    # --- the plain-English briefing -----------------------------------------
    def briefing(self, fund: SafetyFund | None = None, engine: AdvanceEngine | None = None,
                 advance: dict | None = None) -> str:
        """`advance` is the live offer exactly as Get paid early prices it, so the two never disagree."""
        fund = fund or SafetyFund(balance=0.0)
        engine = engine or AdvanceEngine()
        e, rec = self.earnings(), self.recommendations()
        props = self.proposals(fund, engine)
        if advance is not None:
            props = [p for p in props if p["action"] != "take_advance"]
            if advance.get("eligible") and advance.get("offer"):
                props.insert(0, {"action": "take_advance", "up_to": advance["offer"], "fee_rate": advance.get("fee_rate"),
                                 "pd": advance.get("pd"), "needs_approval": True})
        facts = {"earnings": _dollars(e), "recommendations": rec, "options": [_plain(p) for p in props]}
        if self.llm.available:
            try:
                msg = self.llm.chat(
                    messages=[{"role": "system", "content":
                               "You are a creator's money manager. Write 3 short sentences from these facts: "
                               "how the business is doing, what to make more of, and the best money option. "
                               "No greeting, no preamble, no sign-off. Use the numbers exactly as written "
                               "(dollars like $1,234, percents like 24%); never write raw decimals. Never "
                               "invent a number."},
                              {"role": "user", "content": json.dumps(facts)}],
                    temperature=0.5, max_tokens=220)
                txt = (msg or {}).get("content")
                if txt:
                    return txt.strip()
            except Exception:
                pass
        return (f"This month you netted ${e['month']['net']:,.0f} (week ${e['week']['net']:,.0f}, "
                f"year ${e['year']['net']:,.0f}). {rec['text']} "
                f"You have {len(props)} options waiting, each needs your approval.")
