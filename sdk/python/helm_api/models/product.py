from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class Product(SdkBaseModel):
    id: str
    """Product id."""

    title: str
    """Product title."""

    brand: str
    """Brand name."""

    merchant: str
    """Merchant domain."""

    price: float
    """Price."""

    currency: str
    """Currency code."""

    url: str
    """Buy URL."""

    image: str
    """Image URL, if any."""

    category: str
    """Category slug."""

    affordable: bool
    """Whether it fits the stated budget."""


class ProductDict(TypedDict):
    id: str
    title: str
    brand: str
    merchant: str
    price: float
    currency: str
    url: str
    image: str
    category: str
    affordable: bool
