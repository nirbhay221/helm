from __future__ import annotations

from typing import Any

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel


class A2ACheckIn(SdkBaseModel):
    intent_credential: Optional[Any] = UNSET
    """A signed intent mandate exactly as returned by /api/a2a/demo (kept as a raw object so its ES256 signature is not
    disturbed)."""

    category: str = ""
    """Category the agent wants to buy."""

    price: float = 0.0
    """Proposed deal price."""

    spent: float = 0.0
    """Amount already spent under this mandate."""

    cart_credential: Optional[Any] = UNSET
    """An optional signed cart mandate (raw object)."""


class A2ACheckInDict(TypedDict):
    intent_credential: NotRequired[Any]
    category: NotRequired[str]
    price: NotRequired[float]
    spent: NotRequired[float]
    cart_credential: NotRequired[Any]
