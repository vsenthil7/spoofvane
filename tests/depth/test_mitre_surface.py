"""v07 D5 Gate — per-surface MITRE ATT&CK TTP mapping differential probe.

Distinct surfaces yield distinct characteristic technique sets; surface
enrichment still layers capability/family techniques; D3FEND countermeasures are
derived; an unknown surface falls back to capability-only enrichment.
"""
from __future__ import annotations

from src.verdict.mitre_enricher import enrich, enrich_for_surface, SURFACE_TECHNIQUES


def test_distinct_surfaces_distinct_ttps():
    social = enrich_for_surface("social")
    appstore = enrich_for_surface("appstore")
    credleak = enrich_for_surface("credleak")
    assert set(social.techniques) != set(appstore.techniques)
    assert set(appstore.techniques) != set(credleak.techniques)
    # Each surface includes its characteristic techniques.
    assert "T1585.001" in social.techniques        # Social Media Accounts
    assert "T1660" in appstore.techniques          # Phishing (mobile)
    assert "T1078" in credleak.techniques          # Valid Accounts


def test_surface_layers_capability_techniques():
    # A domain surface finding that ALSO harvests credentials gets both sets.
    enriched = enrich_for_surface("domain", capabilities=["aitm_relay"], family="m365")
    assert "T1583.001" in enriched.techniques      # from surface
    assert "T1557" in enriched.techniques          # from aitm_relay capability
    assert "T1056.003" in enriched.techniques      # from m365 family -> credential_harvest


def test_d3fend_derived_from_techniques():
    rtp = enrich_for_surface("rtp")               # includes T1557 -> D3-NTA
    assert "D3-NTA" in rtp.d3fend


def test_unknown_surface_falls_back_to_capability():
    # An unknown surface with no caps still returns the baseline brand-impersonation
    # technique from enrich() (since enrich always appends brand_impersonation).
    unknown = enrich_for_surface("nonexistent_surface")
    baseline = enrich([])
    assert set(unknown.techniques) == set(baseline.techniques)


def test_no_duplicate_techniques():
    # email_auth shares T1566.002 with the spearphishing capability; must dedup.
    enriched = enrich_for_surface("email_auth", capabilities=["phishing_page"])
    assert len(enriched.techniques) == len(set(enriched.techniques))


def test_all_surfaces_have_mappings():
    for surface in SURFACE_TECHNIQUES:
        e = enrich_for_surface(surface)
        assert len(e.techniques) >= 1
