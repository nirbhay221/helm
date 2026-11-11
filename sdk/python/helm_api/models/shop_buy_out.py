from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel
from .held import Held, HeldDict
from .settled import Settled, SettledDict


class ShopBuyOut(SdkBaseModel):
    authorized: bool
    """Whether the signed budget authorized the buy."""

    title: str
    """Product title."""

    price: float
    """Price paid."""

    merchant: Optional[str] = UNSET
    """Merchant paid."""

    budget: float = 0.0
    """Signed budget."""

    reason: str = ""
    """Plain-language outcome."""

    backend: Optional[str] = UNSET
    """'paypal-sandbox' or 'demo'."""

    held: Optional[Held] = UNSET
    """The authorized hold, if the buy went through."""

    settled: Optional[Settled] = UNSET
    """The settlement, if the buy went through."""


class ShopBuyOutDict(TypedDict):
    authorized: bool
    title: str
    price: float
    merchant: NotRequired[str]
    budget: NotRequired[float]
    reason: NotRequired[str]
    backend: NotRequired[str]
    held: NotRequired[HeldDict]
    settled: NotRequired[SettledDict]
