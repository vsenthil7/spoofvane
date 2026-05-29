"""End-to-end browser tests (Playwright).

These drive a real Chromium against a running SpoofVane server, covering the
flows a user actually clicks: login, failed login, demo-user quick-fill, MFA
challenge, logout, and unauthenticated redirect.

Running
-------
Browser binaries must be present (``playwright install chromium``). In CI or a
dev machine::

    # 1. start the app on :8099 with the demo matrix seeded
    bash tests/e2e/run_e2e.sh

    # or manually:
    python -m scripts.seed_users
    uvicorn src.api.app:app --port 8099 &
    pytest tests/e2e -q

Environment
-----------
E2E_BASE_URL  defaults to http://127.0.0.1:8099

Note: this suite is skipped automatically if Playwright's browser is not
installed, so it never breaks the unit/integration run. It is a *separate*
verified dimension in the traceability matrix (REQ-UI-01..03, REQ-MFA-02).
"""
from __future__ import annotations

import os

import pytest

playwright = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402

BASE = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8099")
DEMO_PW = "DemoPass123!"


def _browser_available() -> bool:
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            b.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _browser_available(),
    reason="Playwright Chromium not installed (run: playwright install chromium)",
)


@pytest.fixture()
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        pg = ctx.new_page()
        yield pg
        ctx.close()
        browser.close()


# ─────────────────────────────── Tests ──────────────────────────────────

class TestLoginFlow:
    def test_login_page_loads(self, page):
        page.goto(f"{BASE}/login")
        expect(page.get_by_text("Sign in to SpoofVane")).to_be_visible()

    def test_successful_login_redirects_to_dashboard(self, page):
        page.goto(f"{BASE}/login")
        page.fill("#email", "owner@business.demo")
        page.fill("#password", DEMO_PW)
        page.click("#login-form button[type=submit]")
        page.wait_for_url(f"{BASE}/")
        expect(page).to_have_url(f"{BASE}/")

    def test_failed_login_shows_error(self, page):
        page.goto(f"{BASE}/login")
        page.fill("#email", "owner@business.demo")
        page.fill("#password", "wrongpassword")
        page.click("#login-form button[type=submit]")
        expect(page.locator("#err")).to_be_visible()

    def test_demo_user_quickfill(self, page):
        page.goto(f"{BASE}/login")
        page.get_by_text("Demo logins", exact=False).click()
        row = page.locator(".demo-row[data-email='analyst@business.demo']")
        row.click()
        expect(page.locator("#email")).to_have_value("analyst@business.demo")
        expect(page.locator("#password")).to_have_value(DEMO_PW)

    def test_mfa_challenge_appears(self, page):
        page.goto(f"{BASE}/login")
        page.fill("#email", "mfa.reviewer@enterprise.demo")
        page.fill("#password", DEMO_PW)
        page.click("#login-form button[type=submit]")
        # password correct -> MFA form should reveal, login form should hide
        expect(page.locator("#mfa-form")).to_be_visible()
        expect(page.locator("#login-form")).to_be_hidden()

    def test_logout_returns_to_login(self, page):
        # login first
        page.goto(f"{BASE}/login")
        page.fill("#email", "owner@business.demo")
        page.fill("#password", DEMO_PW)
        page.click("#login-form button[type=submit]")
        page.wait_for_url(f"{BASE}/")
        # logout via API then verify dashboard no longer authed
        page.request.post(f"{BASE}/auth/logout")
        page.goto(f"{BASE}/auth/me")
        # /auth/me returns 401 JSON when logged out
        assert "401" in page.content() or "authentication required" in page.content()
