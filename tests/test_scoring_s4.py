"""Sprint 4 — scoring C1, C2, C6, C8 (review §8 group C)."""
from src.scoring.url_risk import UrlRiskScorer, shannon_entropy
from src.scoring.kit_signatures_ext import all_kit_names, fingerprint_extended, EXTENDED_KITS
from src.scoring.cluster import ThreatClusterer, ClusterNode
from src.scoring.calibration import calibrate, PlattCalibrator


# --- C2 URL risk ---
def test_url_risk_higher_for_phishy_url():
    s = UrlRiskScorer()
    bad = s.score("https://acme-secure-login-verify.top/account", age_days=3)
    good = s.score("https://acme.com/login", age_days=4000)
    assert bad.score > good.score
    assert bad.suspicious_tokens
    assert "tokens" in bad.contributions


def test_url_risk_detects_punycode_and_ip():
    s = UrlRiskScorer()
    assert s.score("https://xn--80ak6aa92e.com/login").has_punycode
    assert s.score("http://192.168.10.5/login").has_ip_host


def test_url_risk_contributions_sum_to_score():
    s = UrlRiskScorer()
    r = s.score("https://verify-acct.xyz/login", age_days=10)
    assert abs(sum(r.contributions.values()) - r.score) < 1e-6 or r.score == 1.0


def test_entropy_monotonic():
    assert shannon_entropy("aaaa") < shannon_entropy("a8x2k9qz")


# --- C6 kit signatures (>=12) ---
def test_at_least_twelve_kits():
    assert len(all_kit_names()) >= 12
    assert len(set(all_kit_names())) == len(all_kit_names())  # unique


def test_js_bundle_hash_is_high_confidence():
    kit = EXTENDED_KITS[0]
    m = fingerprint_extended("nothing here", list(kit.js_bundle_hashes))
    assert m and m[0].confidence >= 0.95 and m[0].matched_on == "js_bundle_hash"


def test_dom_plus_css_match():
    m = fingerprint_extended("page has frappo and frp_dashboard plus frp-cc class")
    names = {x.kit for x in m}
    assert "Frappo" in names


# --- C8 clustering ---
def test_clustering_links_shared_signals():
    c = ThreatClusterer()
    c.add(ClusterNode("a", asn="AS200651", kit="EvilProxy"))
    c.add(ClusterNode("b", asn="AS200651"))
    c.add(ClusterNode("c", kit="EvilProxy"))
    c.add(ClusterNode("solo", asn="AS1"))
    clusters = c.cluster()
    assert len(clusters) == 1
    assert set(clusters[0].members) == {"a", "b", "c"}
    assert clusters[0].risk > 0.5


def test_clustering_ignores_singletons():
    c = ThreatClusterer()
    c.add(ClusterNode("x", asn="AS1"))
    c.add(ClusterNode("y", asn="AS2"))
    assert c.cluster() == []


# --- C1 calibration ---
def test_calibration_is_monotonic_probability():
    probs = [calibrate(r, {}).probability for r in (0.1, 0.3, 0.5, 0.7, 0.9)]
    assert probs == sorted(probs)
    assert all(0.0 <= p <= 1.0 for p in probs)


def test_calibration_not_raw_passthrough():
    cs = calibrate(0.5, {"a": 0.5})
    assert cs.probability != cs.raw_score  # genuine transform, not identity


def test_calibration_fit_shifts_curve():
    c = PlattCalibrator()
    before = c.probability(0.85)
    c.fit([(0.1, 0), (0.2, 0), (0.85, 1), (0.9, 1)] * 5)
    after = c.probability(0.85)
    assert before != after
