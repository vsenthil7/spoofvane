"""v07 §V07-GUARD — no-shrink protection.

The protected baseline (v05/BUILD 016 + audit fix) is immutable: later builds
may EXTEND but must never delete, empty, or stub-replace a baseline module.

Asserts: (1) src/ Python LOC stays >= the protected floor; (2) every baseline
package still exists; (3) representative named baseline modules stay substantial
(not emptied to a stub). BLOCKING gate (v07 acceptance gate 1).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

PROTECTED_LOC_FLOOR = 15173  # v07 blueprint §1 figure; measured baseline 15193

REPO = Path(__file__).resolve().parents[2]

BASELINE_PACKAGES = [
    "src/discovery", "src/inspection", "src/scoring", "src/verdict",
    "src/deepfake", "src/delivery", "src/delivery/takedown", "src/agents",
    "src/ai_surfaces", "src/api", "src/common", "src/storage", "src/web",
    "src/integrations/brightdata",
]

BASELINE_MODULES_MIN_LINES = {
    "src/inspection/browser.py": 200,
    "src/scoring/composite.py": 60,
    "src/scoring/family.py": 80,
    "src/verdict/ensemble.py": 40,
    "src/integrations/brightdata/base.py": 40,
    "src/common/audit.py": 60,
    "src/common/pipeline.py": 80,
    "src/delivery/integration_base.py": 30,
}


def _git_tracked_src_py() -> list[Path]:
    out = subprocess.check_output(["git", "ls-files", "src"], cwd=REPO, text=True).split()
    return [REPO / f for f in out if f.endswith(".py")]


def _count_lines(p: Path) -> int:
    with open(p, encoding="utf-8", errors="replace") as fh:
        return sum(1 for _ in fh)


def test_src_python_loc_above_floor():
    total = sum(_count_lines(p) for p in _git_tracked_src_py())
    assert total >= PROTECTED_LOC_FLOOR, (
        f"src/ Python LOC {total} dropped below protected floor "
        f"{PROTECTED_LOC_FLOOR} — a baseline module was deleted or gutted."
    )


@pytest.mark.parametrize("pkg", BASELINE_PACKAGES)
def test_baseline_package_exists(pkg):
    assert (REPO / pkg).is_dir(), f"baseline package {pkg} missing"


@pytest.mark.parametrize("module,min_lines", sorted(BASELINE_MODULES_MIN_LINES.items()))
def test_baseline_module_not_stubbed(module, min_lines):
    p = REPO / module
    assert p.is_file(), f"baseline module {module} missing"
    assert _count_lines(p) >= min_lines, (
        f"{module} shrank below {min_lines} lines — looks stubbed/gutted."
    )
