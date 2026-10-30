"""Shared domain types: suppliers, the business plan, the state Helm steers, and the moves it makes."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Tier:
    min_qty: int
    unit_price: float


@dataclass(frozen=True)
class Supplier:
    id: str
    name: str
    tiers: tuple[Tier, ...]  # all-units discount: the whole order gets the price of the tier it reaches
    lead_weeks: int
    capacity: int
    fixed_fee: float = 0.0

    @property
    def moq(self) -> int:
        return self.tiers[0].min_qty

    def unit_price(self, qty: int) -> float:
        price = None
        for tier in sorted(self.tiers, key=lambda t: t.min_qty):
            if qty >= tier.min_qty:
                price = tier.unit_price
        if price is None:
            raise ValueError(f"{qty} is below {self.id}'s minimum order of {self.moq}")
        return price

    def order_cost(self, qty: int) -> float:
        return qty * self.unit_price(qty) + self.fixed_fee


@dataclass(frozen=True)
class BusinessPlan:
    """The course Helm steers to: weekly targets set by the owner's forecast or budget."""

    inventory_target: tuple[float, ...]
    cash_target: tuple[float, ...]
    cash_floor: float
    price: float
    sales_target: tuple[float, ...] = ()  # units the budget expects sold each week; empty means not tracked


@dataclass(frozen=True)
class Limits:
    """The owner's envelope. Inside it Helm acts alone; outside it Helm asks."""

    max_spend_per_week: float
    commission_min: float
    commission_max: float
    allowed_suppliers: frozenset[str]
    max_payout_per_affiliate: float = 500.0


@dataclass
class State:
    week: int
    on_hand: float
    cash: float  # spendable PayPal balance
    commission_rate: float
    pipeline: list[tuple[int, float, str]] = field(default_factory=list)  # (arrival week, qty, supplier)
    held: list[tuple[int, float]] = field(default_factory=list)  # (release week, amount) held by PayPal
    demand_history: list[float] = field(default_factory=list)
    revenue_history: list[float] = field(default_factory=list)

    @property
    def cash_held(self) -> float:
        return sum(a for _, a in self.held)

    def arrivals(self, week: int) -> float:
        return sum(q for w, q, _ in self.pipeline if w == week)

    def releases(self, week: int) -> float:
        return sum(a for w, a in self.held if w == week)

    def copy(self) -> "State":
        return State(
            self.week, self.on_hand, self.cash, self.commission_rate,
            list(self.pipeline), list(self.held), list(self.demand_history), list(self.revenue_history),
        )


@dataclass(frozen=True)
class Order:
    supplier_id: str
    qty: int
    unit_price: float
    fixed_fee: float = 0.0

    @property
    def cost(self) -> float:
        return self.qty * self.unit_price + self.fixed_fee


@dataclass(frozen=True)
class Payout:
    receiver: str
    amount: float
    purpose: str  # PayPal Payouts allows commissions, rebates, rewards, incentives


@dataclass
class Action:
    orders: list[Order] = field(default_factory=list)
    commission_rate: float | None = None
    payouts: list[Payout] = field(default_factory=list)

    @property
    def spend(self) -> float:
        return sum(o.cost for o in self.orders) + sum(p.amount for p in self.payouts)
