"""Signed, verifiable mandates for agent payments, AP2-style.

Google's Agent Payments Protocol (AP2, now moving into the FIDO Alliance) makes a
mandate a verifiable credential: the owner signs what they authorized, and anyone
can verify it, so an agent can prove a human approved a payment and cannot widen
its own authority. AP2 uses two mandates, an INTENT mandate (standing permission)
and a CART mandate (one specific purchase), signed with ES256 (ECDSA P-256).

This module implements exactly that with real cryptography: an owner key signs a
canonical JSON payload with ES256; verification checks the signature against the
embedded public key and the expiry. Tampering with any field, say widening a
spend cap, breaks the signature, so the fit check downstream runs only on a
payload a human actually signed. No new dependency: Python's `cryptography`.
"""
from __future__ import annotations

import base64
import json
import time
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class OwnerKey:
    """An owner's signing key (ES256 / P-256). The private key never leaves here;
    the public key travels inside each credential so anyone can verify it."""

    def __init__(self) -> None:
        self._priv = ec.generate_private_key(ec.SECP256R1())

    def public_pem(self) -> str:
        return self._priv.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo).decode("utf-8")

    def sign_credential(self, payload: dict) -> dict:
        data = _canonical(payload)
        sig = self._priv.sign(data, ec.ECDSA(hashes.SHA256()))
        return {"payload": payload, "alg": "ES256", "public_key": self.public_pem(),
                "signature": base64.b64encode(sig).decode("ascii")}


def verify_credential(credential: dict, expected_public_key: str | None = None) -> tuple[bool, dict, str]:
    """Verify an ES256 credential's signature and expiry. Returns (ok, payload, reason).

    Two distinct guarantees, do not conflate them:
      - INTEGRITY (always checked): the payload was signed by the holder of the key
        embedded in the credential and has not been altered. This alone catches a
        tampered mandate, but NOT a mandate an attacker self-signed with their own key.
      - AUTHORITY (checked only when expected_public_key is given): the embedded key is
        the owner's known key. Pass the owner's registered public key here to bind the
        credential to a trusted owner; otherwise a credential signed with any key passes
        the integrity check. In production the owner key must come from a trusted
        registry, never from the credential being verified."""
    try:
        payload = credential["payload"]
        sig = base64.b64decode(credential["signature"])
        pub_pem = credential["public_key"]
        pub = serialization.load_pem_public_key(pub_pem.encode("utf-8"))
        pub.verify(sig, _canonical(payload), ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:
        return False, {}, "signature does not match (payload was altered or wrong key)"
    except Exception as exc:  # malformed credential
        return False, {}, f"malformed credential: {str(exc)[:80]}"
    if expected_public_key is not None:
        import hmac
        if not hmac.compare_digest("".join(pub_pem.split()), "".join(expected_public_key.split())):
            return False, payload, "public key is not the trusted owner key (possible self-signed forgery)"
    exp = payload.get("exp")
    if exp is not None and time.time() > float(exp):
        return False, payload, "mandate has expired"
    return True, payload, "ok"


def issue_intent_mandate(owner_key: OwnerKey, owner: str, max_total: float, max_per_item: float,
                         allowed_categories=(), approval_threshold: float = 1e9,
                         ttl_seconds: int = 3600) -> dict:
    """The owner's standing authorization, signed. Carries a nonce and expiry."""
    now = time.time()
    payload = {
        "type": "IntentMandate", "owner": owner,
        "max_total": float(max_total), "max_per_item": float(max_per_item),
        "allowed_categories": list(allowed_categories),
        "approval_threshold": float(approval_threshold),
        "nonce": uuid.uuid4().hex, "iat": now, "exp": now + ttl_seconds,
    }
    return owner_key.sign_credential(payload)


def issue_cart_mandate(owner_key: OwnerKey, intent_nonce: str, buyer: str, seller: str,
                       listing: str, amount: float) -> dict:
    """A signed record of one specific approved purchase, tied to an intent nonce."""
    payload = {"type": "CartMandate", "intent_nonce": intent_nonce, "buyer": buyer,
               "seller": seller, "listing": listing, "amount": float(amount), "iat": time.time()}
    return owner_key.sign_credential(payload)
