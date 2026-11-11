from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel


class BudgetSoundness(SdkBaseModel):
    proven: bool
    """Whether the invariant was proven."""

    base_case: Optional[bool] = UNSET
    """Whether the base case holds."""

    inductive_step: str
    """Z3 result for the step ('unsat' means proven)."""

    statement: Optional[str] = UNSET
    """What was proven."""

    method: Optional[str] = UNSET
    """Proof method."""


class BudgetSoundnessDict(TypedDict):
    proven: bool
    base_case: NotRequired[bool]
    inductive_step: str
    statement: NotRequired[str]
    method: NotRequired[str]
