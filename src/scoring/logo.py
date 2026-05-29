"""Logo-presence score on a non-brand domain.

The production layer uses CLIP (ViT-B/32, open weights) to embed both the
canonical logo and every distinct image on the suspect page, then takes
the max cosine similarity. The CLIP dependency is heavy and is omitted
from this prototype's default install — instead we use a fast colour-
histogram proxy that performs well on the synthetic demo pages.

A real deployment swaps :func:`_compare` for a CLIP-based comparison; the
public API stays the same.
"""
from __future__ import annotations

from io import BytesIO

from PIL import Image


def _histogram(img: Image.Image, bins: int = 8) -> list[float]:
    """Return a normalised RGB histogram (3*bins floats summing to 1)."""
    img = img.convert("RGB").resize((64, 64))
    hist = img.histogram()  # 256 R + 256 G + 256 B
    bucket = 256 // bins
    out: list[float] = []
    for channel in range(3):
        offset = channel * 256
        for b in range(bins):
            out.append(sum(hist[offset + b * bucket : offset + (b + 1) * bucket]))
    total = sum(out) or 1
    return [v / total for v in out]


def _compare(canonical: Image.Image, suspect: Image.Image) -> float:
    a = _histogram(canonical)
    b = _histogram(suspect)
    # Bhattacharyya-coefficient-style score, bounded in [0, 1].
    import math

    return round(sum(math.sqrt(x * y) for x, y in zip(a, b)), 4)


def logo_score(canonical_logo_png: bytes, suspect_screenshot_png: bytes) -> float:
    """Return a 0..1 score for "the canonical logo appears on the suspect page".

    Heuristic: compare the canonical logo to the top-left 200×100 region of the
    suspect screenshot (where login pages typically place the brand logo).
    """
    if not canonical_logo_png or not suspect_screenshot_png:
        return 0.0
    canonical = Image.open(BytesIO(canonical_logo_png))
    suspect_full = Image.open(BytesIO(suspect_screenshot_png))
    suspect_header = suspect_full.crop(
        (0, 0, min(200, suspect_full.width), min(100, suspect_full.height))
    )
    return _compare(canonical, suspect_header)
