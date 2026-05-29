"""Sprint 5 — deepfake/voiceprint C9, C10, D6 (golden-fixture variation §V8-4)."""
from src.deepfake.voiceprint import VoiceprintScorer
from src.deepfake.deepfake_score import DeepfakeScorer
from src.deepfake.multimodal_verdict import fuse


def test_voiceprint_same_clip_matches():
    vp = VoiceprintScorer()
    enr = vp.enroll(b"executive enrolled voice")
    r = vp.score(b"executive enrolled voice", enr)
    assert r.is_match and r.similarity > 0.99


def test_voiceprint_different_clip_does_not_match():
    vp = VoiceprintScorer()
    enr = vp.enroll(b"executive enrolled voice")
    r = vp.score(b"totally different attacker clone", enr)
    assert not r.is_match


def test_voiceprint_deterministic_but_not_constant():
    """§V8-4: same input -> same output; different input -> different output."""
    vp = VoiceprintScorer()
    enr = vp.enroll(b"x")
    a1 = vp.score(b"clipA", enr).similarity
    a2 = vp.score(b"clipA", enr).similarity
    b = vp.score(b"clipB", enr).similarity
    assert a1 == a2          # deterministic
    assert a1 != b           # not constant


def test_deepfake_valid_c2pa_lowers_probability():
    df = DeepfakeScorer()
    no = df.score(b"v", b"a", b"face", None).probability
    yes = df.score(b"v", b"a", b"face", b"a-valid-manifest-blob-here").probability
    assert yes < no


def test_deepfake_contributions_present_and_sum():
    df = DeepfakeScorer()
    r = df.score(b"v", b"a", b"face")
    assert set(r.contributions) == {"face", "lipsync", "provenance"}
    assert abs(sum(r.contributions.values()) - r.probability) < 1e-6 or r.probability == 1.0


def test_deepfake_input_dependent():
    df = DeepfakeScorer()
    probs = {df.score(f"v{i}".encode(), b"a", b"face").probability for i in range(20)}
    assert len(probs) > 10


def test_multimodal_escalates_on_strong_signals():
    df = DeepfakeScorer()
    strong = df.score(b"deepfake-vid", b"aud", b"face")
    vp = VoiceprintScorer(); enr = vp.enroll(b"ceo")
    mism = vp.score(b"cloned", enr)
    mv = fuse(strong, mism, text_context_risk=0.9)
    assert mv.verdict in ("deepfake", "suspicious")
    assert "voice" in mv.modalities_used and "text" in mv.modalities_used


def test_multimodal_authentic_path():
    df = DeepfakeScorer()
    # craft a low-signal case via valid provenance
    low = df.score(b"clean", b"clean", b"face", b"valid-c2pa-manifest-trusted-source")
    mv = fuse(low, None, text_context_risk=0.0)
    assert mv.confidence <= low.probability + 0.01
