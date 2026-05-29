"""Sprint 8 — delivery F4, F5(XSOAR), F8 (review §8 group F)."""
from src.delivery.takedown.hosting_abuse import HostingAbuseReporter, host_from_asn, ABUSE_CHANNELS
from src.delivery.cortex_xsoar import CortexXsoarSink, SEVERITY_MAP
from src.delivery.bd_mcp_client import BdMcpClient
from src.integrations.brightdata import get_cost_tracker


def test_hosting_abuse_routes_by_asn_org():
    assert host_from_asn("Amazon AWS") == "aws"
    assert host_from_asn("OVH SAS") == "ovh"
    assert host_from_asn("Hetzner Online GmbH") == "hetzner"
    assert host_from_asn("Google LLC") == "gcp"
    assert host_from_asn("Unknown ISP") == "cloudflare"  # default


def test_hosting_abuse_requires_hitl_to_submit():
    r1 = HostingAbuseReporter().submit("https://e.top", "Hetzner")
    r2 = HostingAbuseReporter().submit("https://e.top", "Hetzner", hitl_approved=True)
    assert r1.submitted is False and r2.submitted is True
    assert r2.channel == ABUSE_CHANNELS["hetzner"]


def test_xsoar_severity_mapping():
    assert CortexXsoarSink().create_incident({"url": "x", "verdict": "phish"}).severity == 3
    assert CortexXsoarSink().create_incident({"url": "x", "verdict": "benign"}).severity == 1


def test_xsoar_dedup_stable():
    a = CortexXsoarSink().create_incident({"url": "https://e.top", "verdict": "phish"})
    b = CortexXsoarSink().create_incident({"url": "https://e.top", "verdict": "phish"})
    assert a.dedup_key == b.dedup_key and a.incident_id == b.incident_id


def test_bd_mcp_client_tracks_cost():
    t = get_cost_tracker(); t.reset()
    m = BdMcpClient(tenant_id="mt").render_markdown("https://e.top")
    assert m.ok and m.rendered_via == "brightdata_mcp"
    assert "mcp_server" in t.product_breakdown()


def test_bd_mcp_two_tools():
    c = BdMcpClient()
    r1 = c.render_markdown("https://a.top")
    r2 = c.search_engine("acme login")
    assert r1.tool == "scrape_as_markdown" and r2.tool == "search_engine"
