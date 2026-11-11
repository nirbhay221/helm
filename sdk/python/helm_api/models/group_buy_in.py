from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel
from .group_buy_member import GroupBuyMember, GroupBuyMemberDict


class GroupBuyIn(SdkBaseModel):
    item: str = "preset pack"
    """Item bought in bulk."""

    unit_price: float = 20.0
    """List price per unit."""

    members: Optional[list[GroupBuyMember]] = UNSET
    """People buying together."""


class GroupBuyInDict(TypedDict):
    item: NotRequired[str]
    unit_price: NotRequired[float]
    members: NotRequired[list[GroupBuyMemberDict]]
