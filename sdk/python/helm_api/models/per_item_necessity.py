from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel


class PerItemNecessity(SdkBaseModel):
    needed: bool
    """Whether the per-item cap is non-redundant."""

    example_price: Optional[float] = UNSET
    """A deal over the cap but within budget."""

    note: Optional[str] = UNSET
    """Explanation."""


class PerItemNecessityDict(TypedDict):
    needed: bool
    example_price: NotRequired[float]
    note: NotRequired[str]
