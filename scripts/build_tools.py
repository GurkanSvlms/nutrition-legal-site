#!/usr/bin/env python3
"""Free calculators (protein, macros, calorie deficit by goal date, BMI) in every site language.

    python3 scripts/build_tools.py            # write all pages from data/tools/<lang>.json
    python3 scripts/build_tools.py --check    # validate the JSON files only
    python3 scripts/build_tools.py --partial  # only languages whose JSON exists

Text lives in data/tools/<lang>.json (en.json is the reference: same keys in every file).
Math lives in assets/cycle-calories.js + assets/women-tools.js (tests: scripts/test_women_tools.js).
After building, run scripts/apply_nav.py so the pages get the header/footer menus and hub entries.
"""
import html as htmllib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "tools"
SITE = "https://getpofu.com/"
LANGS = ["en", "tr", "de", "fr", "es", "it", "pt-BR", "nl", "pl", "ru", "uk", "cs", "ro", "sv", "ja", "ko",
         "zh-Hans", "id", "vi", "th", "hi", "ar"]
TOOLS = ["protein", "macro", "deficit", "bmi"]
SLUG = {"protein": "protein-calculator-for-women.html", "macro": "macro-calculator-for-women.html",
        "deficit": "calorie-deficit-calculator.html", "bmi": "bmi-calculator-for-women.html"}
TR_SLUG = {"protein": "kadinlar-icin-protein-ihtiyaci-hesaplama.html", "macro": "kadinlar-icin-makro-hesaplama.html",
           "deficit": "kalori-acigi-hesaplama.html", "bmi": "kadinlar-icin-vucut-kitle-endeksi-hesaplama.html"}
# Existing tools linked from "related": (en/other file, tr file)
OLD_TOOLS = [("cycle-calorie-calculator.html", "kadin-gunluk-kalori-ihtiyaci-hesaplama.html"),
             ("period-water-weight-calculator.html", "regl-kilosu-su-mu-yag-mi.html")]
TODAY = "2026-11-06"
# app screen recording shown under "How this calculator works" (assets/video/demo-<clip>.mp4 + .jpg), if the file exists
TOOL_CLIP = {"protein": "today", "macro": "today", "deficit": "today", "bmi": "streak"}


def path_of(L, tool):
    """Site-relative file path of a tool page."""
    if L == "en":
        return SLUG[tool]
    if L == "tr":
        return TR_SLUG[tool]
    return f"{L}/{SLUG[tool]}"


def prefix(L):
    return "" if L in ("en", "tr") else "../"


def url(L, tool):
    return SITE + path_of(L, tool)


def esc(s):
    return htmllib.escape(s, quote=True)


def css():
    t = (ROOT / "cycle-calorie-calculator.html").read_text(encoding="utf-8")
    return re.search(r"<style>(.*?)</style>", t, re.S).group(1)  # first block = page styles (second is the nav)


def h1_of(rel):
    t = (ROOT / rel).read_text(encoding="utf-8")
    return re.sub(r"<[^>]+>", "", re.search(r"<h1[^>]*>(.*?)</h1>", t, re.S).group(1)).strip()


def load(L):
    return json.loads((DATA / f"{L}.json").read_text(encoding="utf-8"))


def keys(o, p=""):
    if isinstance(o, dict):
        out = set()
        for k, v in o.items():
            out |= {p + k} | keys(v, p + k + ".")
        return out
    return set()


def placeholders(o):
    if isinstance(o, str):
        return set(re.findall(r"\{\w+\}", o))
    if isinstance(o, dict):
        return {(k, x) for k, v in o.items() for x in placeholders(v)}
    if isinstance(o, list):
        return {(i, x) for i, v in enumerate(o) for x in placeholders(v)}
    return set()


def check():
    en = load("en")
    ok = True
    for L in LANGS:
        f = DATA / f"{L}.json"
        if not f.exists():
            print(L, "missing"); ok = False; continue
        try:
            d = load(L)
        except Exception as e:
            print(L, "json", e); ok = False; continue
        miss, extra = keys(en) - keys(d), keys(d) - keys(en)
        if miss or extra:
            print(L, "keys", sorted(miss)[:8], sorted(extra)[:8]); ok = False
        for t in TOOLS:  # placeholders like {goal} must survive translation
            for k in ("too_fast", "res_ok", "range", "s_range", "pct", "low_goal"):
                a, b = en["tools"][t].get(k), d.get("tools", {}).get(t, {}).get(k)
                if a and b and set(re.findall(r"\{\w+\}", a)) != set(re.findall(r"\{\w+\}", b)):
                    print(L, t, k, "placeholders differ"); ok = False
            if len(d.get("tools", {}).get(t, {}).get("faq", [])) < 4:
                print(L, t, "faq < 4"); ok = False
    return ok


UNIT_FIELDS = {  # which inputs each tool needs
    "protein": ("weight",), "macro": ("age", "height", "weight", "activity"),
    "deficit": ("age", "height", "weight", "activity"), "bmi": ("height", "weight"),
}


def form(L, d, tool):
    c, t = d["common"], d["tools"][tool]
    us = c["us"]
    need = UNIT_FIELDS[tool]
    f = []
    if "age" in need:
        f.append(f'<div class="field"><label for="age">{c["f_age"]}</label><input id="age" name="age" type="number" '
                 'inputmode="numeric" min="18" max="80" placeholder="30" required></div>')
    if us:
        f.append(f'<div class="field"><label for="system">{c["f_system"]}</label><select id="system" name="system">'
                 f'<option value="us" selected>{c["sys_us"]}</option><option value="metric">{c["sys_metric"]}</option></select></div>')
    if "height" in need:
        if us:
            f.append(f'<div class="field" data-us><span class="lbl"><b>{c["f_height"]}</b></span><div class="two">'
                     f'<input name="ft" type="number" inputmode="numeric" min="4" max="7" placeholder="ft" aria-label="{c["a_ft"]}">'
                     f'<input name="inch" type="number" inputmode="numeric" min="0" max="11" placeholder="in" aria-label="{c["a_in"]}"></div></div>')
        f.append(f'<div class="field" data-metric{" hidden" if us else ""}><label for="cm">{c["f_height"]} (cm)</label>'
                 '<input id="cm" name="cm" type="text" inputmode="decimal" placeholder="165"></div>')
    for name, label, ph in (("w", c["f_weight"], "65"),) + ((("g", t.get("f_goal_kg", ""), "60"),) if tool == "deficit" else ()):
        if us:
            f.append(f'<div class="field" data-us><label for="{name}lb">{label} (lb)</label>'
                     f'<input id="{name}lb" name="{name}lb" type="text" inputmode="decimal"></div>')
        f.append(f'<div class="field" data-metric{" hidden" if us else ""}><label for="{name}kg">{label} (kg)</label>'
                 f'<input id="{name}kg" name="{name}kg" type="text" inputmode="decimal" placeholder="{ph}"></div>')
    if "activity" in need:
        opts = "".join(f'<option value="{k}"{" selected" if k == "moderate" else ""}>{v}</option>' for k, v in c["activity"].items())
        f.append(f'<div class="field"><label for="activity">{c["f_activity"]}</label><select id="activity" name="activity">{opts}</select></div>')
    if tool in ("protein", "macro"):
        dflt = "lose"
        opts = "".join(f'<option value="{k}"{" selected" if k == dflt else ""}>{v}</option>' for k, v in t["goals"].items())
        f.append(f'<div class="field"><label for="goal">{t["f_goal"]}</label><select id="goal" name="goal">{opts}</select></div>')
    if tool == "deficit":
        f.append(f'<div class="field"><label for="date">{t["f_date"]}</label><input id="date" name="date" type="date" required></div>')
    return "\n".join(f)


SCRIPT = r"""
(function () {
  var T = window.__T, f = document.getElementById('cc-form'), out = document.getElementById('cc-result');
  var d = new Date(); var today = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  if (f.date) f.date.min = today;
  function n(v) { return +String(v || '').replace(',', '.'); }
  function fmt(x, dec) { return (+x).toLocaleString(T.locale, { maximumFractionDigits: dec || 0, minimumFractionDigits: dec || 0 }); }
  function sys() { return f.system ? f.system.value : 'metric'; }
  function sync() { var us = sys() === 'us'; document.querySelectorAll('[data-us]').forEach(function (e) { e.hidden = !us; }); document.querySelectorAll('[data-metric]').forEach(function (e) { e.hidden = us; }); }
  if (f.system) { f.system.addEventListener('change', sync); sync(); }
  function sub(s, o) { return s.replace(/\{(\w+)\}/g, function (m, k) { return k in o ? o[k] : m; }); }
  function stat(v, l) { return '<div class="stat"><b>' + v + '</b><span>' + l + '</span></div>'; }
  function day(iso) { var p = iso.split('-'); return new Date(+p[0], +p[1] - 1, +p[2]).toLocaleDateString(T.locale, { year: 'numeric', month: 'long', day: 'numeric' }); }
  function addDays(k) { var x = new Date(d.getFullYear(), d.getMonth(), d.getDate() + k); return x.getFullYear() + '-' + String(x.getMonth() + 1).padStart(2, '0') + '-' + String(x.getDate()).padStart(2, '0'); }
  f.addEventListener('submit', function (e) {
    e.preventDefault();
    var us = sys() === 'us', LB = 0.45359237;
    var h = f.cm ? (us ? (n(f.ft.value) * 12 + n(f.inch.value)) * 2.54 : n(f.cm.value)) : 165;
    var w = us ? n(f.wlb.value) * LB : n(f.wkg.value);
    var kgOut = function (kg) { var v = us ? kg / LB : kg; return v.toLocaleString(T.locale, { maximumFractionDigits: 1 }) + (us ? ' lb' : ' kg'); };
    var r, html = '';
    out.hidden = false;
    function fail(k) { out.innerHTML = '<p class="err">' + T.errors[k] + '</p>'; out.focus(); }
    if (T.tool === 'protein') {
      r = WomenTools.protein({ weightKg: w, goal: f.goal.value });
      if (r.error) return fail(r.error);
      html = '<p class="meta">' + T.res_head + '</p><p class="big">' + fmt(r.g) + ' g</p><div class="stats">' +
        stat(fmt(r.perMeal3) + ' g', T.s_meal3) + stat(fmt(r.perMeal4) + ' g', T.s_meal4) +
        stat(fmt(r.low) + '–' + fmt(r.high) + ' g', T.s_range) + '</div><p>' + T.explain + '</p>';
    } else if (T.tool === 'bmi') {
      r = WomenTools.bmi({ heightCm: h, weightKg: w });
      if (r.error) return fail(r.error);
      html = '<p class="meta">' + T.res_head + '</p><p class="big">' + fmt(r.bmi, 1) + '</p><p><strong>' + T.cats[r.cat] + '</strong></p>' +
        '<p>' + sub(T.range, { low: kgOut(r.lowKg), high: kgOut(r.highKg) }) + '</p><p>' + T.explain + '</p>';
    } else {
      var goal = T.tool === 'macro' ? f.goal.value : 'maintain';
      r = CycleCalories.calc({ age: n(f.age.value), heightCm: h, weightKg: w, activity: f.activity.value, goal: goal });
      if (r.error) return fail(r.error);
      if (T.tool === 'macro') {
        var pc = function (g, k) { return Math.round(g * k * 100 / r.target); };
        html = '<p class="meta">' + T.res_head + '</p><p class="big">' + fmt(r.target) + ' kcal</p><div class="stats">' +
          stat(fmt(r.proteinG) + ' g', T.s_p + ' · ' + sub(T.pct, { p: pc(r.proteinG, 4) })) +
          stat(fmt(r.carbsG) + ' g', T.s_c + ' · ' + sub(T.pct, { p: pc(r.carbsG, 4) })) +
          stat(fmt(r.fatG) + ' g', T.s_f + ' · ' + sub(T.pct, { p: pc(r.fatG, 9) })) + '</div>';
        if (r.floorApplied) html += '<p>' + T.floor + '</p>';
        html += '<p>' + T.explain + '</p>';
      } else {
        var gkg = us ? n(f.glb.value) * LB : n(f.gkg.value);
        if (!/^\d{4}-\d{2}-\d{2}$/.test(f.date.value)) return fail('date');
        var p = f.date.value.split('-'), days = Math.round((new Date(+p[0], +p[1] - 1, +p[2]) - new Date(d.getFullYear(), d.getMonth(), d.getDate())) / 86400000);
        var g = WomenTools.goalPlan({ tdee: r.tdee, weightKg: w, goalKg: gkg, days: days, heightCm: h });
        if (g.error) return fail(g.error);
        if (g.feasible) {
          html = '<p class="meta">' + sub(T.res_ok, { goal: kgOut(gkg), date: day(f.date.value) }) + '</p><p class="big">' + fmt(g.target) + ' kcal</p><div class="stats">' +
            stat(fmt(g.deficit) + ' kcal', T.s_deficit) + stat(kgOut(g.weeklyKg), T.s_week) + stat(fmt(r.tdee) + ' kcal', T.s_maint) + '</div>';
        } else {
          html = '<p class="err">' + sub(T.too_fast, { need: fmt(g.deficit), max: fmt(g.safeDeficit), goal: kgOut(gkg), date: day(addDays(g.safeDays)), target: fmt(g.safeTarget) }) + '</p>' +
            '<div class="stats">' + stat(fmt(g.safeTarget) + ' kcal', T.s_target) + stat(fmt(r.tdee) + ' kcal', T.s_maint) + '</div>';
        }
        if (g.lowGoal) html += '<p>' + T.low_goal + '</p>';
        html += '<p>' + T.explain + '</p>';
      }
    }
    out.innerHTML = html + T.bridge; out.focus();
  });
})();
"""


def tf_caption(L):
    """'Screen recording from the Pofu app (English interface)' in L, from data/trust/<L>.json."""
    f = ROOT / "data" / "trust" / f"{L}.json"
    if not f.exists():
        return ""
    return re.split(r"\s*[:：]\s*", json.loads(f.read_text(encoding="utf-8"))["food"]["video_caption"], maxsplit=1)[0]


def page(L, d, tool, style):
    c, t = d["common"], d["tools"][tool]
    pre = prefix(L)
    me = url(L, tool)
    store = f"https://apps.apple.com/app/apple-store/id6778044605?pt=128375664&amp;ct=tool_{tool}_{L}&amp;mt=8"
    alts = "".join(f'<link rel="alternate" hreflang="{x}" href="{url(x, tool)}">\n' for x in LANGS)
    alts += f'<link rel="alternate" hreflang="x-default" href="{url("en", tool)}">\n'
    app_ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": t["h1"], "url": me, "inLanguage": c["lang"],
              "applicationCategory": "HealthApplication", "operatingSystem": "Any (web browser)", "isAccessibleForFree": True,
              "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
              "author": {"@type": "Person", "name": "Ali Gürkan Sevilmiş"},
              "publisher": {"@id": "https://getpofu.com/#org", "@type": "Organization", "name": "Pofu", "url": SITE},
              "datePublished": TODAY, "dateModified": TODAY, "description": t["desc"]}
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "url": me, "inLanguage": c["lang"],
              "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)}}
                             for q, a in t["faq"]]}
    bridge = (f'<div class="bridge"><p>{t["bridge"]}</p><p class="cta"><a href="{store}"><img src="{pre}assets/img/app-store-badge.png" '
              f'alt="{esc(c["badge_alt"])}" width="180" height="60"></a></p></div>')
    T = {k: v for k, v in t.items() if k not in ("faq", "how", "sources", "body", "lede", "title", "desc", "og_title", "h1", "tool_h",
                                                     "goals", "f_goal", "f_goal_kg", "f_date", "bridge", "note")}
    T.update(tool=tool, locale=c["locale"], errors=c["errors"] | t.get("errors", {}), bridge=bridge)
    # related: the other new tools + the two existing ones, same language
    rel = [(path_of(L, x), d["tools"][x]["h1"]) for x in TOOLS if x != tool]
    for en_f, tr_f in OLD_TOOLS:
        p = tr_f if L == "tr" else en_f if L == "en" else f"{L}/{en_f}"
        if (ROOT / p).exists():
            rel.append((p, h1_of(p)))
    here_dir = "" if L in ("en", "tr") else L + "/"
    rel_html = "\n".join(f'<li><a href="{p[len(here_dir):] if p.startswith(here_dir) else pre + p}">{esc(h)}</a></li>' for p, h in rel)
    home = "tr/pofu.html" if L == "tr" else "pofu.html"
    legal = "tr/" if L == "tr" else pre
    foot = (f'<a href="{home}">Pofu</a>\n<a href="{legal}privacy.html">{c["privacy_l"]}</a>\n'
            f'<a href="{legal}terms.html">{c["terms_l"]}</a>\n<a href="{pre}support.html">{c["support_l"]}</a>')
    how = "\n".join(f"<li>{x}</li>" for x in t["how"])
    src = "\n".join(f"<li>{x}</li>" for x in t["sources"])
    faq_html = "\n".join(f"<h3>{q}</h3>\n<p>{a}</p>" for q, a in t["faq"])
    clip = TOOL_CLIP.get(tool)
    clip_html = ""
    if clip and (ROOT / f"assets/video/demo-{clip}.mp4").exists() and tf_caption(L):
        clip_html = (f'<figure class="demo"><video controls muted playsinline preload="none" width="270" height="587" '
                     f'poster="{pre}assets/video/demo-{clip}.jpg"><source src="{pre}assets/video/demo-{clip}.mp4" type="video/mp4"></video>'
                     f'<figcaption>{esc(tf_caption(L))}</figcaption></figure>')
    embed_code = (f'<iframe src="{me}?embed=1" title="{esc(t["h1"])}" width="100%" height="940" loading="lazy" '
                  f'style="border:0;max-width:640px"></iframe>\n<p><a href="{me}">{esc(t["h1"])}</a> · Pofu</p>')
    dir_attr = ' dir="rtl"' if L == "ar" else ""
    tf = TRUST / f"{L}.json"
    method_label = json.loads(tf.read_text(encoding="utf-8"))["food"]["method_link"] if tf.exists() else ""
    method_href = method_path(L)[len(L) + 1:] if L not in ("en", "tr") else method_path(L)
    return f'''<!doctype html>
<html lang="{c['lang']}"{dir_attr}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(t['title'])}</title>
<meta name="description" content="{esc(t['desc'])}">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<link rel="canonical" href="{me}">
{alts}<meta name="apple-itunes-app" content="app-id=6778044605">
<meta name="color-scheme" content="light dark">
<meta property="og:type" content="website">
<meta property="og:locale" content="{c['og_locale']}">
<meta property="og:title" content="{esc(t['og_title'])}">
<meta property="og:description" content="{esc(t['desc'])}">
<meta property="og:url" content="{me}">
<meta property="og:image" content="https://getpofu.com/assets/img/{c['og_img']}">
<link rel="icon" type="image/png" sizes="64x64" href="{pre}assets/pofu-favicon.png?v=20260703">
<link rel="apple-touch-icon" sizes="180x180" href="{pre}assets/apple-touch-icon.png?v=20260703">
<style>{style}
.demo {{ margin: .8rem 0 0; }}
.demo video {{ display: block; width: 100%; max-width: 270px; height: auto; border-radius: 1rem; border: 1px solid var(--line); background: var(--card); }}
.demo figcaption {{ font-size: .88rem; color: var(--ink2); margin-top: .4rem; }}
#embed textarea {{ width: 100%; min-height: 6.5rem; font: .82rem/1.4 ui-monospace, Menlo, monospace; padding: .6rem; border: 1px solid var(--line); border-radius: .6rem; background: var(--card); color: var(--ink); }}
.embed-by {{ display: none; }}
.embed body {{ background: transparent; }}
.embed .skip, .embed header.top, .embed .hero, .embed main > section:not(#tool), .embed footer {{ display: none !important; }}
.embed #tool {{ margin: 0; padding: 0; }}
.embed .embed-by {{ display: block; margin: .6rem 0 0; font-size: .85rem; }}
</style>
<script>if (/[?&]embed=1/.test(location.search)) {{ document.documentElement.classList.add('embed'); document.write('<base target="_blank">'); }}</script>
<script type="application/ld+json">
{json.dumps(app_ld, ensure_ascii=False)}
</script>
<script type="application/ld+json">
{json.dumps(faq_ld, ensure_ascii=False)}
</script>
</head>
<body>
<a class="skip" href="#main">{c['skip']}</a>
<header class="top">
<div class="wrap top__in">
<a class="brand" href="{home}" aria-label="Pofu"><img src="{pre}assets/img/icon-96.webp" alt="" width="34" height="34"><span>Pofu</span></a>
<a class="btn btn--sm" href="{store}">{c['get_app']}</a>
</div>
</header>
<main id="main" class="wrap">
<section class="hero">
<p class="pill">{c['pill']}</p>
<h1>{t['h1']}</h1>
<p class="lede">{t['lede']}</p>
<p class="fine">{c['byline']}</p>
</section>
<section id="tool" class="tool" aria-labelledby="tool-h">
<h2 id="tool-h">{t['tool_h']}</h2>
<div class="card">
<form id="cc-form" novalidate>
{form(L, d, tool)}
<button class="btn" type="submit">{c['submit']}</button>
<p class="fine">{c['privacy']}</p>
</form>
<div id="cc-result" class="result" role="status" aria-live="polite" tabindex="-1" hidden></div>
<p class="embed-by"><a href="{me}">{c['embed_by']}</a></p>
</div>
</section>
<section id="how">
<h2>{c['how_h']}</h2>
<ul>
{how}
</ul>
<p>{t['note']}</p>
{clip_html}
</section>
<section id="sources">
<h2>{c['src_h']}</h2>
<ul>
{src}
</ul>
<p class="fine">{c['method_note']} <a href="{method_href}">{method_label}</a>.</p>
</section>
<section id="embed">
<h2>{c['embed_h']}</h2>
<p>{c['embed_p']}</p>
<textarea id="embed-code" readonly aria-label="{esc(c['embed_h'])}">{esc(embed_code)}</textarea>
<p><button class="btn btn--sm" type="button" id="embed-copy" data-done="{esc(c['embed_copied'])}">{c['embed_copy']}</button></p>
</section>
<section id="faq">
<h2>{c['faq_h']}</h2>
{faq_html}
</section>
<section id="related">
<h2>{c['rel_h']}</h2>
<ul>
{rel_html}
</ul>
</section>
<section id="not-medical">
<div class="note"><p>{c['medical']}</p></div>
</section>
</main>
<footer class="foot">
<div class="wrap">
<nav aria-label="{esc(c['foot_nav'])}">
{foot}
</nav>
<p>{c['updated']}</p>
<p>{c['tm']}</p>
</div>
</footer>
<script src="{pre}assets/cycle-calories.js?v={TODAY}"></script>
<script src="{pre}assets/women-tools.js?v={TODAY}"></script>
<script>window.__T = {json.dumps(T, ensure_ascii=False)};</script>
<script>{SCRIPT}</script>
<script>(function () {{ var b = document.getElementById('embed-copy'), t = document.getElementById('embed-code'); if (!b) return;
  b.addEventListener('click', function () {{ t.select(); (navigator.clipboard ? navigator.clipboard.writeText(t.value) : Promise.reject()).catch(function () {{ document.execCommand('copy'); }}); b.textContent = b.dataset.done; }}); }})();</script>
</body>
</html>
'''


# ----------------------------------------------------------------------------- editorial policy page
TRUST = ROOT / "data" / "trust"


def method_path(L):
    return "editorial-policy.html" if L == "en" else "icerik-ve-kaynak-politikasi.html" if L == "tr" else f"{L}/editorial-policy.html"


def method_page(L, d, m, style):
    """'How we prepare our content and sources' page; strings in data/trust/<lang>.json["method"]."""
    c = d["common"]
    pre = prefix(L)
    me = SITE + method_path(L)
    alts = "".join(f'<link rel="alternate" hreflang="{x}" href="{SITE + method_path(x)}">\n' for x in LANGS)
    alts += f'<link rel="alternate" hreflang="x-default" href="{SITE + method_path("en")}">\n'
    ld = {"@context": "https://schema.org", "@type": "AboutPage", "name": m["h1"], "url": me, "inLanguage": c["lang"],
          "description": m["desc"], "dateModified": TODAY,
          "author": {"@type": "Person", "name": "Ali Gürkan Sevilmiş"},
          "publisher": {"@id": "https://getpofu.com/#org", "@type": "Organization", "name": "Pofu", "url": SITE}}
    home = "tr/pofu.html" if L == "tr" else "pofu.html"
    legal = "tr/" if L == "tr" else pre
    store = f"https://apps.apple.com/app/apple-store/id6778044605?pt=128375664&amp;ct=method_{L}&amp;mt=8"
    secs = "\n".join(f'<section>\n<h2>{h}</h2>\n{b}\n</section>' for h, b in m["sections"])
    tools = "\n".join(f'<li><a href="{path_of(L, t)[len(L) + 1:] if L not in ("en", "tr") else path_of(L, t)}">{esc(d["tools"][t]["h1"])}</a></li>'
                      for t in TOOLS)
    foot = (f'<a href="{home}">Pofu</a>\n<a href="{legal}privacy.html">{c["privacy_l"]}</a>\n'
            f'<a href="{legal}terms.html">{c["terms_l"]}</a>\n<a href="{pre}support.html">{c["support_l"]}</a>')
    dir_attr = ' dir="rtl"' if L == "ar" else ""
    return f'''<!doctype html>
<html lang="{c['lang']}"{dir_attr}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(m['title'])}</title>
<meta name="description" content="{esc(m['desc'])}">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<link rel="canonical" href="{me}">
{alts}<meta name="apple-itunes-app" content="app-id=6778044605">
<meta name="color-scheme" content="light dark">
<meta property="og:type" content="website">
<meta property="og:locale" content="{c['og_locale']}">
<meta property="og:title" content="{esc(m['h1'])}">
<meta property="og:description" content="{esc(m['desc'])}">
<meta property="og:url" content="{me}">
<meta property="og:image" content="https://getpofu.com/assets/img/{c['og_img']}">
<link rel="icon" type="image/png" sizes="64x64" href="{pre}assets/pofu-favicon.png?v=20260703">
<link rel="apple-touch-icon" sizes="180x180" href="{pre}assets/apple-touch-icon.png?v=20260703">
<style>{style}</style>
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False)}
</script>
</head>
<body>
<a class="skip" href="#main">{c['skip']}</a>
<header class="top">
<div class="wrap top__in">
<a class="brand" href="{home}" aria-label="Pofu"><img src="{pre}assets/img/icon-96.webp" alt="" width="34" height="34"><span>Pofu</span></a>
<a class="btn btn--sm" href="{store}">{c['get_app']}</a>
</div>
</header>
<main id="main" class="wrap">
<section class="hero">
<h1>{m['h1']}</h1>
<p class="lede">{m['lede']}</p>
<p class="fine">{c['byline']}</p>
</section>
{secs}
<section id="related">
<h2>{c['rel_h']}</h2>
<ul>
{tools}
</ul>
</section>
</main>
<footer class="foot">
<div class="wrap">
<nav aria-label="{esc(c['foot_nav'])}">
{foot}
</nav>
<p>{c['updated']}</p>
<p>{c['tm']}</p>
</div>
</footer>
</body>
</html>
'''


def main():
    global LANGS
    if "--partial" in sys.argv:  # build only the languages that have a JSON file (while translating)
        LANGS = [L for L in LANGS if (DATA / f"{L}.json").exists()]
    if not check():
        sys.exit(1)
    if "--check" in sys.argv:
        print("ok"); return
    style = css()
    n = 0
    for L in LANGS:
        d = load(L)
        for tool in TOOLS:
            p = ROOT / path_of(L, tool)
            p.parent.mkdir(exist_ok=True)
            new = page(L, d, tool, style)
            if p.exists():  # keep the nav blocks apply_nav.py added; it re-syncs them afterwards
                old = p.read_text(encoding="utf-8")
                for a, b in (("<!-- nav:start -->", "<!-- nav:end -->"), ("<!-- footnav:start -->", "<!-- footnav:end -->")):
                    m = re.search(re.escape(a) + ".*?" + re.escape(b), old, re.S)
                    if m and a == "<!-- nav:start -->":
                        new = new.replace(f'<a class="btn btn--sm"', m.group(0) + '\n<a class="btn btn--sm"', 1)
            p.write_text(new, encoding="utf-8")
            n += 1
        tf = TRUST / f"{L}.json"
        if tf.exists():
            m = json.loads(tf.read_text(encoding="utf-8"))["method"]
            mp = ROOT / method_path(L)
            out = method_page(L, d, m, style)
            if mp.exists():  # keep the header menu apply_nav.py added
                mm = re.search(r"<!-- nav:start -->.*?<!-- nav:end -->", mp.read_text(encoding="utf-8"), re.S)
                if mm:
                    out = out.replace('<a class="btn btn--sm"', mm.group(0) + '\n<a class="btn btn--sm"', 1)
            mp.write_text(out, encoding="utf-8")
            n += 1
    print("pages written:", n)


if __name__ == "__main__":
    main()
