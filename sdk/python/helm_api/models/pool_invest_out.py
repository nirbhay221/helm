from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel
from .allocation import Allocation, AllocationDict


class PoolInvestOut(SdkBaseModel):
    asset: str
    """Ticker co-owned."""

    label: Optional[str] = UNSET
    """Human label for the pool."""

    funded_total: float
    """Total cash pooled."""

    total_units: float
    """Units bought for the pool."""

    price: float
    """Fill price per unit."""

    backend: str
    """'alpaca-paper' or a live-price source."""

    routed_to_alpaca: bool
    """Whether a real paper order was placed."""

    members: Optional[list[str]] = UNSET
    """Member names in the pool."""

    allocations: list[Allocation]
    """Per-member share of the position."""


class PoolInvestOutDict(TypedDict):
    asset: str
    label: NotRequired[str]
    funded_total: float
    total_units: float
    price: float
    backend: str
    routed_to_alpaca: bool
    members: NotRequired[list[str]]
    allocations: list[AllocationDict]
