#!/usr/bin/env python3
"""Find thin food / Q&A pages in the languages that stay indexable (noindex_unsupported.py handles the rest).

Words are counted in the visible <main> text only: promo/aside, tables, figures, the related-foods
section and food lists are left out. A page is thin when its count is below THIN_RATIO x the median of
its own folder (so each language is judged against its own script/length). Measured Nov 18 2026:
counts are tightly clustered (p5 ~ 0.93 x median) except zero-calorie drinks (black coffee, tea,
Turkish coffee), which sit ~0.75-0.8 x median, so 0.85 separates exactly that group.
noindex_unsupported.py reads thin_paths() and applies the same noindex + sitemap + hreflang treatment.
"""
import html
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THIN_RATIO = 0.85
# folders of the 9 app languages; index.html (hub) is never counted
DIRS = ["calories", "questions", "kalori", "sorular", "de/kalorien", "de/questions", "fr/calories", "fr/questions",
        "es/calorias", "es/questions", "pt-BR/calorias", "pt-BR/questions", "ko/kallori", "ko/questions",
        "ru/kalorii", "ru/questions", "vi/calo", "vi/questions"]


def words(t):
    t = re.sub(r"(?is)<(script|style|aside|nav|header|footer|svg|video|table|figure)\b.*?</\1>", "", t)
    m = re.search(r"(?is)<main\b[^>]*>(.*)</main>", t)
    if not m:
        return None
    t = re.sub(r'(?is)<section id="related".*?</section>|<ul class="foodlist">.*?</ul>|<!--.*?-->', "", m.group(1))
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    cjk = len(re.findall(r"[぀-ヿ一-鿿]", t))
    t = re.sub(r"[぀-ヿ一-鿿]", " ", t)
    return len(re.findall(r"[^\W_]+", t)) + cjk / 2


def thin_paths():
    """{site-relative path: (words, median)} of the thin pages."""
    out = {}
    for d in DIRS:
        counts = {}
        for f in (ROOT / d).glob("*.html"):
            if f.name != "index.html":
                w = words(f.read_text(encoding="utf-8"))
                if w is not None:
                    counts[f"{d}/{f.name}"] = w
        if counts:
            med = statistics.median(counts.values())
            out.update({p: (w, med) for p, w in counts.items() if w < THIN_RATIO * med})
    return out


if __name__ == "__main__":
    for p, (w, med) in sorted(thin_paths().items()):
        print(f"{p}\t{w:.0f}\tmedian {med:.0f}")
