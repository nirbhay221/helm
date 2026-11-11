from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel


class AdvanceIn(SdkBaseModel):
    proven_earnings: float = 1000.0
    """Proven unpaid earnings to borrow against."""

    fund: float = 10000.0
    """Safety-fund balance."""

    history: Optional[list[float]] = UNSET
    """Past payout history, oldest first."""

    creator: str = "creator"
    """Creator identifier."""


class AdvanceInDict(TypedDict):
    proven_earnings: NotRequired[float]
    fund: NotRequired[float]
    history: NotRequired[list[float]]
    creator: NotRequired[str]
