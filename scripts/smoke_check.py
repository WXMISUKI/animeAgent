"""Post-deploy smoke check for Vercel endpoints.

Usage:
  python scripts/smoke_check.py https://your-domain.vercel.app
"""

from __future__ import annotations

import json
import sys
from urllib import request
from urllib.error import URLError, HTTPError


def http_get(url: str) -> tuple[int, str]:
    req = request.Request(url, method="GET")
    with request.urlopen(req, timeout=15) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/smoke_check.py <base_url>")
        return 2

    base = sys.argv[1].rstrip("/")
    targets = [
        f"{base}/",
        f"{base}/health",
        f"{base}/health/detail",
        f"{base}/metrics",
    ]

    failed = False
    for url in targets:
        try:
            status, body = http_get(url)
            print(f"[OK] {url} -> {status}")
            if url.endswith("/health/detail"):
                parsed = json.loads(body)
                print(
                    "     all_required_ready="
                    f"{parsed.get('env', {}).get('all_required_ready')}"
                )
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            failed = True
            print(f"[FAIL] {url} -> {exc}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

