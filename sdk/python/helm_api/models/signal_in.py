from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import SdkBaseModel


class SignalIn(SdkBaseModel):
    text: str = ""
    """An operational signal to react to."""

    current_period: int = 0
    """Index of the current period."""

    baseline_demand: float = 1000.0
    """Baseline demand before adjustment."""

    horizon: int = 6
    """Number of periods to forecast."""


class SignalInDict(TypedDict):
    text: NotRequired[str]
    current_period: NotRequired[int]
    baseline_demand: NotRequired[float]
    horizon: NotRequired[int]
