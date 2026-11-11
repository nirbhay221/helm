from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class Fill(SdkBaseModel):
    ticker: str
    """Ticker filled."""

    units: float
    """Units bought."""

    price: float
    """Fill price."""


class FillDict(TypedDict):
    ticker: str
    units: float
    price: float
