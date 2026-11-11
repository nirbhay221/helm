from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel
from .criterion_result import CriterionResult, CriterionResultDict


class Settled(SdkBaseModel):
    buyer: str
    """Buyer identifier."""

    seller: str
    """Seller identifier."""

    amount: float
    """Amount settled."""

    status: str
    """'released' or 'refunded'."""

    authorization_id: str
    """PayPal authorization id."""

    reason: str
    """Plain-language outcome."""

    criteria: list[str]
    """Acceptance criteria keys."""

    criteria_results: list[CriterionResult]
    """Per-criterion outcome."""


class SettledDict(TypedDict):
    buyer: str
    seller: str
    amount: float
    status: str
    authorization_id: str
    reason: str
    criteria: list[str]
    criteria_results: list[CriterionResultDict]
