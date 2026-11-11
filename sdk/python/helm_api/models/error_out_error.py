from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class ErrorOutError(SdkBaseModel):
    error: str
    """Why the request failed."""


class ErrorOutErrorDict(TypedDict):
    error: str
