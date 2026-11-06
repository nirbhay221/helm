"""Customers as real agents: each is a small LLM that decides for itself.

The hellhole we are closing is a deterministic world. Before, the marketplace was
seeded data and the fraud was planted. Here every customer is an autonomous agent
with its own balance, inventory and persona, and each cycle it CHOOSES what to do,
list an item, buy one, return one, or hold, from its own state. The market's
activity and its abuse emerge from those choices, non-deterministically, instead
of being scripted. This is the agent-based market the 2026 literature uses
(TruthMarketTwin arXiv 2605.10059; AgenticPay arXiv 2602.06008; the LLM
data-marketplace sim arXiv 2511.13233).

The deterministic pieces stay where they belong: the agent only proposes an
action, and the Marketplace executes it under plain rules (you cannot buy your own
listing, spend more than your balance, or return an order that was not yours). The
world is agentic; the bookkeeping is not.

With a model key each agent genuinely decides; with no key a stochastic fallback
keeps the simulation running so it is testable offline.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from agent.llm import LLMClient

from .marketplace import Account, Listing, Marketplace, Order

_CATS = ["prints", "presets", "beats", "ebooks", "merch", "templates"]

# a spread of personas; the last two behave badly, but by their OWN choices, not
# by planted orders, so the abuse engine must catch emergent behaviour.
PERSONAS = [
    ("steady maker", "You are a reliable creator. You list items at fair prices, buy occasionally, and almost never return."),
    ("prolific seller", "You list a lot of items and rarely buy. You want sales volume."),
    ("bargain buyer", "You mostly buy cheap items from others and list little. You return only genuinely bad goods."),
    ("cautious saver", "You sell a little, spend little, and prefer to hold your balance."),
    ("serial returner", "You buy often and then return most of what you buy to get the goods for free. You rarely sell."),
    ("bad seller", "You list items cheaply and ship poor quality, so buyers who buy from you often end up returning."),
]

CHOOSE_ACTION_TOOL = {
    "type": "function",
    "function": {
        "name": "choose_action",
        "description": ("Choose ONE action for this cycle as this marketplace member. "
                        "list = put a new item up for sale; buy = buy one listing (not your own); "
                        "return = return one item you recently bought; hold = do nothing."),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "buy", "return", "hold"]},
                "title": {"type": "string", "description": "for list: a short item title"},
                "price": {"type": "number", "description": "for list: price 5 to 120"},
                "category": {"type": "string", "enum": _CATS, "description": "for list"},
                "listing_id": {"type": "string", "description": "for buy: the listing to buy"},
                "order_id": {"type": "string", "description": "for return: the order to return"},
                "reason": {"type": "string", "description": "one short phrase why"},
            },
            "required": ["action"],
        },
    },
}


@dataclass
class CustomerAgent:
    account: Account
    persona: str
    behavior: str
    balance: float = 500.0
    llm: LLMClient = field(default_factory=LLMClient)
    memory: list = field(default_factory=list)      # recency-ordered log of what happened
    reflection: str = ""                            # a periodic higher-level lesson

    def decide(self, m: Marketplace, rng) -> dict:
        if self.llm.available:
            try:
                return self._decide_llm(m)
            except Exception:
                pass
        return self._decide_fallback(m, rng)

    def remember(self, event: str, cap: int = 8) -> None:
        self.memory.append(event)
        if len(self.memory) > cap:
            self.memory = self.memory[-cap:]            # keep the most recent (recency)

    def reflect(self) -> None:
        """Form one short lesson from recent memory that should steer what comes
        next, the reflection step from Generative Agents. Model-written when a key
        is present, a simple heuristic otherwise."""
        if not self.memory:
            return
        if self.llm.available:
            try:
                msg = self.llm.chat(
                    messages=[{"role": "system", "content":
                               "You are a marketplace member. In ONE short sentence, state the lesson "
                               "from your recent activity that should guide what you do next."},
                              {"role": "user", "content": "Recent: " + "; ".join(self.memory[-6:])}],
                    temperature=0.6, max_tokens=60)
                txt = (msg or {}).get("content")
                if txt:
                    self.reflection = txt.strip()[:160]
                    return
            except Exception:
                pass
        returns = sum(1 for m in self.memory if "return" in m)
        if returns >= 2:
            self.reflection = "returning what I buy keeps working, so keep buying and returning"
        elif any("listed" in m for m in self.memory):
            self.reflection = "listing items is bringing sales, keep listing"
        else:
            self.reflection = "nothing notable yet, stay the course"

    def _state(self, m: Marketplace) -> dict:
        mine = [l.id for l in m.listings.values() if l.seller == self.account.id]
        others = [{"id": l.id, "title": l.title, "price": l.price}
                  for l in list(m.listings.values()) if l.seller != self.account.id][:8]
        my_buys = [{"order": o.id, "listing": o.listing}
                   for o in m.orders_as_buyer(self.account.id) if o.status == "fulfilled"][-5:]
        return {"you": self.account.name, "balance": round(self.balance, 2),
                "your_listings": mine, "buyable": others, "your_recent_buys": my_buys,
                "recent_memory": self.memory[-5:], "your_reflection": self.reflection}

    def _decide_llm(self, m: Marketplace) -> dict:
        sysmsg = (f"You are {self.account.name}, a member of a creator marketplace. {self.behavior} "
                  "Use your recent_memory and your_reflection to learn from what happened, then choose "
                  "exactly one action for this cycle by calling choose_action. Act in character.")
        user = "Your state:\n" + json.dumps(self._state(m)) + "\n\nChoose one action."
        msg = self.llm.chat(
            messages=[{"role": "system", "content": sysmsg}, {"role": "user", "content": user}],
            tools=[CHOOSE_ACTION_TOOL],
            tool_choice={"type": "function", "function": {"name": "choose_action"}},
            temperature=0.9, max_tokens=200)
        calls = (msg or {}).get("tool_calls") or []
        if not calls:
            return {"action": "hold"}
        args = calls[0].get("function", {}).get("arguments", "{}")
        return args if isinstance(args, dict) else json.loads(args)

    def _decide_fallback(self, m: Marketplace, rng) -> dict:
        # stochastic stand-in weighted by persona, so the sim runs without a key
        w = {"list": 0.3, "buy": 0.3, "return": 0.1, "hold": 0.3}
        if "returner" in self.persona:
            w = {"list": 0.05, "buy": 0.45, "return": 0.45, "hold": 0.05}
        elif "seller" in self.persona:
            w = {"list": 0.6, "buy": 0.2, "return": 0.05, "hold": 0.15}
        actions, weights = list(w), list(w.values())
        a = str(rng.choice(actions, p=[x / sum(weights) for x in weights]))
        return {"action": a, "title": f"{rng.choice(_CATS)} drop",
                "price": round(float(rng.uniform(5, 120)), 2), "category": str(rng.choice(_CATS))}


class AgentMarket:
    """A marketplace driven by customer agents deciding each cycle."""

    def __init__(self, llm: LLMClient | None = None, n_agents: int = 6, seed: int = 7,
                 reflect_every: int = 2) -> None:
        import numpy as np
        self.rng = np.random.default_rng(seed)
        self.m = Marketplace()
        self.llm = llm or LLMClient()
        self.reflect_every = max(1, int(reflect_every))
        self.agents: list[CustomerAgent] = []
        self._lid = 0
        self._oid = 0
        self.log: list[dict] = []
        countries = ["US", "IN", "BR", "GB", "NG"]
        firsts = ["Ava", "Aarav", "Davi", "Olivia", "Zainab", "Noah", "Mia", "Arjun"]
        for i in range(n_agents):
            persona, behavior = PERSONAS[i % len(PERSONAS)]
            c = countries[i % len(countries)]
            acc = self.m.add_account(Account(id=f"a{i:03d}",
                                             name=f"{firsts[i % len(firsts)]} {chr(65 + i)}.", country=c))
            self.agents.append(CustomerAgent(account=acc, persona=persona, behavior=behavior,
                                             balance=float(self.rng.integers(300, 900)), llm=self.llm))
            self._list_item(acc.id, f"{persona}'s item", round(float(self.rng.uniform(10, 80)), 2),
                            str(self.rng.choice(_CATS)))

    def _list_item(self, seller, title, price, category):
        lid = f"l{self._lid:04d}"
        self._lid += 1
        self.m.list_item(Listing(id=lid, seller=seller, title=title, price=price, category=category))
        return lid

    def _execute(self, agent: CustomerAgent, act: dict) -> str:
        a = (act or {}).get("action", "hold")
        if a == "list":
            self._list_item(agent.account.id, str(act.get("title", "item"))[:40],
                            max(5.0, min(120.0, float(act.get("price", 20) or 20))),
                            act.get("category") if act.get("category") in _CATS else "prints")
            return f"{agent.account.name} listed an item"
        if a == "buy":
            cand = [l for l in self.m.listings.values()
                    if l.seller != agent.account.id and l.price <= agent.balance]
            if not cand:
                return f"{agent.account.name} could not buy (nothing affordable)"
            lst = act.get("listing_id")
            listing = self.m.listings.get(lst) if lst else None
            if listing is None or listing.seller == agent.account.id or listing.price > agent.balance:
                listing = cand[int(self.rng.integers(0, len(cand)))]
            o = self.m.place_order(Order(id=f"o{self._oid:05d}", buyer=agent.account.id,
                                         seller=listing.seller, listing=listing.id,
                                         amount=listing.price, day=len(self.log), status="fulfilled"))
            self._oid += 1
            agent.balance -= listing.price
            seller = next((ag for ag in self.agents if ag.account.id == listing.seller), None)
            if seller:
                seller.balance += listing.price
            return f"{agent.account.name} bought {listing.title} for {listing.price}"
        if a == "return":
            mine = [o for o in self.m.orders_as_buyer(agent.account.id) if o.status == "fulfilled"]
            if not mine:
                return f"{agent.account.name} had nothing to return"
            oid = act.get("order_id")
            order = next((o for o in mine if o.id == oid), None) or mine[-1]
            self.m.mark_return(order, str(act.get("reason", "returned")))
            agent.balance += order.amount          # refunded
            seller = next((ag for ag in self.agents if ag.account.id == order.seller), None)
            if seller:
                seller.balance -= order.amount
            return f"{agent.account.name} returned {order.listing}"
        return f"{agent.account.name} held"

    def tick(self) -> list[dict]:
        order = list(range(len(self.agents)))
        self.rng.shuffle(order)
        events = []
        for i in order:
            agent = self.agents[i]
            act = agent.decide(self.m, self.rng)
            outcome = self._execute(agent, act)
            agent.remember(f"t{len(self.log)}: {act.get('action', 'hold')} -> {outcome}")
            ev = {"agent": agent.account.name, "persona": agent.persona,
                  "action": act.get("action", "hold"), "reason": act.get("reason", ""),
                  "outcome": outcome, "balance": round(agent.balance, 2),
                  "reflection": agent.reflection}
            events.append(ev)
        if (len(self.log) + 1) % self.reflect_every == 0:   # periodic reflection pass
            for a in self.agents:
                try:
                    a.reflect()
                except Exception:
                    pass
        self.log.append({"tick": len(self.log), "events": events})
        return events

    def run(self, ticks: int = 4) -> Marketplace:
        for _ in range(ticks):
            self.tick()
        return self.m
