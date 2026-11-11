from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel


class TaxOut(SdkBaseModel):
    form: Optional[str] = UNSET
    """Reporting form (1099-K / DAC7)."""

    box_1a_gross: Optional[float] = UNSET
    """Gross reportable amount."""

    transactions: Optional[int] = UNSET
    """Transaction count."""

    federal_threshold: Optional[str] = UNSET
    """Federal reporting threshold."""

    reportable_federally: Optional[bool] = UNSET
    """Whether it is federally reportable."""

    reportable_in_low_threshold_states: Optional[bool] = UNSET
    """Whether a low-threshold state would report it."""

    state_threshold: Optional[str] = UNSET
    """Lowest state threshold."""

    net_after_platform_fees: Optional[float] = UNSET
    """Net after platform fees."""

    note: Optional[str] = UNSET
    """Any caveat."""


class TaxOutDict(TypedDict):
    form: NotRequired[str]
    box_1a_gross: NotRequired[float]
    transactions: NotRequired[int]
    federal_threshold: NotRequired[str]
    reportable_federally: NotRequired[bool]
    reportable_in_low_threshold_states: NotRequired[bool]
    state_threshold: NotRequired[str]
    net_after_platform_fees: NotRequired[float]
    note: NotRequired[str]
