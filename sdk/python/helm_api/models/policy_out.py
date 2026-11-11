from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel
from .constraints1 import Constraints1, Constraints1Dict
from .weights2 import Weights2, Weights2Dict


class PolicyOut(SdkBaseModel):
    source: str
    """'model' when the live model compiled it, else 'fallback'."""

    reading: str
    """How the model read the policy."""

    weights: Weights2
    """Objective weights."""

    constraints: Constraints1
    """Hard constraints."""

    violations: Optional[list[str]] = UNSET
    """Any bounds the policy tried to break."""


class PolicyOutDict(TypedDict):
    source: str
    reading: str
    weights: Weights2Dict
    constraints: Constraints1Dict
    violations: NotRequired[list[str]]
