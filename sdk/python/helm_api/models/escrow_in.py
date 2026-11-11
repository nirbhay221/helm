from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import SdkBaseModel


class EscrowIn(SdkBaseModel):
    amount: float = 200.0
    """Deal amount to hold in escrow."""

    cheat: bool = False
    """Deliver nothing and try to get paid, to show the refund."""


class EscrowInDict(TypedDict):
    amount: NotRequired[float]
    cheat: NotRequired[bool]
