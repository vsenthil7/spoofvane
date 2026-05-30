"""W14 evidence provenance: tamper-evident evidence record tied to an audit chain.

Builds a court-ready evidence record for a finding: content hash, optional C2PA
provenance, and a link to the prior audit-chain hash so the record is part of a
verifiable chain (matches the v06 audit hash-chain design).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


@dataclass
class EvidenceRecord:
    finding_id: str
    captured_at: str
    content_sha256: str
    prev_hash: str
    record_hash: str
    c2pa_trust: str | None = None

    def verify_link(self, prev_hash: str) -> bool:
        return self.prev_hash == prev_hash


def _hash(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def build_evidence_record(finding_id: str, captured_at: str, content: bytes | str,
                          prev_hash: str = "0" * 64,
                          c2pa_trust: str | None = None) -> EvidenceRecord:
    """Create a chained evidence record. record_hash binds content + prev_hash,
    so any tamper or reorder breaks the chain."""
    if isinstance(content, str):
        content = content.encode()
    content_sha = hashlib.sha256(content).hexdigest()
    record_hash = _hash(finding_id, captured_at, content_sha, prev_hash, c2pa_trust or "")
    return EvidenceRecord(
        finding_id=finding_id, captured_at=captured_at,
        content_sha256=content_sha, prev_hash=prev_hash,
        record_hash=record_hash, c2pa_trust=c2pa_trust,
    )


def verify_chain(records: list[EvidenceRecord]) -> bool:
    """Verify a list of evidence records forms an unbroken hash chain."""
    for i in range(1, len(records)):
        if records[i].prev_hash != records[i - 1].record_hash:
            return False
    # Also re-derive each record_hash to detect content tampering.
    for r in records:
        expected = _hash(r.finding_id, r.captured_at, r.content_sha256,
                         r.prev_hash, r.c2pa_trust or "")
        if expected != r.record_hash:
            return False
    return True
