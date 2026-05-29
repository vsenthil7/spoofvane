"""Branch-coverage tests for notification prefs/email, review queries, deps."""
from __future__ import annotations

import pytest

from src.common import notifications, review
from src.common.identity import authenticate_password, signup
from src.common.rbac import Tier
from src.storage import models as orm
from src.storage.db import session_scope
from src.storage.identity_models import ReviewItemRow
from src.storage.init_db import init_db


@pytest.fixture(scope="module", autouse=True)
def _schema():
    init_db()


def _user_account(email):
    with session_scope() as s:
        au = signup(s, email=email, password="password123", tier=Tier.BUSINESS)
        return au.user_id, au.account_id


# ───────────────────── Notification preference branches ─────────────────

class TestNotificationBranches:
    def test_default_pref_emails_on_warning(self):
        uid, acct = _user_account("nb1@x.example")
        with session_scope() as s:
            recips = notifications._recipients(
                s, account_id=acct, kind="detection", severity="warning", user_id=None)
            assert any("nb1@x.example" == r for r in recips)

    def test_default_pref_skips_info(self):
        uid, acct = _user_account("nb2@x.example")
        with session_scope() as s:
            recips = notifications._recipients(
                s, account_id=acct, kind="detection", severity="info", user_id=None)
            assert "nb2@x.example" not in recips

    def test_explicit_pref_email_off(self):
        uid, acct = _user_account("nb3@x.example")
        with session_scope() as s:
            notifications.set_pref(s, user_id=uid, account_id=acct, kind="detection",
                                   email=False, min_severity="info")
            recips = notifications._recipients(
                s, account_id=acct, kind="detection", severity="critical", user_id=None)
            assert "nb3@x.example" not in recips

    def test_explicit_pref_email_on_above_threshold(self):
        uid, acct = _user_account("nb4@x.example")
        with session_scope() as s:
            notifications.set_pref(s, user_id=uid, account_id=acct, kind="detection",
                                   email=True, min_severity="critical")
            # warning is below threshold -> not emailed
            r_warn = notifications._recipients(
                s, account_id=acct, kind="detection", severity="warning", user_id=None)
            assert "nb4@x.example" not in r_warn
            # critical meets threshold -> emailed
            r_crit = notifications._recipients(
                s, account_id=acct, kind="detection", severity="critical", user_id=None)
            assert "nb4@x.example" in r_crit

    def test_email_enabled_smtp_path_handles_failure(self, monkeypatch):
        # Turn email on but point SMTP at an unroutable host; _maybe_email must
        # swallow the error (logged, not raised).
        uid, acct = _user_account("nb5@x.example")
        monkeypatch.setenv("EMAIL_ENABLED", "true")
        monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
        monkeypatch.setenv("SMTP_PORT", "1")  # nothing listening
        from src.common import settings as smod
        smod.get_settings.cache_clear()
        try:
            with session_scope() as s:
                nid = notifications.notify(
                    s, account_id=acct, kind="sla_breach", title="Crit",
                    severity="critical", user_id=uid, send_email=True)
                assert nid  # did not raise despite SMTP failure
        finally:
            monkeypatch.setenv("EMAIL_ENABLED", "false")
            smod.get_settings.cache_clear()

    def test_account_wide_notification_no_user(self):
        uid, acct = _user_account("nb6@x.example")
        with session_scope() as s:
            notifications.notify(s, account_id=acct, kind="system_error",
                                 title="Sys", severity="warning", user_id=None,
                                 send_email=False)
            items = notifications.list_for_user(s, user_id=uid, account_id=acct)
            assert any(i["title"] == "Sys" for i in items)


# ─────────────────────────── Review query branches ──────────────────────

class TestReviewBranches:
    def _enqueue(self, acct):
        with session_scope() as s:
            return review.enqueue_for_review(
                s, account_id=acct, alert_id="a1", suspect_url="https://e.example",
                ai_verdict="phish", ai_confidence=0.9, severity="critical",
                verdict_id="verd_x", brand_id="brand_x").id

    def test_escalate_path(self):
        uid, acct = _user_account("rb1@x.example")
        rid = self._enqueue(acct)
        with session_scope() as s:
            res = review.decide(s, review_id=rid, decision="escalate",
                                decided_by=uid, actor_email="rb1@x.example")
            assert res["state"] == "escalated"
            assert res["takedown_eligible"] is False

    def test_assign_and_list_filter(self):
        uid, acct = _user_account("rb2@x.example")
        rid = self._enqueue(acct)
        with session_scope() as s:
            review.assign(s, review_id=rid, assignee_user_id=uid, actor_email="rb2@x.example")
            mine = review.list_queue(s, account_id=acct, state="pending", assigned_to=uid)
            assert any(i["id"] == rid for i in mine)

    def test_feedback_reads_verdict_signals(self):
        # link a real verdict so the _feed_active_learning branch reads signals
        uid, acct = _user_account("rb3@x.example")
        with session_scope() as s:
            s.add(orm.VerdictRow(
                id="verd_real", inspection_id="insp_x", verdict="phish", confidence=0.9,
                severity="critical", evidence_summary=["clone"], suggested_action="takedown",
                takedown_draft="...", model_used="claude", attack_family="banking",
                kit_match="16Shop", cloaking_detected=True))
            s.flush()
            item = review.enqueue_for_review(
                s, account_id=acct, alert_id="a2", suspect_url="https://e2.example",
                ai_verdict="phish", ai_confidence=0.9, severity="critical",
                verdict_id="verd_real", brand_id="brand_y")
            rid = item.id
        with session_scope() as s:
            review.decide(s, review_id=rid, decision="approve",
                          decided_by=uid, actor_email="rb3@x.example")
        with session_scope() as s:
            fb = s.scalars(
                __import__("sqlalchemy").select(orm.FeedbackEventRow)
                .where(orm.FeedbackEventRow.tenant_id == acct)).all()
            assert any(f.attack_family == "banking" and f.kit_match == "16Shop" for f in fb)

    def test_queue_stats(self):
        uid, acct = _user_account("rb4@x.example")
        self._enqueue(acct)
        with session_scope() as s:
            stats = review.queue_stats(s, account_id=acct)
            assert stats.get("pending", 0) >= 1


# ──────────────────────────── deps cookie auth ──────────────────────────

class TestDepsCookieAuth:
    def test_cookie_session_authenticates(self):
        from fastapi.testclient import TestClient
        from src.api.app import app
        c = TestClient(app)
        # signup sets a session cookie; /auth/me via cookie exercises _from_cookie
        c.post("/auth/signup", json={"email": "cookie@x.example", "password": "password123"})
        r = c.get("/auth/me")  # no bearer -> falls through to cookie path
        assert r.status_code == 200
        assert r.json()["email"] == "cookie@x.example"

    def test_invalid_cookie_returns_none(self):
        from fastapi.testclient import TestClient
        from src.api.app import app
        c = TestClient(app)
        c.cookies.set("dd_session", "not-a-valid-signed-value")
        assert c.get("/auth/me").status_code == 401
