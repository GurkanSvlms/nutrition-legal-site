"""One-off (Nov 13 2026): fold pofu.html into index.html (and tr/pofu.html into tr/index.html).

Copies the factual parts AI assistants and search cite (what is Pofu, at a glance, what Pofu is not,
the extra FAQ questions, Organization/WebSite/WebPage schema) into the landing page, then turns the
old page into a redirect stub. Links to the old URLs are rewritten by apply_nav.py (home_url()).
Run once: python3 scripts/merge_home.py
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_FAQ = {0, 5, 10}  # already on the landing FAQ: tracker?, free?, Android?
CSS = (".about{padding:64px 0}.about__lede{max-width:68ch;font-size:1.1rem;line-height:1.6;color:var(--ink2);margin:0 0 24px}"
       ".facts{display:grid;grid-template-columns:minmax(110px,max-content) 1fr;gap:10px 20px;margin:0 0 24px;max-width:68ch}"
       ".facts dt{font-weight:700}.facts dd{margin:0;color:var(--ink2)}.about__note{max-width:68ch;font-size:.95rem;color:var(--ink2);margin:0}")


def sec(s, sid):
    return re.search(r'<section id="%s"[^>]*>(.*?)</section>' % sid, s, re.S).group(1)


def inner(tag, s):
    return re.search(r"<%s[^>]*>(.*?)</%s>" % (tag, tag), s, re.S).group(1).strip()


def text(s):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s))).strip()


def merge(home, old, url):
    h, o = (ROOT / home).read_text(), (ROOT / old).read_text()
    assert 'id="about"' not in h, f"{home} already merged"
    what, glance, nope = sec(o, "what-is-pofu"), sec(o, "at-a-glance"), sec(o, "not-medical")
    about = (f'<section id="about" class="about" aria-labelledby="about-title">\n<style>{CSS}</style>\n      <div class="wrap">\n'
             f'        <header class="section-head">\n          <p class="kicker">{inner("h2", glance)}</p>\n'
             f'          <h2 id="about-title">{inner("h2", what)}</h2>\n        </header>\n'
             f'        <p class="about__lede">{inner("p", what)}</p>\n'
             f'        <dl class="facts">\n{inner("dl", glance)}\n        </dl>\n'
             f'        <p class="about__note"><strong>{inner("h2", nope).rstrip("?") + "?" if inner("h2", nope).endswith("?") else inner("h2", nope) + "."}</strong> {inner("p", nope)}</p>\n'
             f'      </div>\n    </section>\n\n    ')
    h = h.replace('<section id="faq"', about + '<section id="faq"', 1)

    qa = re.findall(r'<div class="qa">\s*<h3>(.*?)</h3>\s*<p>(.*?)</p>\s*</div>', sec(o, "faq"), re.S)
    assert len(qa) == 11, (old, len(qa))
    extra = "".join(f"\n          <details>\n            <summary>{q}</summary>\n            <p>{a}</p>\n          </details>"
                    for i, (q, a) in enumerate(qa) if i not in SKIP_FAQ)
    i = h.index('<div class="faq__list">')
    j = h.index("\n        </div>", i)
    h = h[:j] + extra + h[j:]

    lst = h[i:h.index("\n        </div>", i) + 1]
    faq = [{"@type": "Question", "name": text(q), "acceptedAnswer": {"@type": "Answer", "text": text(a)}}
           for q, a in re.findall(r"<summary>(.*?)</summary>\s*<p>(.*?)</p>", lst, re.S)]
    blocks = [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', o, re.S)]
    graph = [g for b in blocks for g in b.get("@graph", [])]  # tr/pofu.html has no Organization graph
    graph = [g for g in graph if g["@type"] in ("Organization", "WebSite", "WebPage")]
    for g in graph:
        if g["@type"] == "Organization":
            g["url"] = "https://getpofu.com/"
        if g["@type"] == "WebPage":
            g["@id"], g["url"] = url + "#webpage", url
            g.pop("breadcrumb", None)
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph + [{"@type": "FAQPage", "mainEntity": faq}]},
                    ensure_ascii=False, indent=2)
    h = h.replace("</head>", f'<script type="application/ld+json">\n{ld}\n</script>\n</head>', 1)
    h = re.sub(r"<title>.*?</title>", lambda m: re.search(r"<title>.*?</title>", o).group(0), h, count=1)
    (ROOT / home).write_text(h)

    stub = (f'<!doctype html>\n<html lang="{"tr" if home.startswith("tr/") else "en"}">\n<head>\n<meta charset="utf-8">\n'
            f'<title>Pofu</title>\n<link rel="canonical" href="{url}">\n<meta name="robots" content="noindex, follow">\n'
            f'<meta http-equiv="refresh" content="0; url={url}">\n<script>location.replace("{url}"+location.hash)</script>\n'
            f'</head>\n<body><p><a href="{url}">Pofu</a></p></body>\n</html>\n')
    (ROOT / old).write_text(stub)
    print(home, "faq", len(faq))


def hreflang():
    """Give / and /tr/ the 22-language hreflang set the pofu.html pages had; drop the old URLs from the sitemap."""
    alts = re.findall(r'<link rel="alternate" hreflang="[^"]+" href="[^"]+">', (ROOT / "pofu.html").read_text())
    assert len(alts) >= 22, len(alts)
    block = "\n".join(alts)
    for home in ("index.html", "tr/index.html"):
        h = (ROOT / home).read_text()
        h = re.sub(r'(?:<link rel="alternate" hreflang="[^"]+" href="[^"]+">\s*)+', block + "\n", h, count=1)
        (ROOT / home).write_text(h)
    sm = (ROOT / "sitemap.xml").read_text()
    urls = {re.search(r"<loc>(.*?)</loc>", u).group(1): u for u in re.findall(r"<url>.*?</url>", sm, re.S)}
    xalts = re.findall(r"<xhtml:link [^>]*/>", urls["https://getpofu.com/pofu.html"])
    for old, new in (("https://getpofu.com/pofu.html", "https://getpofu.com/"),
                     ("https://getpofu.com/tr/pofu.html", "https://getpofu.com/tr/")):
        sm = re.sub(r"\s*" + re.escape(urls[old]), "", sm, count=1)
        u = urls[new]
        u2 = re.sub(r"(?:\s*<xhtml:link [^>]*/>)+", lambda m: "\n    " + "\n    ".join(xalts), u, count=1)
        sm = sm.replace(u, u2, 1)
    (ROOT / "sitemap.xml").write_text(sm)


if __name__ == "__main__":
    import sys
    if "--tr-only" not in sys.argv:  # first run stopped after the English merge
        hreflang()
        merge("index.html", "pofu.html", "https://getpofu.com/")
    merge("tr/index.html", "tr/pofu.html", "https://getpofu.com/tr/")
