"""A tamper-evident, hash-chained receipt ledger for every money action.

The SQLite ledger prevents double-booking, but a ledger a privileged party can edit
after the fact is not evidence. The strongest trust-focused entries in the field chain
each action into a receipt whose hash commits to the one before it, so any later edit,
insertion or deletion breaks the chain and is detectable without trusting the keeper.

Each receipt is hash = SHA-256(prev_hash || canonical(record)). Verification re-walks
the chain and re-derives every hash; the first mismatch is the tamper point. This is the
same construction a blockchain or a certificate-transparency log uses, kept minimal.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import List, Optional

_GENESIS = "0" * 64


def _canon(record: dict) -> str:
    """Deterministic serialization so the hash is stable regardless of key order."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"))


def _hash(prev_hash: str, record: dict) -> str:
    return hashlib.sha256((prev_hash + _canon(record)).encode()).hexdigest()


@dataclass
class ReceiptChain:
    receipts: List[dict] = field(default_factory=list)

    @property
    def head(self) -> str:
        return self.receipts[-1]["hash"] if self.receipts else _GENESIS

    def append(self, action: str, ref: str, amount: float, meta: Optional[dict] = None) -> dict:
        """Record a money action and chain it to the previous receipt."""
        prev = self.head
        record = {"seq": len(self.receipts), "action": str(action), "ref": str(ref),
                  "amount": round(float(amount), 2), "meta": meta or {},
                  "ts": round(time.time(), 3), "prev_hash": prev}
        record["hash"] = _hash(prev, {k: record[k] for k in
                                      ("seq", "action", "ref", "amount", "meta", "ts", "prev_hash")})
        self.receipts.append(record)
        return record

    def verify(self) -> dict:
        """Re-walk the chain and re-derive each hash. Returns whether it is intact and,
        if not, the sequence number where it first breaks."""
        prev = _GENESIS
        for r in self.receipts:
            body = {k: r[k] for k in ("seq", "action", "ref", "amount", "meta", "ts", "prev_hash")}
            if r["prev_hash"] != prev or r["hash"] != _hash(prev, body):
                return {"intact": False, "broken_at": r["seq"],
                        "reason": "receipt %d does not chain to the previous hash" % r["seq"]}
            prev = r["hash"]
        return {"intact": True, "length": len(self.receipts), "head": self.head}
