"""G10 — deepfake chain-of-custody pack for legal discovery.

Builds a tamper-evident chain-of-custody record for a deepfake artefact: each
handling event (acquired, hashed, analysed, exported) is appended with a hash
chain and a handler identity, producing an evidence pack suitable for legal
discovery. Mirrors the audit-chain pattern used elsewhere.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class CustodyEvent:
    seq: int
    event: str
    handler: str
    artefact_sha256: str
    prev_hash: str
    this_hash: str
    ts: str


@dataclass
class ChainOfCustody:
    artefact_id: str
    events: list[CustodyEvent] = field(default_factory=list)

    def record(self, event: str, handler: str, artefact_bytes: bytes) -> CustodyEvent:
        seq = len(self.events)
        prev = self.events[-1].this_hash if self.events else "0" * 64
        art_hash = hashlib.sha256(artefact_bytes).hexdigest()
        ts = datetime.now(timezone.utc).isoformat()
        body = f"{seq}|{event}|{handler}|{art_hash}|{prev}|{ts}"
        this_hash = hashlib.sha256(body.encode()).hexdigest()
        e = CustodyEvent(seq, event, handler, art_hash, prev, this_hash, ts)
        self.events.append(e)
        return e

    def verify(self) -> bool:
        prev = "0" * 64
        for e in self.events:
            body = f"{e.seq}|{e.event}|{e.handler}|{e.artefact_sha256}|{prev}|{e.ts}"
            if hashlib.sha256(body.encode()).hexdigest() != e.this_hash or e.prev_hash != prev:
                return False
            prev = e.this_hash
        return True

    def export_pack(self) -> dict:
        return {
            "artefact_id": self.artefact_id,
            "event_count": len(self.events),
            "chain_valid": self.verify(),
            "events": [
                {"seq": e.seq, "event": e.event, "handler": e.handler,
                 "artefact_sha256": e.artefact_sha256, "hash": e.this_hash, "ts": e.ts}
                for e in self.events
            ],
        }
