"""Discovery: same-domain filter must not flag the brand's own URLs."""

from src.common.models import Brand
from src.discovery.base import is_same_brand_domain


def _brand(login_url: str) -> Brand:
    return Brand(
        id="brand_x",
        name="X",
        login_url=login_url,
        target_country="US",
    )


def test_same_apex_domain() -> None:
    brand = _brand("https://www.acme.example/signin")
    assert is_same_brand_domain("https://login.acme.example/x", brand) is True


def test_unrelated_domain() -> None:
    brand = _brand("https://acme.example/signin")
    assert is_same_brand_domain("https://account-update-portal.xyz/login", brand) is False


def test_typosquat_is_not_same() -> None:
    brand = _brand("https://acme.example/signin")
    assert is_same_brand_domain("https://acmme.example/login", brand) is False


def test_malformed_url_safe_default() -> None:
    brand = _brand("https://acme.example/signin")
    # Should not raise; defaults to False so the URL is inspected.
    assert is_same_brand_domain("not a url", brand) is False
