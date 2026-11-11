from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel


class SignalOut(SdkBaseModel):
    source: str
    """'model' or 'fallback'."""

    rationale: str
    """Why the adjustment was made."""

    cited: Optional[str] = UNSET
    """The signal phrase the model cited."""

    confidence: float
    """Model confidence, 0 to 1."""

    disagreement: float
    """Ensemble disagreement, 0 to 1."""

    period_deltas: dict[str, float]
    """Demand delta per period index."""


class SignalOutDict(TypedDict):
    source: str
    rationale: str
    cited: NotRequired[str]
    confidence: float
    disagreement: float
    period_deltas: dict[str, float]
