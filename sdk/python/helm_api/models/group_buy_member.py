from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import SdkBaseModel


class GroupBuyMember(SdkBaseModel):
    member: str
    """Member name."""

    qty: float = 1.0
    """Units this member wants."""


class GroupBuyMemberDict(TypedDict):
    member: str
    qty: NotRequired[float]
