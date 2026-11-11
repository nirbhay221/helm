from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class GroupBuyLine(SdkBaseModel):
    member: str
    """Member name."""

    ok: bool
    """Whether the member's contribution was accepted."""

    qty: float
    """Units this member took."""

    solo_cost: float
    """Cost buying alone."""

    pooled_cost: float
    """Cost at the pooled discount."""

    saving_shapley: float
    """Saving attributed by the Shapley value."""


class GroupBuyLineDict(TypedDict):
    member: str
    ok: bool
    qty: float
    solo_cost: float
    pooled_cost: float
    saving_shapley: float
