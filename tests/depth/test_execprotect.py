"""v07 W9 Gate — executive/VIP protection differential probe.

Two distinct execs => distinct exposure dossiers + redaction sets + doxxing
items + physical threats. VIP registry manages protectees by tier. Live
physical-threat feeds 🔒 BLOCKED-ENV.
"""
from __future__ import annotations

import pytest

from src.execprotect.vip_registry import VipRegistry, Protectee
from src.execprotect.physical_threat import scan_physical_threats
from src.execprotect.doxxing_monitor import scan_doxxing
from src.execprotect.dossier import build_exec_dossier


def test_vip_registry_tiers():
    reg = VipRegistry()
    reg.add(Protectee("Jane Powell", "AcmeBank", "CEO", tier="c_suite"))
    reg.add(Protectee("Raj Mehta", "AcmeBank", "Board Member", tier="board"))
    assert reg.get("jane powell").role == "CEO"
    assert len(reg.by_tier("board")) == 1
    assert len(reg.all()) == 2


def test_two_execs_distinct_dossiers():
    a = build_exec_dossier("Jane Powell", "AcmeBank", "CEO")
    b = build_exec_dossier("Raj Mehta", "Globex", "CFO")
    # Materially different dossiers.
    assert (a.broker_exposure, a.overall_risk, tuple(a.redaction_items)) != \
           (b.broker_exposure, b.overall_risk, tuple(b.redaction_items))
    assert 0.0 <= a.overall_risk <= 1.0 and 0.0 <= b.overall_risk <= 1.0


def test_doxxing_input_dependent():
    a = scan_doxxing("Jane Powell", "AcmeBank")
    b = scan_doxxing("Raj Mehta", "Globex")
    assert a.exposed_items != b.exposed_items or a.severity != b.severity


def test_physical_threats_ranked_by_severity():
    threats = scan_physical_threats("Jane Powell", "AcmeBank")
    sev = [t.severity for t in threats]
    assert sev == sorted(sev, reverse=True)
    for t in threats:
        assert "[synthetic]" in t.snippet  # fixture-backed, synthetic only


def test_physical_threats_live_blocked_env(monkeypatch):
    monkeypatch.setenv("SPOOFVANE_BD_MODE", "live")
    with pytest.raises(NotImplementedError, match="BLOCKED-ENV"):
        scan_physical_threats("Jane Powell", "AcmeBank")


def test_dossier_determinism():
    a1 = build_exec_dossier("Jane Powell", "AcmeBank", "CEO")
    a2 = build_exec_dossier("Jane Powell", "AcmeBank", "CEO")
    assert a1.overall_risk == a2.overall_risk
