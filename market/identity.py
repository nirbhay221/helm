"""Agent identity attestation: a verifiable passport for an autonomous agent.

A spend mandate says what an agent may do. It does not say WHO the agent is. In agentic
commerce a counterparty needs both: an identity credential that binds an agent to its
owner and the capabilities it was issued, signed by an issuer, so the other side can
verify who it is dealing with before it transacts, and refuse an expired, tampered or
under-scoped identity. This is the identity half of the agent-to-agent stack, alongside
the AP2-style mandate (authority) and the x402 payment (settlement).

Reuses the repo's ES256 signing. An identity carries agent_id, owner, capabilities and
an expiry; verification checks the signature, the expiry, and (optionally) that the
identity actually carries the capability being exercised.
"""
from __future__ import annotations

import time
from typing import List, Optional

from .mandates import OwnerKey, verify_credential


def issue_agent_identity(issuer: OwnerKey, agent_id: str, owner: str,
                         capabilities: List[str], ttl_seconds: int = 3600) -> dict:
    """Issue a signed identity credential for an agent."""
    payload = {"type": "AgentIdentity", "agent_id": str(agent_id), "owner": str(owner),
               "capabilities": [str(c) for c in (capabilities or [])],
               "iat": time.time(), "exp": time.time() + max(1, int(ttl_seconds))}
    return issuer.sign_credential(payload)


def verify_agent_identity(credential: dict, required_capability: Optional[str] = None) -> tuple:
    """Verify an agent identity: signature, type, expiry, and optionally that it carries
    the capability being exercised. Returns (ok, payload, reason)."""
    ok, payload, reason = verify_credential(credential or {})
    if not ok:
        return False, {}, "signature invalid: " + reason
    if payload.get("type") != "AgentIdentity":
        return False, {}, "not an agent identity"
    if time.time() > float(payload.get("exp", 0)):
        return False, payload, "identity expired"
    if required_capability and required_capability not in (payload.get("capabilities") or []):
        return False, payload, "identity lacks the capability '%s'" % required_capability
    return True, payload, "identity verified"
