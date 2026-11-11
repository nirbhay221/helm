from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import SdkBaseModel


class ShopSearchIn(SdkBaseModel):
    query: str = ""
    """What to buy, in natural language."""

    budget: float = 0.0
    """Earnings to spend; flags affordable results."""


class ShopSearchInDict(TypedDict):
    query: NotRequired[str]
    budget: NotRequired[float]
