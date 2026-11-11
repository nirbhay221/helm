from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel


class GuardNecessity(SdkBaseModel):
    busts: bool
    """Whether dropping the guard breaks the budget."""

    n_deals: Optional[int] = UNSET
    """Deals needed to bust the budget."""

    prices: Optional[list[float]] = UNSET
    """The busting deal prices."""

    total: Optional[float] = UNSET
    """Total of the busting deals."""

    note: Optional[str] = UNSET
    """Explanation."""


class GuardNecessityDict(TypedDict):
    busts: bool
    n_deals: NotRequired[int]
    prices: NotRequired[list[float]]
    total: NotRequired[float]
    note: NotRequired[str]
