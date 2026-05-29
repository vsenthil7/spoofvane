"""
Onboard a brand into DoppelDomain.

Usage::

    python -m scripts.onboard_brand \\
        --name "Acme Bank" \\
        --login-url https://login.acme.example/signin \\
        --target-country US \\
        --keyword acme --keyword acmebank \\
        --threshold 0.65 \\
        --logo /path/to/logo.png

The script:

1. Creates the :class:`Brand` row.
2. Inspects the canonical login URL through the configured Inspector
   (Bright Data in live mode, the synthetic ``MockInspector`` in mock mode).
3. Re-stores the resulting screenshot + DOM as the canonical artefacts on the
   brand row, so the scorer has something to compare suspect captures against.
4. Optionally registers a logo image, which the logo-region scorer compares
   against the top-left of each suspect screenshot.

In live mode (``MOCK_MODE=false``) step 2 requires Bright Data credentials.
In mock mode the canonical capture is the synthetic render the MockInspector
produces — this is enough to demonstrate the scoring pipeline end-to-end
without any network access.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.common.ids import brand_id as gen_brand_id, suspect_id
from src.common.logging import get_logger
from src.common.models import Brand, Source, SuspectURL
from src.common.settings import get_settings
from src.inspection.browser import get_inspector
from src.storage.blob_store import write_blob
from src.storage.db import session_scope
from src.storage.repositories import BrandRepo

logger = get_logger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Onboard a brand into DoppelDomain")
    parser.add_argument("--name", required=True, help="Brand display name")
    parser.add_argument(
        "--login-url", required=True, help="Canonical login URL — will be inspected"
    )
    parser.add_argument(
        "--payment-url", default=None, help="Optional canonical payment URL"
    )
    parser.add_argument(
        "--target-country",
        default="US",
        help="ISO 3166-1 alpha-2 country to render suspect URLs from",
    )
    parser.add_argument(
        "--keyword",
        action="append",
        default=[],
        help="Brand-adjacent keyword (may repeat). Used by SERP/cert-stream discovery.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.65,
        help="Composite-score threshold above which a suspect is flagged",
    )
    parser.add_argument("--logo", type=Path, default=None, help="Path to canonical logo PNG/JPG")
    args = parser.parse_args()

    settings = get_settings()
    settings.ensure_dirs()

    logger.info(
        "onboard.start",
        name=args.name,
        login_url=args.login_url,
        country=args.target_country,
        mock_mode=settings.mock_mode,
    )

    # Logo file → settled at canonical/<brand>.png
    logo_path: Path | None = None
    if args.logo:
        if not args.logo.exists():
            print(f"error: logo file not found: {args.logo}", file=sys.stderr)
            return 2
        target = settings.canonical_dir / f"{args.name.replace(' ', '_').lower()}_logo{args.logo.suffix}"
        target.write_bytes(args.logo.read_bytes())
        logo_path = target

    # Build a partial brand row first (need an id to inspect against)
    brand = Brand(
        id=gen_brand_id(),
        name=args.name,
        login_url=args.login_url,
        payment_url=args.payment_url,
        logo_path=logo_path,
        target_country=args.target_country.upper(),
        brand_keywords=args.keyword,
        score_threshold=args.threshold,
    )

    # Synthesize a SuspectURL pointing at the brand's own login URL so the
    # inspector can render it; this gives us canonical screenshot + DOM.
    canonical_suspect = SuspectURL(
        id=suspect_id(),
        brand_id=brand.id,
        url=args.login_url,
        source=Source.MANUAL,
        discovery_metadata={"role": "canonical_baseline"},
    )

    inspector = get_inspector()
    canonical = inspector.inspect(brand, canonical_suspect)
    if not canonical.success:
        print(
            f"error: canonical inspection failed: {canonical.error}", file=sys.stderr
        )
        return 3

    # Promote the inspection's screenshot/DOM hashes to brand-level canonical
    # references. The bytes are already on disk via the blob store.
    brand.canonical_screenshot_hash = canonical.screenshot_hash
    brand.canonical_dom_hash = canonical.dom_hash

    with session_scope() as s:
        repo = BrandRepo(s)
        if repo.get_by_name(brand.name) is not None:
            print(f"error: brand already exists: {brand.name}", file=sys.stderr)
            return 4
        saved = repo.create(brand)

    print(f"✓ Onboarded brand")
    print(f"  id:                  {saved.id}")
    print(f"  name:                {saved.name}")
    print(f"  login_url:           {saved.login_url}")
    print(f"  target_country:      {saved.target_country}")
    print(f"  threshold:           {saved.score_threshold}")
    print(f"  canonical screenshot: {saved.canonical_screenshot_hash}")
    print(f"  canonical dom:       {saved.canonical_dom_hash}")
    if saved.logo_path:
        print(f"  logo:                {saved.logo_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
