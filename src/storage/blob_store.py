"""Evidence blob store.

Writes are content-addressed (SHA-256) — the returned hash *is* the lookup
key. This gives us tamper-evidence essentially for free: any modification
to an evidence file changes its hash, which the inspections-table row no
longer matches.

In MOCK_MODE this writes to the local filesystem under ``EVIDENCE_DIR``.
In production it would write to S3 with object-lock for 90 days.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Final

from ..common.settings import get_settings


_SUBDIR_LEN: Final[int] = 2


def write_blob(content: bytes, suffix: str = "") -> tuple[str, Path]:
    """Write a content-addressed blob; return (hex_sha256, path).

    Path layout: ``<EVIDENCE_DIR>/aa/bb/<full_hash><suffix>``.
    """
    settings = get_settings()
    h = hashlib.sha256(content).hexdigest()
    sub1 = h[:_SUBDIR_LEN]
    sub2 = h[_SUBDIR_LEN : 2 * _SUBDIR_LEN]
    dirpath = settings.evidence_dir / sub1 / sub2
    dirpath.mkdir(parents=True, exist_ok=True)
    path = dirpath / f"{h}{suffix}"
    if not path.exists():
        path.write_bytes(content)
    return h, path


def read_blob(sha256: str, suffix: str = "") -> bytes:
    settings = get_settings()
    sub1 = sha256[:_SUBDIR_LEN]
    sub2 = sha256[_SUBDIR_LEN : 2 * _SUBDIR_LEN]
    path = settings.evidence_dir / sub1 / sub2 / f"{sha256}{suffix}"
    return path.read_bytes()


def verify_blob(sha256: str, suffix: str = "") -> bool:
    """Return True iff the stored blob's hash matches the expected hash."""
    try:
        content = read_blob(sha256, suffix)
    except FileNotFoundError:
        return False
    return hashlib.sha256(content).hexdigest() == sha256


def blob_path(sha256: str, suffix: str = "") -> Path:
    settings = get_settings()
    sub1 = sha256[:_SUBDIR_LEN]
    sub2 = sha256[_SUBDIR_LEN : 2 * _SUBDIR_LEN]
    return settings.evidence_dir / sub1 / sub2 / f"{sha256}{suffix}"
