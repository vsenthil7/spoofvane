"""Tests for v0.3 Phases 2–5: audit, human-in-the-loop, notifications, reports."""
from __future__ import annotations

import pytest

from src.common import audit, notifications, reports, review
from src.common.identity import signup
from src.common.rbac import Tier
from src.storage import models as orm
from src.storage.db import session_scope
from src.storage.identity_models import ReviewItemRow
from src.storage.init_db import init_db


@pytest.fixture(scope="module", autouse=True)
def _schema():
    init_db()


def _account(email: str, tier: Tier = Tier.BUSINESS) -> str:
    with session_scope() as s:
        return signup(s, email=email, password="password123", tier=tier).account_id


# ─────────────────────────────── Audit ──────────────────────────────────

class TestAuditChain:
    def test_records_and_verifies(self):
        acct = _account("aud1@x.com")
        with session_scope() as s:
            for i in range(5):
                audit.record(s, actor="u@x.com", action=f"act{i}", account_id=acct,
                             target_kind="t", target_id=str(i))
        with session_scope() as s:
            res = audit.verify_chain(s, account_id=acct)
            assert res["valid"] is True
            assert res["verified"] == 5

    def test_query_filters(self):
        acct = _account("aud2@x.com")
        with session_scope() as s:
            audit.record(s, actor="alice@x.com", action="login", account_id=acct)
            audit.record(s, actor="bob@x.com", action="brand.create", account_id=acct)
        with session_scope() as s:
            assert len(audit.query(s, account_id=acct, actor="alice@x.com")) == 1
            assert len(audit.query(s, account_id=acct, action="brand.create")) == 1

    def test_tamper_is_detected(self):
        acct = _account("aud3@x.com")
        with session_scope() as s:
            for i in range(4):
                audit.record(s, actor="u@x.com", action=f"act{i}", account_id=acct)
        # Tamper: mutate a historical row's action in place
        with session_scope() as s:
            rows = s.scalars(
                __import__("sqlalchemy").select(orm.AuditLogRow)
                .where(orm.AuditLogRow.tenant_id == acct)
                .order_by(orm.AuditLogRow.created_at)
            ).all()
            rows[1].action = "TAMPERED"
            s.flush()
        with session_scope() as s:
            res = audit.verify_chain(s, account_id=acct)
            assert res["valid"] is False
            assert res["broken_index"] == 1

    def test_csv_export(self):
        acct = _account("aud4@x.com")
        with session_scope() as s:
            audit.record(s, actor="u@x.com", action="x", account_id=acct)
            rows = audit.query(s, account_id=acct)
        csv_text = audit.export_csv(rows)
        assert "actor" in csv_text and "u@x.com" in csv_text


# ───────────────────────── Human-in-the-loop ────────────────────────────

class TestReview:
    def _enqueue(self, acct, verdict="phish", severity="high"):
        with session_scope() as s:
            item = review.enqueue_for_review(
                s, account_id=acct, alert_id="alrt_1", suspect_url="https://evil.example",
                ai_verdict=verdict, ai_confidence=0.92, severity=severity,
            )
            return item.id if item else None

    def test_high_severity_enqueues(self):
        acct = _account("rev1@x.com")
        assert self._enqueue(acct, "phish", "high") is not None

    def test_benign_low_does_not_enqueue(self):
        acct = _account("rev2@x.com")
        assert self._enqueue(acct, "benign", "low") is None

    def test_approve_makes_takedown_eligible(self):
        acct = _account("rev3@x.com")
        rid = self._enqueue(acct)
        with session_scope() as s:
            res = review.decide(s, review_id=rid, decision="approve",
                                decided_by="u1", actor_email="rev@x.com")
            assert res["state"] == "approved"
            assert res["takedown_eligible"] is True

    def test_reject_blocks_takedown(self):
        acct = _account("rev4@x.com")
        rid = self._enqueue(acct)
        with session_scope() as s:
            res = review.decide(s, review_id=rid, decision="reject",
                                decided_by="u1", actor_email="rev@x.com")
            assert res["takedown_eligible"] is False

    def test_cannot_decide_twice(self):
        acct = _account("rev5@x.com")
        rid = self._enqueue(acct)
        with session_scope() as s:
            review.decide(s, review_id=rid, decision="approve",
                          decided_by="u1", actor_email="rev@x.com")
        with session_scope() as s, pytest.raises(ValueError, match="already"):
            review.decide(s, review_id=rid, decision="reject",
                          decided_by="u1", actor_email="rev@x.com")

    def test_invalid_decision_rejected(self):
        acct = _account("rev6@x.com")
        rid = self._enqueue(acct)
        with session_scope() as s, pytest.raises(ValueError):
            review.decide(s, review_id=rid, decision="nuke",
                          decided_by="u1", actor_email="rev@x.com")

    def test_decision_writes_audit_and_feedback(self):
        acct = _account("rev7@x.com")
        rid = self._enqueue(acct)
        with session_scope() as s:
            review.decide(s, review_id=rid, decision="approve",
                          decided_by="u1", actor_email="rev@x.com", reason="confirmed clone")
        with session_scope() as s:
            # audit entry exists
            assert any(e["action"] == "review.approve"
                       for e in audit.query(s, account_id=acct))
            # feedback event exists
            fb = s.scalars(
                __import__("sqlalchemy").select(orm.FeedbackEventRow)
                .where(orm.FeedbackEventRow.tenant_id == acct)
            ).all()
            assert any(f.outcome == "true_positive" for f in fb)

    def test_sla_breach_sweep(self):
        acct = _account("rev8@x.com")
        rid = self._enqueue(acct)
        # force overdue
        with session_scope() as s:
            from datetime import datetime, timedelta, timezone
            it = s.get(ReviewItemRow, rid)
            it.sla_due_at = datetime.now(timezone.utc) - timedelta(hours=1)
            s.flush()
        with session_scope() as s:
            assert review.sweep_sla_breaches(s) >= 1


# ───────────────────────────── Notifications ────────────────────────────

class TestNotifications:
    def test_notify_creates_feed_entry(self):
        acct = _account("ntf1@x.com")
        with session_scope() as s:
            from src.common.identity import authenticate_password
            uid = authenticate_password(s, email="ntf1@x.com", password="password123").user_id
            notifications.notify(s, account_id=acct, kind="detection",
                                 title="Test", body="b", severity="warning", user_id=uid)
            items = notifications.list_for_user(s, user_id=uid, account_id=acct)
            assert len(items) >= 1 and items[0]["title"] == "Test"

    def test_mark_read(self):
        acct = _account("ntf2@x.com")
        with session_scope() as s:
            from src.common.identity import authenticate_password
            uid = authenticate_password(s, email="ntf2@x.com", password="password123").user_id
            nid = notifications.notify(s, account_id=acct, kind="detection",
                                       title="R", user_id=uid, send_email=False)
            notifications.mark_read(s, notification_id=nid)
            unread = notifications.list_for_user(s, user_id=uid, account_id=acct, unread_only=True)
            assert all(i["id"] != nid for i in unread)

    def test_email_skipped_when_not_configured(self):
        # email_enabled defaults False -> notify must not raise, just logs.
        acct = _account("ntf3@x.com")
        with session_scope() as s:
            from src.common.identity import authenticate_password
            uid = authenticate_password(s, email="ntf3@x.com", password="password123").user_id
            # critical -> would email; with no SMTP it should log, not crash
            nid = notifications.notify(s, account_id=acct, kind="sla_breach",
                                       title="Crit", severity="critical", user_id=uid)
            assert nid


# ─────────────────────────────── Reports ────────────────────────────────

class TestReports:
    def test_detection_summary_json(self):
        acct = _account("rpt1@x.com")
        with session_scope() as s:
            path = reports.generate_detection_summary(s, account_id=acct, fmt="json")
        assert path.endswith(".json")
        import json
        from pathlib import Path
        data = json.loads(Path(path).read_text())
        assert data["account_id"] == acct

    def test_detection_summary_csv(self):
        acct = _account("rpt2@x.com")
        with session_scope() as s:
            path = reports.generate_detection_summary(s, account_id=acct, fmt="csv")
        from pathlib import Path
        assert "metric" in Path(path).read_text()

    def test_detection_summary_pdf(self):
        acct = _account("rpt3@x.com")
        with session_scope() as s:
            path = reports.generate_detection_summary(s, account_id=acct, fmt="pdf")
        from pathlib import Path
        assert Path(path).read_bytes()[:4] == b"%PDF"

    def test_board_pack_pdf(self):
        acct = _account("rpt4@x.com")
        with session_scope() as s:
            path = reports.generate_board_pack(s, account_id=acct)
        from pathlib import Path
        assert Path(path).read_bytes()[:4] == b"%PDF"

    def test_audit_export_csv_includes_chain(self):
        acct = _account("rpt5@x.com")
        with session_scope() as s:
            audit.record(s, actor="u@x.com", action="x", account_id=acct)
            path = reports.generate_audit_export(s, account_id=acct, fmt="csv")
        from pathlib import Path
        assert "chain_valid=True" in Path(path).read_text()

    def test_reports_listed(self):
        acct = _account("rpt6@x.com")
        with session_scope() as s:
            reports.generate_detection_summary(s, account_id=acct, fmt="json")
            assert len(reports.list_reports(s, account_id=acct)) >= 1
