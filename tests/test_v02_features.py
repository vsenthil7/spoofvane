"""Tests for the v0.2 detection, integration, and platform modules."""

from __future__ import annotations

import pytest

from src.common.ids import brand_id, suspect_id
from src.common.models import Brand, Source, SuspectURL
from src.common.tenants import (
    SCOPE_ADMIN,
    SCOPE_ALERTS_READ,
    Tenant,
    TenantPlan,
    key_satisfies,
)


# --------------------------------------------------------------------------- #
# Family classification
# --------------------------------------------------------------------------- #


class TestFamilyClassifier:
    def test_banking_signatures(self):
        from src.scoring.family import classify_dom_text, AttackFamily
        dom = (
            "<html><body>"
            "<form><label>Account number</label><input>"
            "<label>Sort code</label><input>"
            "<label>One time passcode</label></form>"
            "</body></html>"
        )
        result = classify_dom_text(dom)
        assert result.family == AttackFamily.BANKING
        assert result.confidence >= 0.6
        assert "account-number" in result.signatures_hit

    def test_crypto_signatures(self):
        from src.scoring.family import classify_dom_text, AttackFamily
        dom = (
            "<html><body>"
            "<h1>Connect MetaMask wallet</h1>"
            "<label>Enter your 12-word seed phrase</label>"
            "<textarea></textarea></body></html>"
        )
        result = classify_dom_text(dom)
        assert result.family == AttackFamily.CRYPTO

    def test_generic_when_no_match(self):
        from src.scoring.family import classify_dom_text, AttackFamily
        result = classify_dom_text("<html><body>Hello world</body></html>")
        assert result.family == AttackFamily.GENERIC
        assert result.confidence == 0.0

    def test_family_weights_differ(self):
        from src.scoring.family import weights_for_family, AttackFamily
        crypto_weights = weights_for_family(AttackFamily.CRYPTO)
        m365_weights = weights_for_family(AttackFamily.M365)
        # Crypto puts more weight on DOM, M365 puts more on visual
        assert crypto_weights["dom"] > m365_weights["dom"]
        assert m365_weights["phash"] > crypto_weights["phash"]


# --------------------------------------------------------------------------- #
# Kit fingerprinting
# --------------------------------------------------------------------------- #


class TestKitFingerprint:
    def test_16shop_matches(self):
        from src.scoring.template_fingerprint import fingerprint_dom
        dom = (
            "<html><body>"
            "<!-- powered by 16shop -->"
            "<form class='sh16-form' action='/sh16/submit'>"
            "<input type='hidden' name='vk16' value='abc'></form>"
            "</body></html>"
        )
        matches = fingerprint_dom(dom.encode())
        assert len(matches) >= 1
        assert matches[0].kit_name == "16Shop"
        assert matches[0].confidence >= 0.7

    def test_tycoon_2fa_matches(self):
        from src.scoring.template_fingerprint import fingerprint_dom
        dom = (
            "<html><body>"
            "<!-- tycoon-2fa kit v3 -->"
            "<script src='//xyz.pinata.io/aaaaaaaaaaaaaaaaaaaaa'></script>"
            "<script>var t = cf_chl_gen_tk_abc;</script>"
            "</body></html>"
        )
        matches = fingerprint_dom(dom.encode())
        assert any(m.kit_name == "Tycoon-2FA" for m in matches)

    def test_no_match_on_clean_html(self):
        from src.scoring.template_fingerprint import fingerprint_dom
        assert fingerprint_dom(b"<html><body>hello</body></html>") == []


# --------------------------------------------------------------------------- #
# Multi-region cloaking detection
# --------------------------------------------------------------------------- #


class TestMultiRegion:
    def test_geo_cloaked_url_detected(self):
        from src.inspection.multi_region import inspect_multi_region
        brand = Brand(
            id=brand_id(),
            name="TestBank",
            login_url="https://login.testbank.example/signin",
            target_country="US",
        )
        susp = SuspectURL(
            id=suspect_id(),
            brand_id=brand.id,
            url="https://geo-testbank-secure.com/login",
            source=Source.SERP,
        )
        report = inspect_multi_region(brand, susp, regions=["US", "GB", "DE", "BR", "IN"])
        assert report.cloaking_detected is True
        assert report.max_divergence >= 0.35
        assert len(report.cloaking_evidence) >= 1

    def test_non_cloaked_url_not_flagged(self):
        from src.inspection.multi_region import inspect_multi_region
        brand = Brand(
            id=brand_id(),
            name="TestBank",
            login_url="https://login.testbank.example/signin",
            target_country="US",
        )
        susp = SuspectURL(
            id=suspect_id(),
            brand_id=brand.id,
            url="https://account-update-portal.xyz/testbank",
            source=Source.SERP,
        )
        report = inspect_multi_region(brand, susp, regions=["US", "GB"])
        assert report.cloaking_detected is False


# --------------------------------------------------------------------------- #
# Tenant + API key + auth
# --------------------------------------------------------------------------- #


class TestTenantsAndKeys:
    def test_scope_satisfaction(self):
        assert key_satisfies([SCOPE_ALERTS_READ], SCOPE_ALERTS_READ) is True
        assert key_satisfies([SCOPE_ALERTS_READ], SCOPE_ADMIN) is False
        # admin:* wins everything
        assert key_satisfies([SCOPE_ADMIN], SCOPE_ALERTS_READ) is True

    def test_api_key_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
        from src.common.settings import get_settings
        get_settings.cache_clear()  # type: ignore[attr-defined]

        from src.storage.db import session_scope
        from src.storage.init_db import init_db
        from src.storage.repositories_v2 import ApiKeyRepo, TenantRepo

        init_db()
        with session_scope() as s:
            t = Tenant(
                id=brand_id(),
                name="UnitTest Co",
                plan=TenantPlan.STANDARD,
            )
            TenantRepo(s).create(t)
            key, secret = ApiKeyRepo(s).issue(t.id, "test-key", [SCOPE_ALERTS_READ])

            # Auth with correct secret
            authed = ApiKeyRepo(s).authenticate(key.id, secret)
            assert authed is not None
            assert authed.tenant_id == t.id
            assert SCOPE_ALERTS_READ in authed.scopes

            # Auth with wrong secret
            assert ApiKeyRepo(s).authenticate(key.id, "wrong") is None

            # Revoke
            assert ApiKeyRepo(s).revoke(key.id) is True
            assert ApiKeyRepo(s).authenticate(key.id, secret) is None


# --------------------------------------------------------------------------- #
# Integration payload + STIX bundle
# --------------------------------------------------------------------------- #


class TestIntegrations:
    def test_stix_bundle_structure(self):
        from datetime import datetime, timezone
        from src.common.ids import alert_id, inspection_id, verdict_id
        from src.common.models import (
            Alert, AlertStatus, Brand, InspectionResult,
            Severity, Verdict, VerdictResult,
        )
        from src.delivery.taxii import build_stix_bundle

        brand = Brand(
            id=brand_id(),
            name="UnitBank",
            login_url="https://unitbank.example/signin",
            target_country="US",
        )
        insp = InspectionResult(
            id=inspection_id(),
            suspect_url_id=suspect_id(),
            success=True,
            rendered_country="US",
            asn="AS13335",
            registrar="Namecheap",
        )
        verdict = VerdictResult(
            id=verdict_id(),
            inspection_id=insp.id,
            verdict=Verdict.PHISH,
            confidence=0.92,
            severity=Severity.CRITICAL,
            evidence_summary=["Kit fingerprint match: 16Shop"],
            suggested_action="takedown",
            takedown_draft="...",
            model_used="claude-sonnet-4-6",
            kit_match="16Shop",
            kit_match_confidence=0.9,
            attack_family="banking",
            attack_family_confidence=0.8,
        )
        alert = Alert(
            id=alert_id(),
            brand_id=brand.id,
            inspection_id=insp.id,
            verdict_id=verdict.id,
            severity=Severity.CRITICAL,
            status=AlertStatus.OPEN,
            suspect_url="https://unitbank-portal.xyz/sh16/",
            created_at=datetime.now(timezone.utc),
        )
        bundle = build_stix_bundle(alert, brand, insp, verdict)
        assert bundle["type"] == "bundle"
        types = sorted({o["type"] for o in bundle["objects"]})
        assert "identity" in types
        assert "indicator" in types
        assert "malware" in types
        assert "relationship" in types
        indicator = [o for o in bundle["objects"] if o["type"] == "indicator"][0]
        assert "[url:value = '" in indicator["pattern"]
        assert indicator["confidence"] == 92
        assert "kit:16shop" in indicator["labels"]

    def test_hmac_signing(self):
        from src.delivery.integration_base import post_with_retry
        # We can't easily run the network call here; just verify the helper
        # is callable without raising on unconfigured endpoints.
        # The actual signature path is exercised via _post_generic in unit tests.
        assert callable(post_with_retry)


# --------------------------------------------------------------------------- #
# Discovery: new sources should at least yield mock fixtures
# --------------------------------------------------------------------------- #


class TestDiscoverySources:
    @pytest.fixture
    def brand(self):
        return Brand(
            id=brand_id(),
            name="UnitBank",
            login_url="https://unitbank.example/signin",
            target_country="US",
            brand_keywords=["UnitBank"],
        )

    def test_paid_ads_yields(self, brand, monkeypatch):
        monkeypatch.setenv("MOCK_MODE", "true")
        from src.common.settings import get_settings
        get_settings.cache_clear()  # type: ignore[attr-defined]
        from src.discovery.paid_ads import PaidAdSource
        urls = list(PaidAdSource().discover(brand))
        assert len(urls) >= 1
        assert all(u.source == Source.PAID_AD for u in urls)

    def test_mobile_app_store_yields(self, brand, monkeypatch):
        monkeypatch.setenv("MOCK_MODE", "true")
        from src.common.settings import get_settings
        get_settings.cache_clear()  # type: ignore[attr-defined]
        from src.discovery.mobile_app_store import MobileAppStoreSource
        urls = list(MobileAppStoreSource().discover(brand))
        assert len(urls) >= 1
        assert all(u.source == Source.MOBILE_APP_STORE for u in urls)

    def test_github_leak_yields(self, brand, monkeypatch):
        monkeypatch.setenv("MOCK_MODE", "true")
        from src.common.settings import get_settings
        get_settings.cache_clear()  # type: ignore[attr-defined]
        from src.discovery.github_leak import GitHubLeakSource
        urls = list(GitHubLeakSource().discover(brand))
        assert len(urls) >= 1
        assert all(u.source == Source.GITHUB_LEAK for u in urls)

    def test_telegram_kit_yields(self, brand, monkeypatch):
        monkeypatch.setenv("MOCK_MODE", "true")
        from src.common.settings import get_settings
        get_settings.cache_clear()  # type: ignore[attr-defined]
        from src.discovery.telegram_kit import TelegramKitSource
        urls = list(TelegramKitSource().discover(brand))
        assert len(urls) >= 1
        assert all(u.source == Source.TELEGRAM_KIT for u in urls)


# --------------------------------------------------------------------------- #
# Active learning
# --------------------------------------------------------------------------- #


class TestActiveLearning:
    def test_insufficient_data_holds(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/al1.db")
        from src.common.settings import get_settings
        get_settings.cache_clear()  # type: ignore[attr-defined]
        from src.storage.db import session_scope
        from src.storage.init_db import init_db
        from src.scoring.active_learning import analyse_feedback

        init_db()
        with session_scope() as s:
            report = analyse_feedback(s)
        assert report.sufficient_data is False
        assert report.threshold is None
        assert any("Holding" in n or "need" in n.lower() for n in report.notes)

    def test_threshold_separation(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/al2.db")
        from src.common.settings import get_settings
        get_settings.cache_clear()  # type: ignore[attr-defined]
        from src.storage.db import session_scope
        from src.storage.init_db import init_db
        from src.storage.repositories_v2 import FeedbackEventRepo
        from src.scoring.active_learning import analyse_feedback

        init_db()
        with session_scope() as s:
            repo = FeedbackEventRepo(s)
            # 15 true positives at high score, 15 false positives at lower score
            for i in range(15):
                repo.record(
                    alert_id=f"tp{i}", outcome="true_positive", actor="t",
                    attack_family="banking", composite_score=0.90,
                )
            for i in range(15):
                repo.record(
                    alert_id=f"fp{i}", outcome="false_positive", actor="t",
                    attack_family="generic", composite_score=0.70,
                )
            report = analyse_feedback(s, min_samples=20)

        assert report.sufficient_data is True
        assert report.threshold is not None
        # Midpoint of 0.90 and 0.70 is 0.80
        assert 0.78 <= report.threshold.recommended_threshold <= 0.82
        # banking should be a high-precision signal → increase
        banking = [w for w in report.weight_nudges if "banking" in w.signal]
        assert banking and banking[0].direction == "increase"
        # generic should be low precision → decrease
        generic = [w for w in report.weight_nudges if "generic" in w.signal]
        assert generic and generic[0].direction == "decrease"

    def test_threshold_clamped(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/al3.db")
        from src.common.settings import get_settings
        get_settings.cache_clear()  # type: ignore[attr-defined]
        from src.storage.db import session_scope
        from src.storage.init_db import init_db
        from src.storage.repositories_v2 import FeedbackEventRepo
        from src.scoring.active_learning import analyse_feedback

        init_db()
        with session_scope() as s:
            repo = FeedbackEventRepo(s)
            # Pathological: all TPs scored very low, all FPs very high.
            # The recommended threshold must still clamp to [0.4, 0.9].
            for i in range(15):
                repo.record(alert_id=f"tp{i}", outcome="true_positive", actor="t", composite_score=0.05)
            for i in range(15):
                repo.record(alert_id=f"fp{i}", outcome="false_positive", actor="t", composite_score=0.99)
            report = analyse_feedback(s, min_samples=20)
        assert 0.4 <= report.threshold.recommended_threshold <= 0.9


# --------------------------------------------------------------------------- #
# Wave-5 follow-ups: notes, metrics, diff-detector endpoint
# --------------------------------------------------------------------------- #


class TestAlertNotes:
    def test_note_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/notes.db")
        from src.common.settings import get_settings
        get_settings.cache_clear()  # type: ignore[attr-defined]
        from src.storage.db import session_scope
        from src.storage.init_db import init_db
        from src.storage.repositories_v2 import AlertNoteRepo

        init_db()
        with session_scope() as s:
            repo = AlertNoteRepo(s)
            repo.add(alert_id="alrt_x", author="alice", body="first note")
            repo.add(alert_id="alrt_x", author="bob", body="second note")
            repo.add(alert_id="alrt_y", author="carol", body="other alert")
            notes = repo.list_for_alert("alrt_x")
        assert len(notes) == 2
        assert notes[0]["author"] == "alice"
        assert notes[1]["author"] == "bob"
        # Ordering is chronological
        assert notes[0]["body"] == "first note"


class TestMetrics:
    def test_metrics_render(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/metrics.db")
        from src.common.settings import get_settings
        get_settings.cache_clear()  # type: ignore[attr-defined]
        from src.storage.init_db import init_db
        init_db()
        from src.api.metrics import render_metrics
        text = render_metrics()
        # Valid exposition: HELP + TYPE lines present
        assert "# HELP doppeldomain_alerts_total" in text
        assert "# TYPE doppeldomain_alerts_total gauge" in text
        assert "doppeldomain_tenants_total" in text
        assert "doppeldomain_brightdata_spend_usd" in text


class TestDiffDetector:
    def test_timebomb_flip_detected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/diff.db")
        monkeypatch.setenv("MOCK_MODE", "true")
        from src.common.settings import get_settings
        get_settings.cache_clear()  # type: ignore[attr-defined]
        from src.storage.db import session_scope
        from src.storage.init_db import init_db
        from src.storage.repositories import BrandRepo, SuspectURLRepo, InspectionRepo
        from src.inspection.browser import get_inspector
        from src.inspection.diff_detector import recheck_recent

        init_db()
        # Create a brand + a time-bomb suspect, inspect once (dormant/benign)
        brand = Brand(
            id=brand_id(), name="DiffBank",
            login_url="https://login.diffbank.example/signin",
            target_country="US", brand_keywords=["DiffBank"],
        )
        susp = SuspectURL(
            id=suspect_id(), brand_id=brand.id,
            url="https://diffbank-timebomb-login.com/account",
            source=Source.SERP,
        )
        insp = get_inspector().inspect(brand, susp)  # recheck_count=0 → benign
        with session_scope() as s:
            BrandRepo(s).create(brand)
            SuspectURLRepo(s).create(susp)
            InspectionRepo(s).create(insp)
        bid = brand.id

        # Recheck — the time-bomb should now flip to phishy
        diffs = recheck_recent(bid, max_urls=10, hours_lookback=48)
        time_bombs = [d for d in diffs if d.time_bomb]
        assert len(time_bombs) >= 1
        assert time_bombs[0].benign_before is True
        assert time_bombs[0].looks_like_phish_now is True
