from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel


class ReservesIn(SdkBaseModel):
    lots: Optional[list[float]] = UNSET
    """Safety-fund reserve lots."""

    liabilities: float = 9000.0
    """Total outstanding liabilities."""

    bits: int = 32
    """Range-proof width in bits."""


class ReservesInDict(TypedDict):
    lots: NotRequired[list[float]]
    liabilities: NotRequired[float]
    bits: NotRequired[int]
