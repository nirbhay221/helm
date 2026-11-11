from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel


class Allocation(SdkBaseModel):
    member: str
    """Member name."""

    ok: bool
    """Whether the member was included."""

    signed: bool
    """Whether the mandate verified."""

    share: Optional[float] = UNSET
    """Fraction of the position owned."""

    units: Optional[float] = UNSET
    """Units owned."""

    value: Optional[float] = UNSET
    """Dollar value owned."""

    reason: str
    """Why included or dropped."""


class AllocationDict(TypedDict):
    member: str
    ok: bool
    signed: bool
    share: NotRequired[float]
    units: NotRequired[float]
    value: NotRequired[float]
    reason: str
