from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class Held(SdkBaseModel):
    buyer: str
    """Buyer identifier."""

    seller: str
    """Seller identifier."""

    amount: float
    """Amount held."""

    status: str
    """Hold status."""

    authorization_id: str
    """PayPal authorization id."""

    reason: str
    """Plain-language status."""

    criteria: list[str]
    """Acceptance criteria keys."""


class HeldDict(TypedDict):
    buyer: str
    seller: str
    amount: float
    status: str
    authorization_id: str
    reason: str
    criteria: list[str]
