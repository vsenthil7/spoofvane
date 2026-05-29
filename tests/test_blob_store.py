"""Content-addressed blob store: write/read/verify."""

import pytest

from src.storage.blob_store import blob_path, read_blob, verify_blob, write_blob


def test_write_then_read_roundtrip() -> None:
    content = b"<html><body>hello</body></html>"
    sha, path = write_blob(content, suffix=".html")
    assert path.exists()
    assert read_blob(sha, ".html") == content


def test_hash_is_deterministic() -> None:
    content = b"deterministic"
    a, _ = write_blob(content, ".bin")
    b, _ = write_blob(content, ".bin")
    assert a == b


def test_verify_detects_tampering(tmp_path) -> None:
    content = b"tamper-test"
    sha, path = write_blob(content, ".bin")
    # Pre-tamper: verifies
    assert verify_blob(sha, ".bin") is True
    # Tamper with the file on disk
    path.write_bytes(b"tampered!")
    assert verify_blob(sha, ".bin") is False


def test_blob_path_uses_sharded_layout() -> None:
    sha = "abcdef0123456789" * 4  # 64 hex chars
    p = blob_path(sha, ".png")
    parts = p.parts
    # Should be …/aa/bb/<full-sha><suffix>
    assert parts[-3] == "ab"
    assert parts[-2] == "cd"
    assert parts[-1] == f"{sha}.png"


def test_missing_blob_raises() -> None:
    with pytest.raises(FileNotFoundError):
        read_blob("0" * 64, ".png")
