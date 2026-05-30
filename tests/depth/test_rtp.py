"""v07 W8 Gate — real-time protection + decoy differential probe.

A beacon from a foreign origin opens an alert; a same-origin event does not;
two victims on the same fake URL aggregate into one incident with count=2;
markered decoy credentials are traceable on reuse. (v07 acceptance gate 5.)
"""
from __future__ import annotations

import pytest

from src.rtp.beacon_ingest import ingest_beacon, BeaconEvent
from src.rtp.clone_detector import detect_clone
from src.rtp.victim_tracker import VictimTracker
from src.rtp.decoy_engine import DecoyEngine


def test_foreign_origin_opens_alert_same_origin_does_not():
    foreign = ingest_beacon({
        "site": "https://acmebank.com", "origin": "https://acme-login.top",
        "fingerprint": "dev1", "ts": "2026-05-30T00:00:00Z", "cluster": "kit_A",
    })
    same = ingest_beacon({
        "site": "https://acmebank.com", "origin": "https://acmebank.com",
        "fingerprint": "dev2", "ts": "2026-05-30T00:01:00Z",
    })
    fv = detect_clone(foreign)
    sv = detect_clone(same)
    assert fv.opens_alert is True and fv.is_clone is True and fv.risk > 0
    assert sv.opens_alert is False and sv.is_clone is False and sv.risk == 0.0


def test_two_victims_one_incident_count_two():
    tracker = VictimTracker()
    e1 = ingest_beacon({"site": "https://acmebank.com", "origin": "https://acme-login.top",
                        "fingerprint": "victimA", "ts": "t1", "cluster": "kit_A"})
    e2 = ingest_beacon({"site": "https://acmebank.com", "origin": "https://acme-login.top",
                        "fingerprint": "victimB", "ts": "t2", "cluster": "kit_A"})
    tracker.record(e1)
    inc = tracker.record(e2)
    assert inc.victim_count == 2
    assert inc.magnitude == "medium"
    assert len(tracker.incidents()) == 1  # both collapse into one incident


def test_same_victim_not_double_counted():
    tracker = VictimTracker()
    e = ingest_beacon({"site": "https://acmebank.com", "origin": "https://acme-login.top",
                       "fingerprint": "victimA", "ts": "t1", "cluster": "kit_A"})
    tracker.record(e)
    tracker.record(e)  # same fingerprint
    assert tracker.incidents()[0].victim_count == 1


def test_victim_tracker_rejects_same_origin():
    tracker = VictimTracker()
    same = ingest_beacon({"site": "https://acmebank.com", "origin": "https://acmebank.com",
                          "fingerprint": "x", "ts": "t"})
    with pytest.raises(ValueError):
        tracker.record(same)


def test_decoy_issue_and_reuse_detection():
    eng = DecoyEngine()
    cred = eng.issue("kit_A")
    assert cred.username.endswith("@decoy.local")
    assert eng.is_decoy(cred.username) is True
    # Attacker reuses the decoy -> traces back to the issuing cluster.
    traced = eng.detect_reuse(cred.username)
    assert traced is not None and traced.issued_for_cluster == "kit_A"
    # A real (non-decoy) credential is not flagged.
    assert eng.is_decoy("realuser@acmebank.com") is False


def test_beacon_ingest_validation():
    with pytest.raises(ValueError):
        ingest_beacon({"site": "", "origin": "https://x.top"})
    # Fingerprint is hashed, never stored raw.
    ev = ingest_beacon({"site": "https://a.com", "origin": "https://b.top", "fingerprint": "raw-device-id"})
    assert ev.fingerprint != "raw-device-id"
    assert len(ev.fingerprint) == 16
