from __future__ import annotations

from typing import Any

from pydantic import Field
from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel
from .unions.location import Location, LocationDict


class ValidationError(SdkBaseModel):
    loc: list[Location]
    """Path to the field that failed validation."""

    msg: str
    """Human-readable error message."""

    type_: str = Field(alias="type")
    """Machine-readable error type code."""

    input: Optional[Any] = UNSET
    """The input value that failed validation."""

    ctx: Optional[Any] = UNSET
    """Extra context about the error."""


class ValidationErrorDict(TypedDict):
    loc: list[LocationDict]
    msg: str
    type_: str
    input: NotRequired[Any]
    ctx: NotRequired[Any]
