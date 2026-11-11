from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel
from .fill import Fill, FillDict


class InvestOut(SdkBaseModel):
    backend: str
    """'alpaca-paper' or a live-price source."""

    fills: list[Fill]
    """Per-ticker fills."""

    cost_basis: float
    """Total cost basis."""

    market_value: float
    """Marked-to-market value."""


class InvestOutDict(TypedDict):
    backend: str
    fills: list[FillDict]
    cost_basis: float
    market_value: float
