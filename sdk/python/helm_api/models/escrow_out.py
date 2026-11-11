from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel
from .held2 import Held2, Held2Dict
from .movement import Movement, MovementDict
from .settled2 import Settled2, Settled2Dict


class EscrowOut(SdkBaseModel):
    held: Held2
    """The authorized hold."""

    settled: Settled2
    """The settlement outcome."""

    backend: str
    """'paypal-sandbox' or 'demo'."""

    movements: list[Movement]
    """Ledger movements."""


class EscrowOutDict(TypedDict):
    held: Held2Dict
    settled: Settled2Dict
    backend: str
    movements: list[MovementDict]
