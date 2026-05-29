"""
Logo similarity via embeddings.

The histogram-based ``logo.py`` scorer compares colour distributions of the
canonical logo and the top-left region of the suspect screenshot. This works
when the phishing kit copies the logo verbatim, but it breaks the moment a
kit:

* Recolours the logo (a darker bank navy → lighter blue)
* Scales it up/down
* Adds slight padding or background
* Re-renders the logo as a font glyph rather than a raster

The real-world fix is image embeddings — CLIP-style models produce vectors
where visually similar images have high cosine similarity even under these
transformations. This module wraps that, with a graceful fallback.

Tiered fallback:

1. **CLIP** (best). Loads ``openai/clip-vit-base-patch32`` if ``transformers``
   and ``torch`` are installed. Real production deployments use this.
2. **Histogram with spatial regions** (default fallback). Computes 6 sub-region
   histograms (top-left, top-centre, etc) and compares region-by-region. More
   robust to small layout shifts than a single global histogram.
3. **Plain histogram** (already in ``logo.py``). Used by the existing scorer.

In MOCK_MODE the CLIP path is skipped, but the spatial-histogram fallback is
itself a meaningful step up from the plain version. The interface is the same
``logo_embedding_score(canonical_logo: bytes, suspect_screenshot: bytes)``.
"""

from __future__ import annotations

import io
from functools import lru_cache
from typing import Callable

from PIL import Image

from ..common.logging import get_logger

logger = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def logo_embedding_score(canonical_logo: bytes, suspect_screenshot: bytes) -> float:
    """Return a 0..1 similarity score between the canonical logo and the
    region of the suspect screenshot where a logo is most likely to be.

    Tries CLIP first; falls back to spatial-histogram if CLIP unavailable.
    Returns 0.0 if either input is empty.
    """
    if not canonical_logo or not suspect_screenshot:
        return 0.0

    scorer = _get_scorer()
    try:
        return scorer(canonical_logo, suspect_screenshot)
    except Exception as exc:  # noqa: BLE001
        logger.warning("logo_embedding.scorer_failed", error=str(exc))
        return 0.0


# --------------------------------------------------------------------------- #
# Scorer selection
# --------------------------------------------------------------------------- #


@lru_cache(maxsize=1)
def _get_scorer() -> Callable[[bytes, bytes], float]:
    """Pick the best available scorer at first call; cache it."""
    try:
        return _build_clip_scorer()
    except ImportError:
        logger.info("logo_embedding.using_fallback", reason="clip_unavailable")
        return _spatial_histogram_scorer


def _build_clip_scorer() -> Callable[[bytes, bytes], float]:
    """Try to construct a CLIP-based scorer. Raises ImportError if unavailable.

    We deliberately do NOT install transformers/torch in requirements.txt — the
    download is ~1GB. Production deployments add it explicitly.
    """
    from transformers import CLIPModel, CLIPProcessor  # type: ignore[import-not-found]
    import torch  # type: ignore[import-not-found]

    model_name = "openai/clip-vit-base-patch32"
    model = CLIPModel.from_pretrained(model_name)
    processor = CLIPProcessor.from_pretrained(model_name)
    model.eval()

    def _score(canonical_logo: bytes, suspect_screenshot: bytes) -> float:
        with torch.no_grad():
            # Crop top-left region of suspect screenshot where logo lives
            suspect_img = Image.open(io.BytesIO(suspect_screenshot)).convert("RGB")
            w, h = suspect_img.size
            crop = suspect_img.crop((0, 0, min(w, w // 3), min(h, h // 6)))

            canonical_img = Image.open(io.BytesIO(canonical_logo)).convert("RGB")

            inputs = processor(images=[canonical_img, crop], return_tensors="pt")
            features = model.get_image_features(**inputs)
            features = features / features.norm(dim=-1, keepdim=True)
            cos = float((features[0] * features[1]).sum().item())
            # CLIP cosine ranges roughly -1..1; map to 0..1
            return max(0.0, min(1.0, (cos + 1.0) / 2.0))

    logger.info("logo_embedding.using_clip", model=model_name)
    return _score


# --------------------------------------------------------------------------- #
# Spatial histogram fallback
# --------------------------------------------------------------------------- #


def _spatial_histogram_scorer(canonical_logo: bytes, suspect_screenshot: bytes) -> float:
    """Compare canonical logo against suspect's top-left region using a
    grid of regional colour histograms.

    More robust than a single global histogram because it preserves spatial
    layout: a logo with red on the left and blue on the right won't match a
    logo with blue on the left and red on the right.
    """
    canonical = Image.open(io.BytesIO(canonical_logo)).convert("RGB")
    suspect_full = Image.open(io.BytesIO(suspect_screenshot)).convert("RGB")

    # Crop the top-left logo region of the suspect — same proportions as
    # canonical so the spatial comparison is fair.
    cw, ch = canonical.size
    sw, sh = suspect_full.size
    # Logos typically sit in the top-left 30% × 15% of the page
    region = suspect_full.crop((0, 0, min(sw, sw // 3), min(sh, sh // 6)))

    # Resize both to a common grid size for spatial comparison
    grid_w, grid_h = 4, 2  # 4 columns × 2 rows of sub-regions
    target_w, target_h = 160, 80  # small enough to be fast
    canonical_norm = canonical.resize((target_w, target_h))
    region_norm = region.resize((target_w, target_h))

    cell_w = target_w // grid_w
    cell_h = target_h // grid_h

    total_score = 0.0
    cells = 0
    for r in range(grid_h):
        for c in range(grid_w):
            box = (c * cell_w, r * cell_h, (c + 1) * cell_w, (r + 1) * cell_h)
            c_cell = canonical_norm.crop(box)
            s_cell = region_norm.crop(box)
            score = _hist_similarity(c_cell, s_cell)
            total_score += score
            cells += 1
    return round(total_score / cells, 4) if cells else 0.0


def _hist_similarity(a: Image.Image, b: Image.Image) -> float:
    """Bhattacharyya coefficient on 8-bin per-channel histograms."""
    hist_a = _eight_bin_histogram(a)
    hist_b = _eight_bin_histogram(b)
    total = 0.0
    for ha, hb in zip(hist_a, hist_b):
        total += (ha * hb) ** 0.5
    return total


def _eight_bin_histogram(img: Image.Image) -> list[float]:
    """Per-channel 8-bin histogram, normalised to sum to 1 per channel.

    Returns a flat list of 24 floats (8 bins × 3 channels).
    """
    counts: list[list[int]] = [[0] * 8 for _ in range(3)]
    pixels = img.load()
    w, h = img.size
    total = max(1, w * h)
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[x, y][:3]
            counts[0][r // 32] += 1
            counts[1][g // 32] += 1
            counts[2][b // 32] += 1
    flat: list[float] = []
    for channel in counts:
        flat.extend(c / total for c in channel)
    return flat
