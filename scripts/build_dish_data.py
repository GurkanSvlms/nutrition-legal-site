#!/usr/bin/env python3
"""'Calories in national dishes: 22 cuisines compared' page in every site language + CSV.

    python3 scripts/build_dish_data.py           # write pages + assets/data/national-dishes-calories.csv
    python3 scripts/build_dish_data.py --stats   # print the numbers only

Dishes = the "local" foods of each food-page language (scripts/build_food_pages.py data), without
drinks, condiments and small sides (under 60 g or 80 kcal a serving).
Text: data/dishes/<lang>.json (+ shared labels from data/tools/<lang>.json "common").
Run scripts/apply_nav.py afterwards.
"""
import csv
import html
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_food_pages as fp  # noqa: E402

SITE = "https://getpofu.com/"
TODAY = "2026-11-06"
LANGS = ["en", "tr", "de", "fr", "es", "it", "pt-BR", "nl", "pl", "ru", "uk", "cs", "ro", "sv", "ja", "ko",
         "zh-Hans", "id", "vi", "th", "hi", "ar"]
CUISINE = {"en": "us", "tr": "tr", "de": "de", "fr": "fr", "es": "mx", "pt-BR": "br", "ar": "arab", "cs": "cz",
           "hi": "in", "id": "id", "it": "it", "ja": "jp", "ko": "kr", "nl": "nl", "pl": "pl", "ro": "ro",
           "ru": "ru", "sv": "se", "th": "th", "uk": "ua", "vi": "vn", "zh-Hans": "cn"}
SMALL = 8
DRINKS = {"Kefir"}  # drinks listed in grams
CSV_PATH = "assets/data/national-dishes-calories.csv"


def path_of(L):
    if L == "en":
        return "national-dishes-calories.html"
    if L == "tr":
        return "ulusal-yemekler-kalori-karsilastirmasi.html"
    return f"{L}/national-dishes-calories.html"


def esc(s):
    return html.escape(str(s), quote=True)


def fill(t, **kw):
    return re.sub(r"\{(\w+)\}", lambda m: str(kw.get(m.group(1), m.group(0))), t)


def collect():
    """{food-page language: [dish dicts]} for local dishes, with per-100 g kcal and page path."""
    out, skipped = {}, []
    for code, lc in fp.LANGS.items():
        items = [i for i in fp.load_items(code, lc, skipped) if i["group"] == "local" and i["grams"]]
        seen, dishes = set(), []
        for i in items:
            slug = i.get("slug") or fp.slugify(i["name"])
            if slug in seen:
                continue
            seen.add(slug)
            unit = "ml" if "ml" in i["label"] else "g"
            # dishes only: skip drinks (ml), condiments and small sides (under 60 g or 80 kcal a serving)
            if unit == "ml" or i["grams"] < 60 or i["kcal"] < 80 or i["base"] in DRINKS:
                continue
            dishes.append(dict(name=i["name"], slug=slug, kcal=round(i["kcal"]), grams=i["grams"], unit=unit,
                               label=fp.label_full(i["label"], i["grams"], unit),
                               k100=round(i["kcal"] / i["grams"] * 100), p=i["p"],
                               cat=fp.category(dict(i, grams=i["grams"])), page=f"{lc['dir']}/{slug}.html"))
        out[code] = sorted(dishes, key=lambda d: d["k100"])
    return out


def stats(data):
    rows = []
    for code, ds in data.items():
        k = [d["k100"] for d in ds]
        rows.append(dict(code=code, cuisine=CUISINE[code], n=len(ds), median=round(statistics.median(k)),
                         lightest=ds[0], densest=ds[-1]))
    rows.sort(key=lambda r: -r["median"])
    return rows


def write_csv(data):
    p = ROOT / CSV_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cuisine", "dish", "serving", "serving_grams_or_ml", "kcal_per_serving", "kcal_per_100", "protein_g_per_serving", "page"])
        for code in LANGS:
            for d in data[code]:
                w.writerow([CUISINE[code], d["name"], d["label"], d["grams"], d["kcal"], d["k100"], d["p"], SITE + d["page"]])


def page(L, T, C, data, rows, style):
    pre = "" if L in ("en", "tr") else "../"
    me = SITE + path_of(L)
    n = sum(r["n"] for r in rows)
    cn = T["cuisines"]
    cap = {k: v[:1].upper() + v[1:] for k, v in cn.items()}  # standalone use (table, headings)
    top, low = rows[0], rows[-1]
    kw = dict(n=n, top=cn[top["cuisine"]], topk=top["median"], low=cn[low["cuisine"]], lowk=low["median"])
    alts = "".join(f'<link rel="alternate" hreflang="{x}" href="{SITE + path_of(x)}">\n' for x in LANGS)
    alts += f'<link rel="alternate" hreflang="x-default" href="{SITE + path_of("en")}">\n'
    faq = [(fill(q, **kw), fill(a, **kw)) for q, a in T["faq"]]
    ld = [{"@context": "https://schema.org", "@type": "Dataset", "name": T["h1"], "description": fill(T["desc"], **kw),
           "url": me, "inLanguage": C["lang"], "dateModified": TODAY, "license": "https://creativecommons.org/licenses/by/4.0/",
           "creator": {"@type": "Organization", "name": "Pofu", "url": SITE},
           "distribution": {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": SITE + CSV_PATH},
           "variableMeasured": ["kcal per serving", "kcal per 100 g"]},
          {"@context": "https://schema.org", "@type": "FAQPage", "url": me, "inLanguage": C["lang"],
           "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}]
    here = Path(path_of(L)).parent

    def link(d):
        rel = Path(d["page"])
        h = str(rel) if str(here) == "." else "../" + str(rel)
        return f'<a href="{esc(h)}">{esc(d["name"])}</a>'

    rank = "".join(
        f'<tr><th scope="row"><a href="#c-{r["cuisine"]}">{esc(cap[r["cuisine"]])}</a></th><td>{r["n"]}'
        + (f' <span class="k">({esc(T["small"])})</span>' if r["n"] < SMALL else "")
        + f'</td><td>{r["median"]}</td><td>{link(r["lightest"])} · {r["lightest"]["k100"]}</td>'
        f'<td>{link(r["densest"])} · {r["densest"]["k100"]}</td></tr>\n' for r in rows)
    detail = ""
    for r in rows:
        ds = data[r["code"]]
        trs = "".join(f'<tr><th scope="row" lang="{fp.LANGS[r["code"]]["code"]}">{link(d)}</th><td>{esc(d["label"])}</td>'
                      f'<td>{d["kcal"]}</td><td>{d["k100"]}</td></tr>\n' for d in ds)
        detail += (f'<h3 id="c-{r["cuisine"]}">{esc(cap[r["cuisine"]])} <span class="k">· {r["median"]} kcal / 100 g</span></h3>\n'
                   f'<div class="tblwrap"><table class="tbl"><thead><tr>'
                   + "".join(f'<th scope="col">{esc(c)}</th>' for c in T["detail_cols"])
                   + f"</tr></thead><tbody>\n{trs}</tbody></table></div>\n")
    finds = [fill(T["find_top"], **kw), fill(T["find_low"], **kw), T["find_soup"], T["find_portion"]]
    home = "tr/pofu.html" if L == "tr" else "pofu.html"
    legal = "tr/" if L == "tr" else pre
    store = f"https://apps.apple.com/app/apple-store/id6778044605?pt=128375664&amp;ct=dishes_{L}&amp;mt=8"
    food_hub = fp.LANGS[L]["dir"] + "/"
    food_href = food_hub if str(here) == "." else "../" + food_hub
    dir_attr = ' dir="rtl"' if L == "ar" else ""
    return f'''<!doctype html>
<html lang="{C['lang']}"{dir_attr}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(T['title'])}</title>
<meta name="description" content="{esc(fill(T['desc'], **kw))}">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<link rel="canonical" href="{me}">
{alts}<meta name="apple-itunes-app" content="app-id=6778044605">
<meta name="color-scheme" content="light dark">
<meta property="og:type" content="article">
<meta property="og:locale" content="{C['og_locale']}">
<meta property="og:title" content="{esc(T['h1'])}">
<meta property="og:description" content="{esc(fill(T['desc'], **kw))}">
<meta property="og:url" content="{me}">
<meta property="og:image" content="https://getpofu.com/assets/img/{C['og_img']}">
<link rel="icon" type="image/png" sizes="64x64" href="{pre}assets/pofu-favicon.png?v=20260703">
<link rel="apple-touch-icon" sizes="180x180" href="{pre}assets/apple-touch-icon.png?v=20260703">
<style>{style}
.tbl {{ width: 100%; border-collapse: collapse; font-size: .93rem; }}
.tbl th, .tbl td {{ text-align: start; vertical-align: top; padding: .5rem .45rem; border-top: 1px solid var(--line); }}
.tbl thead th {{ border-top: 0; }}
.tblwrap {{ overflow-x: auto; margin-bottom: 1rem; }}
.k {{ color: var(--ink2); font-weight: 400; font-size: .9rem; }}
</style>
{"".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' + chr(10) for x in ld)}</head>
<body>
<a class="skip" href="#main">{C['skip']}</a>
<header class="top">
<div class="wrap top__in">
<a class="brand" href="{home}" aria-label="Pofu"><img src="{pre}assets/img/icon-96.webp" alt="" width="34" height="34"><span>Pofu</span></a>
<a class="btn btn--sm" href="{store}">{C['get_app']}</a>
</div>
</header>
<main id="main" class="wrap">
<section class="hero">
<p class="pill">{T['pill']}</p>
<h1>{T['h1']}</h1>
<p class="lede">{fill(T['lede'], **kw)}</p>
<p class="fine">{C['byline']}</p>
</section>
<section id="findings">
<h2>{T['h_find']}</h2>
<ul>
{"".join(f"<li>{x}</li>" for x in finds)}
</ul>
</section>
<section id="ranking">
<h2>{T['h_rank']}</h2>
<div class="tblwrap"><table class="tbl"><thead><tr>{"".join(f'<th scope="col">{esc(c)}</th>' for c in T['rank_cols'])}</tr></thead>
<tbody>
{rank}</tbody></table></div>
<p><a href="{pre}{CSV_PATH}" download>{T['csv']}</a> · {T['cite']}</p>
</section>
<section id="dishes">
<h2>{T['h_detail']}</h2>
{detail}</section>
<section id="method">
<h2>{T['h_method']}</h2>
<ul>
{"".join(f"<li>{x}</li>" for x in T['method'])}
</ul>
</section>
<section id="faq">
<h2>{T['h_faq']}</h2>
{"".join(f"<h3>{esc(q)}</h3>{chr(10)}<p>{esc(a)}</p>{chr(10)}" for q, a in faq)}</section>
<section id="related">
<h2>{T['h_rel']}</h2>
<ul>
<li><a href="{food_href}">{T['rel_food']}</a></li>
</ul>
</section>
<section id="not-medical">
<div class="note"><p>{C['medical']}</p></div>
</section>
</main>
<footer class="foot">
<div class="wrap">
<nav aria-label="{esc(C['foot_nav'])}">
<a href="{home}">Pofu</a>
<a href="{legal}privacy.html">{C['privacy_l']}</a>
<a href="{legal}terms.html">{C['terms_l']}</a>
<a href="{pre}support.html">{C['support_l']}</a>
</nav>
<p>{C['updated']}</p>
<p>{C['tm']}</p>
</div>
</footer>
</body>
</html>
'''


def main():
    data = collect()
    rows = stats(data)
    if "--stats" in sys.argv:
        for r in rows:
            print(r["cuisine"], r["n"], r["median"], r["lightest"]["name"], r["lightest"]["cat"], r["lightest"]["k100"],
                  "|", r["densest"]["name"], r["densest"]["k100"])
        return
    write_csv(data)
    style = re.search(r"<style>(.*?)</style>", (ROOT / "cycle-calorie-calculator.html").read_text(encoding="utf-8"), re.S).group(1)
    n = 0
    for L in LANGS:
        f = ROOT / "data" / "dishes" / f"{L}.json"
        if not f.exists():
            continue
        T = json.loads(f.read_text(encoding="utf-8"))
        C = json.loads((ROOT / "data" / "tools" / f"{L}.json").read_text(encoding="utf-8"))["common"]
        p = ROOT / path_of(L)
        out = page(L, T, C, data, rows, style)
        if p.exists():  # keep the header menu added by apply_nav.py
            m = re.search(r"<!-- nav:start -->.*?<!-- nav:end -->", p.read_text(encoding="utf-8"), re.S)
            if m:
                out = out.replace('<a class="btn btn--sm"', m.group(0) + '\n<a class="btn btn--sm"', 1)
        p.write_text(out, encoding="utf-8")
        n += 1
    print("pages written:", n, "csv rows:", sum(len(v) for v in data.values()))


if __name__ == "__main__":
    main()
