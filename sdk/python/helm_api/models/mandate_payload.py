from __future__ import annotations

from pydantic import Field
from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel


class MandatePayload(SdkBaseModel):
    type_: Optional[str] = Field(default=UNSET, alias="type")
    """Credential type."""

    owner: Optional[str] = UNSET
    """Owner name."""

    max_total: Optional[float] = UNSET
    """Total budget."""

    max_per_item: Optional[float] = UNSET
    """Per-item cap."""

    allowed_categories: Optional[list[str]] = UNSET
    """Allowed categories."""

    approval_threshold: Optional[float] = UNSET
    """Auto-approve under this."""


class MandatePayloadDict(TypedDict):
    type_: NotRequired[str]
    owner: NotRequired[str]
    max_total: NotRequired[float]
    max_per_item: NotRequired[float]
    allowed_categories: NotRequired[list[str]]
    approval_threshold: NotRequired[float]
