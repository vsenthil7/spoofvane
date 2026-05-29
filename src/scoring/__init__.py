"""Similarity scoring — pHash, DOM, logo, favicon."""

from .composite import score
from .phash import phash_score
from .dom_similarity import dom_score
from .logo import logo_score
from .favicon import favicon_match

__all__ = ["score", "phash_score", "dom_score", "logo_score", "favicon_match"]
