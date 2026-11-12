"""Product search for the buyer side of the marketplace.

A person on the marketplace earns as a seller and can spend those earnings as a buyer,
on the same account. This module finds real products to buy. It uses Channel3's
product-search API when CHANNEL3_API_KEY is present, and falls back to a small
deterministic catalog otherwise, so the buy flow runs end to end with no credentials.

The purchase itself is authorized by the person's signed spend mandate and settled
through pay-on-proof escrow on PayPal; this module only finds the product.

Channel3: POST https://api.trychannel3.com/v1/search, header x-api-key, body
{"query": str, "limit": int, "filters": {"price": {"max_price": float}}}. Price, buy
URL and merchant are on offers[0]; brand on brands[0]; image on images[0].
"""
from __future__ import annotations

import os

import requests

C3_SEARCH_URL = "https://api.trychannel3.com/v1/search"

# Creator-relevant demo catalog used when no Channel3 key is set. Honest placeholder
# data: prices are realistic, links are illustrative.
_DEMO_CATALOG = [
    {"id": "demo-mic", "title": "USB condenser microphone for streaming", "brand": "Rode",
     "merchant": "bhphotovideo.com", "price": 99.0, "currency": "USD",
     "url": "https://www.bhphotovideo.com", "image": "", "category": "audio"},
    {"id": "demo-light", "title": "18 inch ring light with stand", "brand": "Neewer",
     "merchant": "neewer.com", "price": 59.99, "currency": "USD",
     "url": "https://neewer.com", "image": "", "category": "lighting"},
    {"id": "demo-webcam", "title": "1080p streaming webcam", "brand": "Logitech",
     "merchant": "logitech.com", "price": 69.99, "currency": "USD",
     "url": "https://www.logitech.com", "image": "", "category": "video"},
    {"id": "demo-tripod", "title": "Adjustable camera tripod", "brand": "Manfrotto",
     "merchant": "manfrotto.com", "price": 45.0, "currency": "USD",
     "url": "https://www.manfrotto.com", "image": "", "category": "video"},
    {"id": "demo-sd", "title": "128GB high-speed SD card", "brand": "SanDisk",
     "merchant": "westerndigital.com", "price": 24.99, "currency": "USD",
     "url": "https://www.westerndigital.com", "image": "", "category": "storage"},
    {"id": "demo-presets", "title": "Lightroom preset pack for creators", "brand": "PixelPacks",
     "merchant": "gumroad.com", "price": 19.0, "currency": "USD",
     "url": "https://gumroad.com", "image": "", "category": "software"},
    {"id": "demo-capture", "title": "USB HDMI capture card", "brand": "Elgato",
     "merchant": "elgato.com", "price": 129.99, "currency": "USD",
     "url": "https://www.elgato.com", "image": "", "category": "video"},
    {"id": "demo-editor", "title": "Video editing software annual license", "brand": "EditPro",
     "merchant": "editpro.com", "price": 149.0, "currency": "USD",
     "url": "https://example.com/editpro", "image": "", "category": "software"},
]


import contextvars as _cv
# set only inside one control-room run that asks to plant a poisoned listing; a context variable,
# so one visitor's attack toggle can never leak into another visitor's search
LIVE_ATTACK: "_cv.ContextVar[bool]" = _cv.ContextVar("helm_live_attack", default=False)


class Channel3Client:
    """Searches Channel3 for products, or a demo catalog when no key is configured."""

    def __init__(self, env: dict | None = None) -> None:
        env = env if env is not None else os.environ
        self.api_key = (env.get("CHANNEL3_API_KEY") or "").strip()
        self.available = bool(self.api_key)

    def search(self, query: str, max_price: float | None = None, limit: int = 6):
        """Return (products, backend). backend is 'channel3' live or 'demo-catalog'."""
        if self.available:
            try:
                return self._live_search(query, max_price, limit), "channel3"
            except Exception:
                pass  # any live failure falls back to the catalog, never fabricates
        return self._demo_search(query, max_price, limit), "demo-catalog"

    def _live_search(self, query: str, max_price: float | None, limit: int):
        body: dict = {"query": query, "limit": max(1, min(int(limit), 30))}
        if max_price:
            body["filters"] = {"price": {"max_price": float(max_price)}}
        r = requests.post(C3_SEARCH_URL, json=body, timeout=20,
                          headers={"x-api-key": self.api_key, "Content-Type": "application/json"})
        r.raise_for_status()
        data = r.json()
        out = []
        for p in (data.get("products") or [])[:limit]:
            offers = p.get("offers") or []
            off = offers[0] if offers else {}
            price = off.get("price") or {}
            brands = p.get("brands") or []
            imgs = p.get("images") or []
            cat = p.get("category")
            out.append({
                "id": p.get("id", ""),
                "title": p.get("title", ""),
                "brand": brands[0].get("name", "") if brands else "",
                "merchant": off.get("domain", ""),
                "price": float(price.get("price") or 0.0),
                "currency": price.get("currency", "USD"),
                "url": off.get("url", ""),
                "image": (imgs[0].get("url") if imgs else "") or "",
                "category": cat.get("slug", "goods") if isinstance(cat, dict) else "goods",
            })
        return out

    def _demo_search(self, query: str, max_price: float | None, limit: int):
        q = (query or "").lower().strip()
        items = [dict(x) for x in _DEMO_CATALOG
                 if not q or q in x["title"].lower() or q in x["brand"].lower()
                 or q in x["category"].lower()]
        if not items:
            items = [dict(x) for x in _DEMO_CATALOG]      # show the catalog if nothing matches
        if max_price:
            priced = [x for x in items if x["price"] <= float(max_price)]
            items = priced or items                        # keep something to show
        return items[:limit]
