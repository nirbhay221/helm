from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel
from .group_buy_line import GroupBuyLine, GroupBuyLineDict


class GroupBuyOut(SdkBaseModel):
    discount_rate: float
    """Unlocked volume-discount rate."""

    pooled_qty: float
    """Total units bought together."""

    unit_price: float
    """List price per unit."""

    discounted_unit_price: float
    """Discounted price per unit."""

    total_list: float
    """Total at list price."""

    total_paid: float
    """Total actually paid."""

    total_saved: float
    """Total saving."""

    lines: list[GroupBuyLine]
    """Per-member cost and Shapley saving."""


class GroupBuyOutDict(TypedDict):
    discount_rate: float
    pooled_qty: float
    unit_price: float
    discounted_unit_price: float
    total_list: float
    total_paid: float
    total_saved: float
    lines: list[GroupBuyLineDict]
