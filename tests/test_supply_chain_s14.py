"""Sprint 14 — supply chain: SBOM + provenance + Makefile (review §V9-4/§V9-5)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sbom_is_valid_cyclonedx():
    sbom = json.loads((ROOT / "supply-chain/sbom.cyclonedx.json").read_text())
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.5"
    assert sbom["metadata"]["component"]["name"] == "spoofvane"
    assert len(sbom["components"]) >= 20


def test_sbom_components_have_purls():
    sbom = json.loads((ROOT / "supply-chain/sbom.cyclonedx.json").read_text())
    for c in sbom["components"]:
        assert c["purl"].startswith("pkg:pypi/")
        assert c["version"]


def test_sbom_covers_key_dependencies():
    sbom = json.loads((ROOT / "supply-chain/sbom.cyclonedx.json").read_text())
    names = {c["name"].lower() for c in sbom["components"]}
    for dep in ("fastapi", "pydantic", "anthropic", "sqlalchemy"):
        assert dep in names


def test_slsa_provenance_shape():
    prov = json.loads((ROOT / "supply-chain/provenance.slsa.json").read_text())
    assert prov["predicateType"] == "https://slsa.dev/provenance/v1"
    assert prov["subject"]
    # honest: builder records BLOCKED-ENV until a real CI builder signs it
    assert "BLOCKED-ENV" in prov["predicate"]["runDetails"]["builder"]["id"]


def test_makefile_has_verify_targets():
    mk = (ROOT / "Makefile").read_text()
    for target in ("bootstrap:", "test:", "depth:", "verify:", "sbom:"):
        assert target in mk
