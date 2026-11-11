from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import SdkBaseModel


class InvestIn(SdkBaseModel):
    amount: float = 1000.0
    """Notional to invest across the basket."""


class InvestInDict(TypedDict):
    amount: NotRequired[float]
