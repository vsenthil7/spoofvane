"""v06 §F Gate 7 — OSINT exec-protection differential probe.

Two materially different exec inputs MUST produce two materially different,
correct outputs across every source. Includes negative cases and the ONNX
runner BLOCKED-ENV status check.
"""
from __future__ import annotations

import pytest

from src.osint.base import ExecInput
from src.osint.edgar import EdgarSource
from src.osint.linkedin_public import LinkedInPublicSource
from src.osint.transcripts import TranscriptsSource
from src.osint.data_broker import DataBrokerSource
from src.osint.redaction import RedactionRecommender
from src.osint.impersonation_graph import build_graph
from src.deepfake.onnx_runner import status as onnx_status

EXEC_A = ExecInput(name="Jane Powell", company="AcmeBank", role="CEO", domain="acmebank.com")
EXEC_B = ExecInput(name="Raj Mehta", company="Globex", role="CFO", domain="globex.com")


def test_edgar_input_dependent():
    a = EdgarSource().lookup(EXEC_A)
    b = EdgarSource().lookup(EXEC_B)
    assert a.cik != b.cik
    assert a.company == "AcmeBank" and b.company == "Globex"
    # Deterministic: same input -> same output.
    assert EdgarSource().lookup(EXEC_A).cik == a.cik


def test_linkedin_input_dependent():
    a = LinkedInPublicSource().enrich(EXEC_A)
    b = LinkedInPublicSource().enrich(EXEC_B)
    assert (a.public_connections, a.impersonation_risk) != (b.public_connections, b.impersonation_risk)


def test_transcripts_input_dependent():
    # Two execs with distinct public-audio footprints (the voice-clone surface).
    exec_c = ExecInput(name="Sara Lin", company="Initech", role="CTO")
    exec_d = ExecInput(name="Tom Reed", company="Hooli", role="CEO")
    a = TranscriptsSource().search(exec_c)
    b = TranscriptsSource().search(exec_d)
    assert a.total_public_audio_minutes != b.total_public_audio_minutes
    assert a.total_public_audio_minutes > 0 and b.total_public_audio_minutes > 0
    # Negative: an exec with no public audio is a valid (zero-risk) result.
    quiet = TranscriptsSource().search(EXEC_A)
    assert quiet.total_public_audio_minutes == 0 and quiet.hits == []


def test_data_broker_distinct_exposure():
    a = DataBrokerSource().check(EXEC_A)
    b = DataBrokerSource().check(EXEC_B)
    assert a.all_exposed_fields != b.all_exposed_fields or a.exposure_score != b.exposure_score


def test_redaction_two_execs_two_distinct_plans():
    """Core Gate 7 assertion: distinct execs -> distinct redaction sets."""
    a = RedactionRecommender().recommend(EXEC_A)
    b = RedactionRecommender().recommend(EXEC_B)
    assert a.ranked_items != b.ranked_items or a.overall_exposure != b.overall_exposure
    # Plans are ranked highest-priority first.
    prios = [i.priority for i in a.items]
    assert prios == sorted(prios, reverse=True)


def test_impersonation_graph_two_seeds_two_graphs():
    g1 = build_graph(EXEC_A, "fake_profile_001")
    g2 = build_graph(EXEC_A, "fake_profile_002")
    # Two distinct fake-profile seeds -> two distinct graphs.
    assert g1.node_ids() != g2.node_ids()
    # Each graph is well-formed: fake_profile -> domain -> {host,registrar,kit}.
    kinds = {n.kind for n in g1.nodes}
    assert kinds == {"fake_profile", "domain", "host", "registrar", "kit"}
    assert len(g1.edges) == 4


def test_negative_same_exec_same_graph_is_deterministic():
    g1 = build_graph(EXEC_B, "seedX")
    g2 = build_graph(EXEC_B, "seedX")
    assert g1.node_ids() == g2.node_ids()


def test_onnx_runner_blocked_env_status():
    """ONNX is honestly BLOCKED-ENV by default (no weights/flag) — not 'done'."""
    st = onnx_status()
    assert st.usable is False
    assert "BLOCKED-ENV" in st.reason
