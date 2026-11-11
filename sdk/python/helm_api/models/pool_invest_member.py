from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel


class PoolInvestMember(SdkBaseModel):
    member: str
    """Member name."""

    amount: float = 0.0
    """Cash this member pools."""

    budget: Optional[float] = UNSET
    """Signed budget (defaults to amount)."""


class PoolInvestMemberDict(TypedDict):
    member: str
    amount: NotRequired[float]
    budget: NotRequired[float]
