from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class A2ACheckOut(SdkBaseModel):
    verified: bool
    """Whether the mandate signature verified."""

    fits: bool
    """Whether the deal fits the mandate."""

    needs_approval: bool
    """Whether owner approval is required."""

    reason: str
    """Plain-language decision."""


class A2ACheckOutDict(TypedDict):
    verified: bool
    fits: bool
    needs_approval: bool
    reason: str
