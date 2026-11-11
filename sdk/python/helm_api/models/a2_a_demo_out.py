from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel
from .credential1 import Credential1, Credential1Dict
from .credential3 import Credential3, Credential3Dict


class A2ADemoOut(SdkBaseModel):
    valid: Credential3
    """A validly signed intent mandate."""

    tampered: Credential1
    """The same mandate with the cap raised, not re-signed."""

    allowed_categories: list[str]
    """Categories the mandate allows."""

    approval_threshold: float
    """Auto-approve threshold."""

    max_per_item: float
    """Per-item cap."""


class A2ADemoOutDict(TypedDict):
    valid: Credential3Dict
    tampered: Credential1Dict
    allowed_categories: list[str]
    approval_threshold: float
    max_per_item: float
