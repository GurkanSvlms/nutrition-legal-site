#!/usr/bin/env python3
"""Add (or update/remove) the Cloudflare Web Analytics beacon on every HTML page.

    python3 scripts/apply_analytics.py          # uses data/analytics.json {"cloudflare_token": "..."}
    python3 scripts/apply_analytics.py --check  # count pages with / without the beacon

Cookieless, no personal data, so no consent banner is needed (see privacy.html).
Idempotent: the snippet lives between <!-- cfa:start --> and <!-- cfa:end --> before </body>.
An empty token removes the snippet everywhere. Run after the page generators and apply_nav.py.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOCK = re.compile(r"\n?<!-- cfa:start -->.*?<!-- cfa:end -->", re.S)


def pages():
    for p in ROOT.rglob("*.html"):
        if any(part.startswith(".") for part in p.relative_to(ROOT).parts) or p.name.startswith("google"):
            continue
        yield p


def main():
    cfg = json.loads((ROOT / "data" / "analytics.json").read_text(encoding="utf-8"))
    token = cfg.get("cloudflare_token", "").strip()
    if token and not re.fullmatch(r"[0-9a-f]{32}", token):
        sys.exit("cloudflare_token must be the 32-character hex token from the Cloudflare snippet")
    snippet = ("<!-- cfa:start -->\n<script type=\"module\" src=\"https://static.cloudflareinsights.com/beacon.min.js\" "
               f"data-cf-beacon='{{\"token\": \"{token}\"}}'></script>\n<!-- cfa:end -->")
    with_b = without = changed = 0
    for p in pages():
        t = p.read_text(encoding="utf-8")
        if "</body>" not in t:
            continue
        if "--check" in sys.argv:
            with_b += "<!-- cfa:start -->" in t
            without += "<!-- cfa:start -->" not in t
            continue
        new = BLOCK.sub("", t)
        if token:
            i = new.rindex("</body>")
            new = new[:i] + snippet + "\n" + new[i:]
        if new != t:
            p.write_text(new, encoding="utf-8")
            changed += 1
    print(f"with beacon={with_b} without={without}" if "--check" in sys.argv else f"pages changed={changed}")


if __name__ == "__main__":
    main()
