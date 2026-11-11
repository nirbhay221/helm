from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class CriterionResult(SdkBaseModel):
    key: str
    """Criterion name."""

    passed: bool
    """Whether it passed."""


class CriterionResultDict(TypedDict):
    key: str
    passed: bool
