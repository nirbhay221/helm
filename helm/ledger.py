"""The event-sourced daily ledger.

Every fact that changes stock or money is an append-only event dated to the day, with money
in integer cents. The daily table, and every week, month and year total, is a projection
rebuilt from the events, so totals at every level agree to the cent by construction.
Events can carry the PayPal transaction ID that proves them.
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date

from helm.calendar import month_key, week_key

# Event kinds and their effect. Flows are summed over a period; stocks are read at period end.
KINDS = {
    "demand",     # units customers wanted (units)
    "sale",       # units sold (units) and revenue (cents)
    "hold",       # PayPal holds part of revenue (cents) until release_on
    "release",    # PayPal releases a hold (cents)
    "purchase",   # units ordered from a supplier (units), cost paid (cents)
    "arrival",    # units received into stock (units)
    "commission", # affiliate commission accrued (cents)
    "payout",     # commission paid out through PayPal Payouts (cents)
    "opening",    # opening stock (units) and opening cash (cents)
}


@dataclass(frozen=True)
class Event:
    day: date
    kind: str
    units: int = 0
    cents: int = 0
    ref: str = ""  # supplier, receiver, or other counterparty
    paypal_id: str = ""
    release_on: date | None = None
    idempotency_key: str = ""

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"unknown event kind {self.kind}")


@dataclass
class Day:
    day: date
    demand: int = 0
    sold: int = 0
    lost: int = 0
    revenue: int = 0
    held: int = 0
    released: int = 0
    purchased_units: int = 0
    purchase_cost: int = 0
    arrived: int = 0
    commission: int = 0
    paid_out: int = 0
    stock_end: int = 0  # units on hand at end of day
    cash_end: int = 0  # spendable cents at end of day
    held_end: int = 0  # cents PayPal is holding at end of day


FLOWS = ("demand", "sold", "lost", "revenue", "held", "released", "purchased_units",
         "purchase_cost", "arrived", "commission", "paid_out")
STOCKS = ("stock_end", "cash_end", "held_end")


@dataclass
class Ledger:
    events: list[Event] = field(default_factory=list)
    _keys: set[str] = field(default_factory=set)

    def append(self, e: Event) -> bool:
        """Append an event. An event whose idempotency key was already seen is ignored (returns False)."""
        if e.idempotency_key:
            if e.idempotency_key in self._keys:
                return False
            self._keys.add(e.idempotency_key)
        if self.events and e.day < self.events[-1].day:
            raise ValueError("events must be appended in date order")
        self.events.append(e)
        return True

    def has_key(self, key: str) -> bool:
        return key in self._keys

    def days(self) -> list[Day]:
        by_day: dict[date, Day] = {}
        stock = cash = held = 0
        for e in self.events:
            d = by_day.get(e.day)
            if d is None:
                d = by_day[e.day] = Day(e.day)
            if e.kind == "opening":
                stock += e.units
                cash += e.cents
            elif e.kind == "demand":
                d.demand += e.units
            elif e.kind == "sale":
                d.sold += e.units
                d.revenue += e.cents
                stock -= e.units
                cash += e.cents
            elif e.kind == "hold":
                d.held += e.cents
                cash -= e.cents
                held += e.cents
            elif e.kind == "release":
                d.released += e.cents
                cash += e.cents
                held -= e.cents
            elif e.kind == "purchase":
                d.purchased_units += e.units
                d.purchase_cost += e.cents
                cash -= e.cents
            elif e.kind == "arrival":
                d.arrived += e.units
                stock += e.units
            elif e.kind == "commission":
                d.commission += e.cents
            elif e.kind == "payout":
                d.paid_out += e.cents
                cash -= e.cents
            d.stock_end, d.cash_end, d.held_end = stock, cash, held
        for d in by_day.values():
            d.lost = d.demand - d.sold
        return [by_day[k] for k in sorted(by_day)]

    def rollup(self, level: str) -> dict[str, dict[str, int]]:
        """Totals per week ("2026-W11"), month ("2026-03") or year ("2026"), summed from days."""
        keyf = {"week": week_key, "month": month_key, "year": lambda d: f"{d.year:04d}"}[level]
        out: dict[str, dict[str, int]] = defaultdict(lambda: {f: 0 for f in FLOWS})
        for d in self.days():
            row = out[keyf(d.day)]
            for f in FLOWS:
                row[f] += getattr(d, f)
            for s in STOCKS:
                row[s] = getattr(d, s)  # days are in order, so the last one wins
        return dict(out)

    # Persistence: the ledger is a plain append-only table, so a restarted process rebuilds it exactly.
    def save(self, path: str) -> None:
        con = sqlite3.connect(path)
        con.execute("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, body TEXT NOT NULL)")
        have = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        rows = [(json.dumps(asdict(e), default=str),) for e in self.events[have:]]
        con.executemany("INSERT INTO events (body) VALUES (?)", rows)
        con.commit()
        con.close()

    @classmethod
    def load(cls, path: str) -> "Ledger":
        con = sqlite3.connect(path)
        con.execute("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, body TEXT NOT NULL)")
        led = cls()
        for (body,) in con.execute("SELECT body FROM events ORDER BY seq"):
            raw = json.loads(body)
            raw["day"] = date.fromisoformat(raw["day"])
            raw["release_on"] = date.fromisoformat(raw["release_on"]) if raw["release_on"] else None
            led.append(Event(**raw))
        con.close()
        return led
