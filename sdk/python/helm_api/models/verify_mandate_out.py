from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel
from .budget_soundness import BudgetSoundness, BudgetSoundnessDict
from .guard_necessity import GuardNecessity, GuardNecessityDict
from .per_item_necessity import PerItemNecessity, PerItemNecessityDict


class VerifyMandateOut(SdkBaseModel):
    verified_signature: bool
    """Whether the mandate signature verified."""

    result: str
    """PROVEN_BOUNDED, NOT_PROVEN or REJECTED."""

    budget_soundness: Optional[BudgetSoundness] = UNSET
    """The budget-soundness proof."""

    guard_necessity: Optional[GuardNecessity] = UNSET
    """The running-total guard counterexample."""

    per_item_necessity: Optional[PerItemNecessity] = UNSET
    """The per-item guard counterexample."""

    verdict_alg: Optional[str] = UNSET
    """Algorithm the verdict is signed with."""

    verdict_signed: Optional[bool] = UNSET
    """Whether a signed verdict was emitted."""


class VerifyMandateOutDict(TypedDict):
    verified_signature: bool
    result: str
    budget_soundness: NotRequired[BudgetSoundnessDict]
    guard_necessity: NotRequired[GuardNecessityDict]
    per_item_necessity: NotRequired[PerItemNecessityDict]
    verdict_alg: NotRequired[str]
    verdict_signed: NotRequired[bool]
