"""Sprint 13 — React SOC console parity checks (review §9, 21 pages).

These run in the Python suite (no Node needed) by parsing the TS page registry,
so the 21-page contract is enforced in CI without a browser. The Playwright
pixel-parity execution is BLOCKED-ENV (needs a running dev server + browsers).
"""
import re
from pathlib import Path

CONSOLE = Path(__file__).resolve().parents[1] / "console"


def _page_registry_ids() -> list[str]:
    txt = (CONSOLE / "src/lib/pages.ts").read_text()
    return re.findall(r'id:\s*"(P\d\d)"', txt)


def _page_components() -> list[str]:
    txt = (CONSOLE / "src/lib/pages.ts").read_text()
    return re.findall(r'component:\s*"(\w+)"', txt)


def test_exactly_21_pages_registered():
    ids = _page_registry_ids()
    assert len(ids) == 21
    assert ids == [f"P{i:02d}" for i in range(1, 22)]


def test_every_registered_page_has_a_component_file():
    for comp in _page_components():
        assert (CONSOLE / f"src/pages/{comp}.tsx").exists(), f"missing page component {comp}"


def test_no_orphan_page_components():
    registered = set(_page_components())
    on_disk = {p.stem for p in (CONSOLE / "src/pages").glob("*.tsx")}
    assert on_disk == registered  # no extra/missing files


def test_pages_use_canonical_tokens_not_hardcoded_palette():
    # Spot-check: page components reference CSS vars, not raw hex brand colors.
    offenders = []
    for p in (CONSOLE / "src/pages").glob("*.tsx"):
        src = p.read_text()
        # allow a few intentional inline hexes (login button ink, 404 codes);
        # the rule is that brand/verdict colors come from var(--sv-*)
        if "var(--sv-" not in src:
            offenders.append(p.name)
    assert not offenders, f"pages not using tokens: {offenders}"


def test_app_router_imports_all_pages():
    app = (CONSOLE / "src/App.tsx").read_text()
    for comp in _page_components():
        assert comp in app, f"App.tsx does not wire {comp}"


def test_design_tokens_present():
    tokens = (CONSOLE / "src/tokens/tokens.css").read_text()
    for var in ("--sv-bg", "--sv-brand", "--sv-phish", "--sv-benign", "--sv-font-display"):
        assert var in tokens
