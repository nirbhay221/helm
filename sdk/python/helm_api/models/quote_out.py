from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class QuoteOut(SdkBaseModel):
    ticker: str
    """Uppercased ticker."""

    price: float
    """Latest price."""

    backend: str
    """'alpaca-paper' or a live-price source."""


class QuoteOutDict(TypedDict):
    ticker: str
    price: float
    backend: str
