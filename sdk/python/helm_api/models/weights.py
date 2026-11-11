from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class Weights(SdkBaseModel):
    speed: float
    """Weight on paying the longest-waiting first."""

    tax: float
    """Weight on minimizing tax withheld."""

    risk: float
    """Weight on avoiding risky creators."""

    fx: float
    """Weight on minimizing FX cost."""


class WeightsDict(TypedDict):
    speed: float
    tax: float
    risk: float
    fx: float
