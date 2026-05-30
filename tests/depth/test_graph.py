"""v07 W12 Gate — threat-actor / campaign graph differential probe.

Two fake domains sharing one TLS cert + kit family collapse into ONE campaign;
an unrelated domain stays separate; pivot from a cert returns all linked
entities. (v07 acceptance gate 4: graph correlation.)
"""
from __future__ import annotations

from src.graph.entity_model import Finding, NodeType, Node
from src.graph.edge_builder import build_graph
from src.graph.campaign_detector import detect_campaigns
from src.graph.pivot_engine import pivot

# Two findings sharing cert + kit; one unrelated finding.
SHARED_CERT = "sha256:abc123"
FINDINGS = [
    Finding("f1", domain="acme-login.top", cert_sha=SHARED_CERT, kit_family="m365",
            registrar="Namecheap", actor="actorX", surface="domain"),
    Finding("f2", domain="acme-verify.xyz", cert_sha=SHARED_CERT, kit_family="m365",
            registrar="Namecheap", surface="domain"),
    Finding("f3", domain="totally-unrelated.com", cert_sha="sha256:zzz999",
            kit_family="banking", registrar="GoDaddy", surface="domain"),
]


def test_shared_infra_collapses_into_one_campaign():
    campaigns = detect_campaigns(FINDINGS)
    # The two acme domains sharing cert+kit must be in the same campaign.
    acme_campaign = next(c for c in campaigns if "acme-login.top" in c.domains)
    assert "acme-verify.xyz" in acme_campaign.domains
    assert "totally-unrelated.com" not in acme_campaign.domains
    # The unrelated domain is its own campaign.
    assert any("totally-unrelated.com" in c.domains and len(c.domains) == 1
               for c in campaigns)


def test_unrelated_stays_separate():
    campaigns = detect_campaigns(FINDINGS)
    # At least 2 distinct campaigns (the acme cluster + the unrelated one).
    assert len(campaigns) >= 2


def test_pivot_from_cert_returns_linked_entities():
    g = build_graph(FINDINGS)
    cert_node = Node(NodeType.CERT, SHARED_CERT).id
    result = pivot(g, cert_node, depth=2)
    # Pivoting from the shared cert reaches both acme domains.
    found = set(result["found"])
    assert "domain:acme-login.top" in found
    assert "domain:acme-verify.xyz" in found
    # Should NOT reach the unrelated domain (different cert).
    assert "domain:totally-unrelated.com" not in found


def test_two_finding_sets_distinct_graphs():
    g1 = build_graph(FINDINGS)
    g2 = build_graph([Finding("g1", domain="other.com", cert_sha="sha256:diff")])
    assert g1.node_ids() != g2.node_ids()


def test_graph_dedups_edges():
    # Same finding twice must not duplicate edges.
    g = build_graph([FINDINGS[0], FINDINGS[0]])
    keys = [e.key() for e in g.edges]
    assert len(keys) == len(set(keys))


def test_pivot_unknown_node_empty():
    g = build_graph(FINDINGS)
    result = pivot(g, "cert:nonexistent")
    assert result["found"] == []
