from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import SdkBaseModel


class PolicyIn(SdkBaseModel):
    text: str = ""
    """Treasury policy in plain English."""


class PolicyInDict(TypedDict):
    text: NotRequired[str]
