from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import SdkBaseModel


class ShopBuyIn(SdkBaseModel):
    title: str = "item"
    """Product title."""

    price: float = 0.0
    """Product price."""

    merchant: str = "merchant"
    """Merchant domain."""

    budget: float = 0.0
    """Signed spend budget."""

    category: str = "goods"
    """Product category."""


class ShopBuyInDict(TypedDict):
    title: NotRequired[str]
    price: NotRequired[float]
    merchant: NotRequired[str]
    budget: NotRequired[float]
    category: NotRequired[str]
