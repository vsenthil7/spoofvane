"""Scoring sub-components on synthetic inputs."""

import io

from PIL import Image

from src.scoring.dom_similarity import dom_score
from src.scoring.favicon import favicon_match
from src.scoring.logo import logo_score
from src.scoring.phash import phash_score


def _png(color: tuple[int, int, int], size: tuple[int, int] = (800, 600)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_phash_identical_screenshots() -> None:
    img = _png((40, 80, 200))
    assert phash_score(img, img) >= 0.99


def test_phash_radically_different_screenshots() -> None:
    # Two structured images with very different layouts. Solid colour images
    # have identical low-frequency components, so pHash treats them as similar
    # — use actual content variation to exercise the metric.
    a_img = Image.new("RGB", (800, 600), (0, 0, 0))
    for x in range(0, 800, 20):
        for y in range(0, 600, 20):
            a_img.paste((255, 255, 255), (x, y, x + 10, y + 10))
    b_img = Image.new("RGB", (800, 600), (255, 255, 255))
    for x in range(0, 800, 40):
        b_img.paste((0, 0, 0), (x, 0, x + 4, 600))

    a_buf, b_buf = io.BytesIO(), io.BytesIO()
    a_img.save(a_buf, format="PNG")
    b_img.save(b_buf, format="PNG")
    score = phash_score(a_buf.getvalue(), b_buf.getvalue())
    # Different structural content should land below the identical-image score
    assert score < 0.95


def test_dom_score_high_for_identical_dom() -> None:
    html = (
        b"<html><body><form><input type='password' name='pw'>"
        b"<input type='text' name='user'></form></body></html>"
    )
    assert dom_score(html, html) >= 0.99


def test_dom_score_login_bonus() -> None:
    """Two login-form pages with the same tag mix score higher than two
    unrelated pages with similar tag mixes."""
    login_html = (
        b"<html><body><form><input type='password'>"
        b"<input type='text'><button>go</button></form></body></html>"
    )
    other = (
        b"<html><body><form><textarea></textarea>"
        b"<button>go</button></form></body></html>"
    )
    s_login = dom_score(login_html, login_html)
    s_mixed = dom_score(login_html, other)
    assert s_login > s_mixed


def test_favicon_match_truth_table() -> None:
    assert favicon_match("aaa", "aaa") is True
    assert favicon_match("aaa", "bbb") is False
    assert favicon_match(None, "aaa") is False
    assert favicon_match("aaa", None) is False


def test_logo_score_returns_unit_interval() -> None:
    # logo_score takes (canonical_logo_bytes, suspect_screenshot_bytes)
    logo = _png((200, 50, 50), size=(120, 60))
    suspect = _png((200, 50, 50))
    s = logo_score(logo, suspect)
    assert 0.0 <= s <= 1.0
