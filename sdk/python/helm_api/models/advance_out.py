from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class AdvanceOut(SdkBaseModel):
    eligible: bool
    """Whether an advance is offered."""

    max_amount: float
    """Offered amount."""

    pd: float
    """Probability of default, 0 to 1."""

    fee_rate: float
    """Fee rate on the advance."""

    binding_cap: str
    """Which cap bound the offer."""

    reason: str
    """Plain-language explanation."""


class AdvanceOutDict(TypedDict):
    eligible: bool
    max_amount: float
    pd: float
    fee_rate: float
    binding_cap: str
    reason: str
