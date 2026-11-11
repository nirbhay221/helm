from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import SdkBaseModel


class VerifyMandateIn(SdkBaseModel):
    max_total: float = 500.0
    """Total budget the owner signs."""

    max_per_item: float = 100.0
    """Per-item cap."""

    owner: str = "agent"
    """Mandate owner."""

    forge: bool = False
    """Widen the budget without re-signing, to show rejection."""


class VerifyMandateInDict(TypedDict):
    max_total: NotRequired[float]
    max_per_item: NotRequired[float]
    owner: NotRequired[str]
    forge: NotRequired[bool]
