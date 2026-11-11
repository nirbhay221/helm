from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel
from .mandate_payload2 import MandatePayload2, MandatePayload2Dict


class Credential(SdkBaseModel):
    payload: MandatePayload2
    """The signed mandate payload."""

    signature: str
    """ES256 signature over the payload."""

    alg: str
    """Signature algorithm."""


class CredentialDict(TypedDict):
    payload: MandatePayload2Dict
    signature: str
    alg: str
