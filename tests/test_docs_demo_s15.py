"""Sprint 15 — demo manifest integrity + required-docs presence."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_demo_manifest_chain_is_valid():
    import hashlib
    m = json.loads((ROOT / "demo/demo_manifest.json").read_text())
    prev = "0" * 16
    for st in m["steps"]:
        assert st["prev"] == prev
        chain = hashlib.sha256(f"{prev}{st['step_hash']}".encode()).hexdigest()[:16]
        assert st["chain"] == chain
        prev = chain
    assert m["manifest_root"] == prev


def test_demo_recording_marked_blocked_env_honestly():
    m = json.loads((ROOT / "demo/demo_manifest.json").read_text())
    assert m["recording"]["status"] == "BLOCKED-ENV"


def test_required_docs_exist():
    required = [
        "BRD.md", "PRD.md", "FRD.md", "NFRD.md", "RTM.md",
        "architecture.md", "security.md", "privacy.md",
        "ANTIPATTERN_LEDGER.md", "DEPTH_LEDGER.md", "SPONSOR_USAGE_LEDGER.md",
        "COST_ENVELOPE.md", "LESSONS_LEDGER.md", "MINORITY_REPORT.md",
        "SECURITY_ABUSE_CASES.md", "REPRODUCIBLE_BUILD.md",
        "EXEC_PROTECTION_DPIA.md", "TRACEABILITY_MASTER.md",
    ]
    missing = [d for d in required if not (ROOT / "docs" / d).exists()]
    assert not missing, f"missing docs: {missing}"


def test_docs_carry_coder_attribution():
    for d in ("BRD.md", "PRD.md", "architecture.md", "DEPTH_LEDGER.md"):
        assert "Claude (Opus 4.8)" in (ROOT / "docs" / d).read_text()
