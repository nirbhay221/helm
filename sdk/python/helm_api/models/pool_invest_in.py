from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel
from .pool_invest_member import PoolInvestMember, PoolInvestMemberDict


class PoolInvestIn(SdkBaseModel):
    asset: str = "SPY"
    """Ticker to co-own."""

    members: Optional[list[PoolInvestMember]] = UNSET
    """People pooling into the position."""

    forge: bool = False
    """Tamper the first member's mandate to show it is excluded."""


class PoolInvestInDict(TypedDict):
    asset: NotRequired[str]
    members: NotRequired[list[PoolInvestMemberDict]]
    forge: NotRequired[bool]
