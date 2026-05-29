"""VerdictEngine mock fallback: conservative thresholds."""

from datetime import datetime, timedelta, timezone

from src.common.ids import inspection_id, suspect_id
from src.common.models import (
    Brand,
    InspectionResult,
    ScoringResult,
    Verdict,
)
from src.verdict.claude_verdict import VerdictEngine


def _brand() -> Brand:
    return Brand(
        id="brand_test",
        name="TestBrand",
        login_url="https://login.testbrand.example/signin",
        target_country="US",
        score_threshold=0.65,
    )


def _inspection(*, days_old: int) -> InspectionResult:
    return InspectionResult(
        id=inspection_id(),
        suspect_url_id=suspect_id(),
        success=True,
        rendered_country="US",
        registration_date=datetime.now(timezone.utc) - timedelta(days=days_old),
        asn="AS204957",
        registrar="Namecheap",
    )


def _scoring(composite: float) -> ScoringResult:
    return ScoringResult(
        inspection_id="i",
        phash_score=composite,
        dom_score=composite,
        logo_score=composite,
        favicon_match=False,
        composite_score=composite,
        above_threshold=composite >= 0.65,
    )


def test_phish_when_strong_match_and_new_domain() -> None:
    v = VerdictEngine().decide(_brand(), _inspection(days_old=3), _scoring(0.92), b"")
    assert v.verdict == Verdict.PHISH


def test_suspicious_when_above_threshold_but_not_phish_signal() -> None:
    v = VerdictEngine().decide(_brand(), _inspection(days_old=400), _scoring(0.70), b"")
    assert v.verdict == Verdict.SUSPICIOUS


def test_benign_when_below_threshold() -> None:
    v = VerdictEngine().decide(_brand(), _inspection(days_old=400), _scoring(0.20), b"")
    assert v.verdict == Verdict.BENIGN


def test_takedown_draft_is_marked_draft() -> None:
    v = VerdictEngine().decide(_brand(), _inspection(days_old=3), _scoring(0.92), b"")
    assert "DRAFT" in v.takedown_draft.upper()
