#!/usr/bin/env python3
"""Keep food + Q&A pages of languages the Pofu app does not ship in out of Google's index.

Those ~1,100 pages are templated translations (scaled-content risk) and send readers to an app
they cannot use in their language. They stay online and linked (noindex, follow), but:
  1. their <meta name="robots"> becomes "noindex, follow";
  2. every other page drops its <link rel="alternate" hreflang> pointing at them;
  3. sitemap.xml drops their <url> entries and the <xhtml:link> alternates pointing at them.
Also hides the thin pages from noindex_thin.py. Idempotent. Run after build_food_pages.py / apply_nav.py (apply_nav.py calls it at the end).
"""
import re
from pathlib import Path

import noindex_thin

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://getpofu.com/"
# App languages: en, tr, de, fr, es, pt-BR, ko, ru, vi. Everything else below gets noindex.
FOOD_DIRS = {"ar": "saarat", "cs": "kalorie", "hi": "calories", "id": "kalori", "it": "calorie", "ja": "karori",
             "nl": "calorieen", "pl": "kalorie", "ro": "calorii", "sv": "kalorier", "th": "khalori",
             "uk": "kalorii", "zh-Hans": "kaluli"}
PREFIXES = tuple(f"{L}/{d}/" for L, fd in FOOD_DIRS.items() for d in (fd, "questions"))
THIN = set(noindex_thin.thin_paths())  # thin pages of indexable languages get the same treatment
ROBOTS = '<meta name="robots" content="noindex, follow">'


def hidden(url_path):
    """True for a site-relative path ("ar/saarat/x.html") inside a noindexed folder."""
    return url_path.startswith(PREFIXES) or url_path in THIN


def alt_re(tag):
    # one alternate tag (html <link> or sitemap <xhtml:link>) whose href is a hidden page, with its leading whitespace
    return re.compile(r'\n?[ \t]*<' + tag + r' rel="alternate" hreflang="[^"]+" href="' + re.escape(SITE)
                      + r'(?:(?:' + "|".join(re.escape(p) for p in PREFIXES) + r')[^"]*|'
                      + "|".join(re.escape(p) for p in sorted(THIN)) + r')"\s*/?>')


def main():
    link_re, xlink_re = alt_re("link"), alt_re("xhtml:link")
    robots_re = re.compile(r'<meta name="robots" content="[^"]*">')
    marked = cleaned = 0
    for f in ROOT.rglob("*.html"):
        rel = f.relative_to(ROOT).as_posix()
        t = f.read_text(encoding="utf-8")
        if hidden(rel):
            t2 = robots_re.sub(ROBOTS, t, count=1) if robots_re.search(t) else t.replace("</head>", ROBOTS + "\n</head>", 1)
            marked += t2 != t
        else:
            t2 = link_re.sub("", t)
            cleaned += t2 != t
        if t2 != t:
            f.write_text(t2, encoding="utf-8")

    sm = ROOT / "sitemap.xml"
    s = sm.read_text(encoding="utf-8")
    urls = re.findall(r"[ \t]*<url>.*?</url>\n", s, flags=re.S)
    keep = [u for u in urls if not hidden(re.search(r"<loc>" + re.escape(SITE) + r"([^<]*)</loc>", u).group(1))]
    s2 = s.replace("".join(urls), "".join(xlink_re.sub("", u) for u in keep)) if "".join(urls) in s else None
    assert s2 is not None, "sitemap <url> blocks are not contiguous; refusing to rewrite"
    if s2 != s:
        sm.write_text(s2, encoding="utf-8")
    print(f"noindex: pages marked={marked}, pages with hreflang cleaned={cleaned}, "
          f"sitemap urls {len(urls)} -> {len(keep)}")


if __name__ == "__main__":
    assert hidden("ar/saarat/x.html") and hidden("zh-Hans/questions/") and not hidden("ko/kallori/x.html")
    assert not hidden("questions/x.html") and not hidden("ar/best-calorie-counter-for-women.html")
    main()
