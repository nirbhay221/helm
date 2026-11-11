from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel
from .product import Product, ProductDict


class ShopSearchOut(SdkBaseModel):
    backend: str
    """'channel3' live or 'demo-catalog'."""

    live: bool
    """Whether a Channel3 key is configured."""

    query: str
    """The query searched."""

    budget: float
    """The stated budget."""

    products: list[Product]
    """Matching products."""


class ShopSearchOutDict(TypedDict):
    backend: str
    live: bool
    query: str
    budget: float
    products: list[ProductDict]
