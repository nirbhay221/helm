from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class ErrorOut(SdkBaseModel):
    error: str
    """Why the request failed."""


class ErrorOutDict(TypedDict):
    error: str
