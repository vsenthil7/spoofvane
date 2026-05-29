"""Tests for the v0.4 social-media impersonation discovery source."""

from src.common.models import Brand, Source
from src.discovery import SocialMediaSource
from src.discovery.run_once import DEFAULT_SOURCES
from src.discovery.social_media import (
    SURFACE_FAKE_SUPPORT,
    SURFACE_HANDLE_SQUAT,
    SURFACE_IMPERSONATION_PAGE,
)


def _brand() -> Brand:
    return Brand(
        id="brand_social",
        name="Acme Bank",
        login_url="https://www.acmebank.example/login",
        target_country="US",
        brand_keywords=["Acme Bank"],
    )


def test_social_source_registered_in_default_sweep() -> None:
    assert "social_media" in DEFAULT_SOURCES
    assert DEFAULT_SOURCES["social_media"] is SocialMediaSource


def test_social_source_yields_suspects_in_mock_mode() -> None:
    suspects = list(SocialMediaSource().discover(_brand()))
    assert suspects, "expected mock social fixtures"
    assert all(s.source is Source.SOCIAL_MEDIA for s in suspects)
    assert all(s.brand_id == "brand_social" for s in suspects)


def test_social_metadata_has_platform_and_surface() -> None:
    suspects = list(SocialMediaSource().discover(_brand()))
    platforms = {s.discovery_metadata.get("platform") for s in suspects}
    surfaces = {s.discovery_metadata.get("surface") for s in suspects}
    # Multiple platforms covered
    assert {"X", "Instagram", "Facebook", "Telegram"} <= platforms
    # All three impersonation surface kinds represented
    assert surfaces == {
        SURFACE_FAKE_SUPPORT,
        SURFACE_HANDLE_SQUAT,
        SURFACE_IMPERSONATION_PAGE,
    } or surfaces <= {
        SURFACE_FAKE_SUPPORT,
        SURFACE_HANDLE_SQUAT,
        SURFACE_IMPERSONATION_PAGE,
    }
    # At least one of each that we seeded
    assert SURFACE_FAKE_SUPPORT in surfaces
    assert SURFACE_IMPERSONATION_PAGE in surfaces


def test_funnel_target_is_external_page_when_present() -> None:
    """Profiles that funnel to an external page should inspect that page,
    while the original profile URL is preserved in metadata."""
    suspects = list(SocialMediaSource().discover(_brand()))
    funnels = [
        s for s in suspects
        if s.discovery_metadata.get("funnels_to_external_page")
    ]
    assert funnels, "expected at least one funnel-to-external-page fixture"
    for s in funnels:
        # The inspect URL is the external page, not the social profile.
        assert "profile_url" in s.discovery_metadata
        assert s.url != s.discovery_metadata["profile_url"]


def test_surface_classifier() -> None:
    src = SocialMediaSource()
    assert src._classify_surface("https://x.com/acme_support") == SURFACE_FAKE_SUPPORT
    assert (
        src._classify_surface("https://facebook.com/pages/acme-care")
        == SURFACE_IMPERSONATION_PAGE
    )
    assert src._classify_surface("https://tiktok.com/@acmegiveaway") == SURFACE_HANDLE_SQUAT


def test_handle_extraction() -> None:
    src = SocialMediaSource()
    assert src._extract_handle("https://x.com/acme_support") == "@acme_support"
    assert src._extract_handle("https://x.com/") is None
