"""Perceptual-hash visual similarity score.

We compute the pHash of the suspect screenshot and the canonical
screenshot, then convert Hamming distance into a 0..1 similarity score
where 1.0 == identical visual.
"""
from __future__ import annotations

from io import BytesIO

import imagehash
from PIL import Image

# Maximum Hamming distance for a 64-bit hash. Distances above this
# saturate to similarity = 0.
_MAX_HAMMING = 32


def phash_score(canonical_png: bytes, suspect_png: bytes) -> float:
    """Return a similarity score in [0, 1].

    A score above ~0.85 is a strong visual-clone signal.
    """
    if not canonical_png or not suspect_png:
        return 0.0

    a = imagehash.phash(Image.open(BytesIO(canonical_png)))
    b = imagehash.phash(Image.open(BytesIO(suspect_png)))
    distance = a - b
    if distance >= _MAX_HAMMING:
        return 0.0
    return round(1.0 - (distance / _MAX_HAMMING), 4)
