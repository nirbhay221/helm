from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel


class ReservesOut(SdkBaseModel):
    solvent: bool
    """Whether solvency verified."""

    provable: bool
    """Whether a proof exists (false if insolvent)."""

    identity_ok: Optional[bool] = UNSET
    """Whether the homomorphic identity held."""

    bits_ok: Optional[bool] = UNSET
    """Whether all bit proofs verified."""

    range_bits: Optional[int] = UNSET
    """Range-proof width."""

    lot_commitments: Optional[int] = UNSET
    """Number of hidden reserve lots."""

    bit_proofs: Optional[int] = UNSET
    """Number of bit proofs."""

    liability_commitment_sha256: Optional[str] = UNSET
    """Hash of the liability commitment."""

    reveals: Optional[str] = UNSET
    """What the proof reveals."""

    statement: Optional[str] = UNSET
    """What was proven."""

    reason: Optional[str] = UNSET
    """Why a proof could not be produced, if any."""


class ReservesOutDict(TypedDict):
    solvent: bool
    provable: bool
    identity_ok: NotRequired[bool]
    bits_ok: NotRequired[bool]
    range_bits: NotRequired[int]
    lot_commitments: NotRequired[int]
    bit_proofs: NotRequired[int]
    liability_commitment_sha256: NotRequired[str]
    reveals: NotRequired[str]
    statement: NotRequired[str]
    reason: NotRequired[str]
