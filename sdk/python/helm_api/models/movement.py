from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class Movement(SdkBaseModel):
    kind: str
    """Ledger movement kind."""

    ref_type: str
    """Referenced object type."""

    ref_id: str
    """Referenced object id."""

    amount: float
    """Amount moved."""

    status: str
    """Movement status."""


class MovementDict(TypedDict):
    kind: str
    ref_type: str
    ref_id: str
    amount: float
    status: str
