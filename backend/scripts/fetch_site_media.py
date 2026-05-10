"""
Download bundled catalog images into backend/site_media/.

Usage (from backend directory):
  python scripts/fetch_site_media.py

Requires network. Safe to re-run (skips files that already exist and are non-empty).
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.site_media import SITE_MEDIA_DOWNLOADS, ensure_placeholder_asset  # noqa: E402


def main() -> None:
    out = BACKEND_ROOT / "site_media"
    out.mkdir(parents=True, exist_ok=True)
    ensure_placeholder_asset(out)

    ua = "Mozilla/5.0 (compatible; GlamrSiteMediaFetcher/1.0)"
    for name, url in SITE_MEDIA_DOWNLOADS:
        dest = out / name
        if dest.exists() and dest.stat().st_size > 0:
            print("skip", name)
            continue
        print("fetch", name, "…")
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        if not data:
            print("  empty response, skipped")
            continue
        dest.write_bytes(data)
        print("  wrote", dest.stat().st_size, "bytes")

    print("done ->", out)


if __name__ == "__main__":
    main()
