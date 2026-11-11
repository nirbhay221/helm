from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class Constraints(SdkBaseModel):
    max_fraction_per_creator: float
    """Cap on any one creator's share."""

    exclude_countries: list[str]
    """Country codes to exclude."""

    max_risk: float
    """Maximum per-creator risk allowed."""


class ConstraintsDict(TypedDict):
    max_fraction_per_creator: float
    exclude_countries: list[str]
    max_risk: float
