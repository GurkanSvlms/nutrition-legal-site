#!/usr/bin/env python3
"""Site navigation + hub pages for getpofu.com (static site, no build step).

RE-RUN AFTER ADDING PAGES (new guide / tool / comparison / translation):
    python3 scripts/apply_nav.py            # regenerate hubs, add/replace nav + footer, home sections, sitemap
    python3 scripts/apply_nav.py --check    # read-only: parse, links, JSON-LD, duplicate markers
    python3 scripts/apply_nav.py --no-hubs  # only nav/footer (leave hub pages alone)

It is idempotent: running twice changes nothing the second time.

What it does
  1. Hub pages per language (guides / tools / compare). Lists are built by scanning the
     language's files. A hub carrying <!-- hub:generated --> is regenerated on every run; a hub
     without that marker (hand edited) is never touched. Hub file names: see HUBFILE below.
     To list a new tool instead of a guide, add its file name to TOOL_NAMES (or end it in
     "calculator.html"/"hesaplama.html"); everything else that is not pofu-vs-* is a guide.
  2. <!-- nav:start/end -->    header menu (inside <header class="top"><div class="wrap top__in">).
     <!-- footnav:start/end --> footer hub links + language switcher (from the page's hreflang links).
     /* nav:css:start/end */   one <style> block before </head>. Head metadata is never changed.
  3. <!-- hubs:start/end -->    "Free tools & guides" section on index.html, tr/index.html, tr/pofu.html.
  4. Hub URLs are appended to sitemap.xml (only if missing).
Skipped: google*.html, non-pages, landing pages without the standard header (index.html, tr/index.html,
get/index.html get only the home section / nothing). Legal pages (privacy/terms/support) get only the footer block.
Edit labels in LABELS below, never in the generated HTML.
"""
import html as htmllib
import json
import os
import posixpath
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://getpofu.com/"
TODAY = "2026-11-06"
SKIN_V = "20261112"  # bump when assets/site.css changes (cache)

OTHER = ["de", "fr", "es", "it", "pt-BR", "nl", "pl", "ru", "uk", "cs", "ro", "sv", "ja", "ko",
         "zh-Hans", "id", "vi", "th", "hi", "ar"]
ALL = ["en", "tr"] + OTHER
SKIP_DIRS = {".git", "graphify-out", "node_modules", "data", "scripts", "assets"}
LANDING = {"index.html", "tr/index.html", "get/index.html"}  # own header design, no nav injection
NON_CONTENT = {"index.html", "pofu.html", "privacy.html", "terms.html", "support.html", "about.html",
               "editorial-policy.html", "icerik-ve-kaynak-politikasi.html"}
TOOL_NAMES = {"period-water-weight-calculator.html", "cycle-calorie-calculator.html",
              "regl-kilosu-su-mu-yag-mi.html", "kadin-gunluk-kalori-ihtiyaci-hesaplama.html"}
GUIDE_ORDER = ["best-calorie-counter-for-women.html", "kadinlar-icin-en-iyi-kalori-sayaci.html",
               "calorie-tracking-menstrual-cycle.html", "does-menstrual-cycle-affect-calorie-needs.html",
               "how-accurate-is-photo-calorie-counting.html", "fotograftan-kalori-hesaplama-ne-kadar-dogru.html",
               "calorie-counter-app-without-guilt.html", "kalori-sayarken-sucluluk.html"]
TOOL_ORDER = ["cycle-calorie-calculator.html", "period-water-weight-calculator.html",
              "kadin-gunluk-kalori-ihtiyaci-hesaplama.html", "regl-kilosu-su-mu-yag-mi.html",
              "calorie-deficit-calculator.html", "kalori-acigi-hesaplama.html",
              "macro-calculator-for-women.html", "kadinlar-icin-makro-hesaplama.html",
              "protein-calculator-for-women.html", "kadinlar-icin-protein-ihtiyaci-hesaplama.html",
              "bmi-calculator-for-women.html", "kadinlar-icin-vucut-kitle-endeksi-hesaplama.html"]

HUBFILE = {
    "en": {"guides": "guides.html", "tools": "tools.html", "compare": "compare.html"},
    "tr": {"guides": "rehberler.html", "tools": "araclar.html", "compare": "karsilastirmalar.html"},
}
for _l in OTHER:
    HUBFILE[_l] = {k: f"{_l}/{v}" for k, v in HUBFILE["en"].items()}
TEMPLATE = {"en": "calorie-counter-app-without-guilt.html", "tr": "kalori-sayarken-sucluluk.html"}

NAMES = {"en": "English", "tr": "Türkçe", "de": "Deutsch", "fr": "Français", "es": "Español", "it": "Italiano",
         "pt-BR": "Português (Brasil)", "nl": "Nederlands", "pl": "Polski", "ru": "Русский", "uk": "Українська",
         "cs": "Čeština", "ro": "Română", "sv": "Svenska", "ja": "日本語", "ko": "한국어", "zh-Hans": "简体中文",
         "id": "Bahasa Indonesia", "vi": "Tiếng Việt", "th": "ไทย", "hi": "हिन्दी", "ar": "العربية"}

# g guides, t tools, c calories, q Q&A, v compare, m menu, l languages, x explore
# gh/gd, th/td, vh/vd = hub h1 / description for guides, tools, compare; fh/fd = home section
LABELS = {
 "en": dict(g="Guides", t="Tools", c="Calories", q="Q&A", v="Compare", m="Menu", l="Languages", x="Explore",
   gh="Guides to calorie counting for women", gd="Practical, sourced guides on calorie tracking, your cycle and the scale, from how accurate photo logging is to counting calories without guilt.",
   th="Free calculators for women", td="Free calculators for period weight and for calorie needs across your cycle. No sign-up needed.",
   vh="Pofu compared with other calorie counters", vd="Honest side-by-side comparisons of Pofu with MyFitnessPal, Noom, Cronometer, Yazio and other calorie apps, written by Pofu's developer, who has a financial interest.",
   fh="Free tools & guides", fd="Calculators, guides and short answers about calories, your cycle and the scale.", vn=""),
 "tr": dict(g="Rehberler", t="Araçlar", c="Kalori", q="Sorular", v="Karşılaştırmalar", m="Menü", l="Diller", x="Keşfet",
   gh="Kadınlar için kalori sayma rehberleri", gd="Kalori takibi, döngü ve tartı hakkında kaynaklı, pratik rehberler: fotoğrafla kalori hesabının doğruluğundan suçluluk duymadan kalori saymaya.",
   th="Kadınlar için ücretsiz hesaplayıcılar", td="Regl kilosu ve günlük kalori ihtiyacı için ücretsiz hesaplayıcılar. Üyelik gerekmez.",
   vh="Pofu ve diğer kalori sayaçları: karşılaştırmalar", vd="Pofu'nun MyFitnessPal, Noom, Cronometer, Yazio ve diğer kalori uygulamalarıyla dürüst karşılaştırmaları. Pofu'nun geliştiricisi tarafından yazıldı; finansal çıkarı vardır.",
   fh="Ücretsiz araçlar ve rehberler", fd="Hesaplayıcılar, rehberler ve kalori, döngü ve tartı hakkında kısa cevaplar.", vn="Bu karşılaştırmalar şimdilik İngilizce."),
 "de": dict(g="Ratgeber", t="Rechner", c="Kalorien", q="Fragen", v="Vergleiche", m="Menü", l="Sprachen", x="Entdecken",
   gh="Ratgeber zum Kalorienzählen für Frauen", gd="Praktische Ratgeber mit Quellen zu Kalorientracking, Zyklus und Waage: von der Genauigkeit der Fotoerfassung bis zum Kalorienzählen ohne Schuldgefühle.",
   th="Kostenlose Rechner für Frauen", td="Kostenlose Rechner zu Zyklusgewicht und Kalorienbedarf im Zyklus. Ohne Anmeldung.",
   vh="Pofu im Vergleich mit anderen Kalorienzählern", vd="Ehrliche Vergleiche von Pofu mit MyFitnessPal, Noom, Cronometer, Yazio und weiteren Kalorien-Apps. Geschrieben vom Entwickler von Pofu, der ein finanzielles Interesse daran hat."),
 "fr": dict(g="Guides", t="Outils", c="Calories", q="Questions", v="Comparatifs", m="Menu", l="Langues", x="Explorer",
   gh="Guides du comptage des calories pour les femmes", gd="Guides pratiques et sourcés sur le suivi des calories, le cycle et la balance : de la précision du suivi par photo au comptage sans culpabilité.",
   th="Calculateurs gratuits pour les femmes", td="Calculateurs gratuits sur le poids lié aux règles et les besoins caloriques au fil du cycle. Sans inscription.",
   vh="Pofu face aux autres compteurs de calories", vd="Des comparatifs honnêtes de Pofu avec MyFitnessPal, Noom, Cronometer, Yazio et d'autres applis de calories. Rédigés par le développeur de Pofu, qui a un intérêt financier."),
 "es": dict(g="Guías", t="Herramientas", c="Calorías", q="Preguntas", v="Comparativas", m="Menú", l="Idiomas", x="Explorar",
   gh="Guías para contar calorías siendo mujer", gd="Guías prácticas y con fuentes sobre el seguimiento de calorías, el ciclo y la báscula: desde la precisión del registro con fotos hasta contar calorías sin culpa.",
   th="Calculadoras gratuitas para mujeres", td="Calculadoras gratuitas sobre el peso durante la regla y las necesidades calóricas a lo largo del ciclo. Sin registro.",
   vh="Pofu frente a otros contadores de calorías", vd="Comparativas honestas de Pofu con MyFitnessPal, Noom, Cronometer, Yazio y otras apps de calorías. Escritas por el desarrollador de Pofu, que tiene un interés económico."),
 "it": dict(g="Guide", t="Strumenti", c="Calorie", q="Domande", v="Confronti", m="Menu", l="Lingue", x="Esplora",
   gh="Guide al conteggio delle calorie per le donne", gd="Guide pratiche e con fonti su tracciamento delle calorie, ciclo e bilancia: dalla precisione del conteggio da foto al contare le calorie senza sensi di colpa.",
   th="Calcolatori gratuiti per le donne", td="Calcolatori gratuiti su peso in periodo mestruale e fabbisogno calorico nel ciclo. Senza registrazione.",
   vh="Pofu a confronto con altri contacalorie", vd="Confronti onesti tra Pofu e MyFitnessPal, Noom, Cronometer, Yazio e altre app per le calorie. Scritti dallo sviluppatore di Pofu, che ha un interesse economico."),
 "pt-BR": dict(g="Guias", t="Ferramentas", c="Calorias", q="Perguntas", v="Comparativos", m="Menu", l="Idiomas", x="Explorar",
   gh="Guias para contar calorias sendo mulher", gd="Guias práticos e com fontes sobre registro de calorias, ciclo menstrual e balança: da precisão do registro por foto a contar calorias sem culpa.",
   th="Calculadoras gratuitas para mulheres", td="Calculadoras gratuitas sobre o peso na menstruação e a necessidade de calorias ao longo do ciclo. Sem cadastro.",
   vh="Pofu comparado a outros contadores de calorias", vd="Comparativos honestos do Pofu com MyFitnessPal, Noom, Cronometer, Yazio e outros apps de calorias. Escritos pelo desenvolvedor do Pofu, que tem interesse financeiro."),
 "nl": dict(g="Gidsen", t="Tools", c="Calorieën", q="Vragen", v="Vergelijkingen", m="Menu", l="Talen", x="Ontdekken",
   gh="Gidsen over calorieën tellen voor vrouwen", gd="Praktische gidsen met bronnen over calorieën bijhouden, je cyclus en de weegschaal: van de nauwkeurigheid van fotoregistratie tot calorieën tellen zonder schuldgevoel.",
   th="Gratis rekentools voor vrouwen", td="Gratis rekentools over gewicht rond je menstruatie en je calorie-behoefte tijdens je cyclus. Zonder account.",
   vh="Pofu vergeleken met andere caloriemeters", vd="Eerlijke vergelijkingen van Pofu met MyFitnessPal, Noom, Cronometer, Yazio en andere calorie-apps. Geschreven door de ontwikkelaar van Pofu, die er financieel belang bij heeft."),
 "pl": dict(g="Poradniki", t="Narzędzia", c="Kalorie", q="Pytania", v="Porównania", m="Menu", l="Języki", x="Odkrywaj",
   gh="Poradniki o liczeniu kalorii dla kobiet", gd="Praktyczne poradniki ze źródłami o śledzeniu kalorii, cyklu i wadze: od dokładności liczenia ze zdjęć po liczenie kalorii bez poczucia winy.",
   th="Darmowe kalkulatory dla kobiet", td="Darmowe kalkulatory wagi w czasie miesiączki i zapotrzebowania na kalorie w cyklu. Bez rejestracji.",
   vh="Pofu na tle innych liczników kalorii", vd="Uczciwe porównania Pofu z MyFitnessPal, Noom, Cronometer, Yazio i innymi aplikacjami do kalorii. Napisane przez twórcę Pofu, który ma w tym interes finansowy."),
 "ru": dict(g="Руководства", t="Инструменты", c="Калории", q="Вопросы", v="Сравнения", m="Меню", l="Языки", x="Разделы",
   gh="Руководства по подсчёту калорий для женщин", gd="Практичные руководства с источниками о подсчёте калорий, менструальном цикле и весах: от точности учёта по фото до подсчёта калорий без чувства вины.",
   th="Бесплатные калькуляторы для женщин", td="Бесплатные калькуляторы: вес во время месячных и потребность в калориях на протяжении цикла. Без регистрации.",
   vh="Pofu и другие счётчики калорий: сравнения", vd="Честные сравнения Pofu с MyFitnessPal, Noom, Cronometer, Yazio и другими приложениями для калорий. Написаны разработчиком Pofu, у которого есть финансовый интерес."),
 "uk": dict(g="Посібники", t="Інструменти", c="Калорії", q="Питання", v="Порівняння", m="Меню", l="Мови", x="Розділи",
   gh="Посібники з підрахунку калорій для жінок", gd="Практичні посібники з джерелами про облік калорій, менструальний цикл і вагу: від точності обліку за фото до підрахунку калорій без почуття провини.",
   th="Безкоштовні калькулятори для жінок", td="Безкоштовні калькулятори: вага під час місячних і потреба в калоріях протягом циклу. Без реєстрації.",
   vh="Pofu та інші лічильники калорій: порівняння", vd="Чесні порівняння Pofu з MyFitnessPal, Noom, Cronometer, Yazio та іншими застосунками для калорій. Написані розробником Pofu, який має фінансовий інтерес."),
 "cs": dict(g="Průvodci", t="Nástroje", c="Kalorie", q="Otázky", v="Srovnání", m="Menu", l="Jazyky", x="Prozkoumat",
   gh="Průvodci počítáním kalorií pro ženy", gd="Praktické průvodci se zdroji o sledování kalorií, menstruačním cyklu a váze: od přesnosti sledování podle fotky po počítání kalorií bez pocitu viny.",
   th="Bezplatné kalkulačky pro ženy", td="Bezplatné kalkulačky váhy při menstruaci a potřeby kalorií během cyklu. Bez registrace.",
   vh="Pofu v porovnání s jinými počítadly kalorií", vd="Upřímná srovnání Pofu s MyFitnessPal, Noom, Cronometer, Yazio a dalšími aplikacemi na kalorie. Napsal je vývojář Pofu, který má finanční zájem."),
 "ro": dict(g="Ghiduri", t="Instrumente", c="Calorii", q="Întrebări", v="Comparații", m="Meniu", l="Limbi", x="Explorează",
   gh="Ghiduri despre numărarea caloriilor pentru femei", gd="Ghiduri practice, cu surse, despre urmărirea caloriilor, ciclul menstrual și cântar: de la acuratețea înregistrării prin fotografie la numărarea caloriilor fără vinovăție.",
   th="Calculatoare gratuite pentru femei", td="Calculatoare gratuite pentru greutatea din timpul menstruației și necesarul de calorii pe parcursul ciclului. Fără cont.",
   vh="Pofu comparat cu alte aplicații de calorii", vd="Comparații sincere între Pofu și MyFitnessPal, Noom, Cronometer, Yazio și alte aplicații de calorii. Scrise de dezvoltatorul Pofu, care are un interes financiar."),
 "sv": dict(g="Guider", t="Verktyg", c="Kalorier", q="Frågor", v="Jämförelser", m="Meny", l="Språk", x="Utforska",
   gh="Guider om kaloriräkning för kvinnor", gd="Praktiska guider med källor om kaloriloggning, menscykeln och vågen: från hur exakt fotologgning är till att räkna kalorier utan skuld.",
   th="Gratis kalkylatorer för kvinnor", td="Gratis kalkylatorer för vikt under mens och kaloribehov under cykeln. Utan konto.",
   vh="Pofu jämfört med andra kaloriräknare", vd="Ärliga jämförelser mellan Pofu och MyFitnessPal, Noom, Cronometer, Yazio och andra kalori-appar. Skrivna av Pofus utvecklare, som har ett ekonomiskt intresse."),
 "ja": dict(g="ガイド", t="ツール", c="カロリー", q="Q&A", v="比較", m="メニュー", l="言語", x="見る",
   gh="女性のためのカロリー計算ガイド", gd="カロリー記録、生理周期、体重計について、出典つきで実用的に解説するガイド集。写真記録の精度から、罪悪感のないカロリー計算まで。",
   th="女性向けの無料計算ツール", td="生理中の体重変化と、周期ごとの必要カロリーを調べられる無料ツール。登録不要です。",
   vh="Pofuと他のカロリー計算アプリの比較", vd="PofuをMyFitnessPal、Noom、Cronometer、Yazioなどのカロリーアプリと正直に比較。Pofuの開発者が執筆しており、金銭的な利害関係があります。"),
 "ko": dict(g="가이드", t="도구", c="칼로리", q="Q&A", v="비교", m="메뉴", l="언어", x="둘러보기",
   gh="여성을 위한 칼로리 계산 가이드", gd="칼로리 기록, 생리 주기, 체중계에 관한 출처 있는 실용 가이드. 사진 기록의 정확도부터 죄책감 없이 칼로리 세기까지.",
   th="여성을 위한 무료 계산기", td="생리 중 체중 변화와 주기에 따른 필요 칼로리를 알아보는 무료 계산기. 가입이 필요 없습니다.",
   vh="Pofu와 다른 칼로리 앱 비교", vd="Pofu를 MyFitnessPal, Noom, Cronometer, Yazio 등 다른 칼로리 앱과 솔직하게 비교했습니다. Pofu 개발자가 직접 썼으며 금전적 이해관계가 있습니다."),
 "zh-Hans": dict(g="指南", t="工具", c="热量", q="问答", v="对比", m="菜单", l="语言", x="探索",
   gh="女性热量计算指南", gd="关于热量记录、月经周期与体重秤的实用指南，附资料来源：从拍照记录的准确度，到不带愧疚地计算热量。",
   th="面向女性的免费计算器", td="免费计算器：了解经期体重变化，以及整个周期中的热量需求。无需注册。",
   vh="Pofu 与其他热量计算应用对比", vd="坦诚对比 Pofu 与 MyFitnessPal、Noom、Cronometer、Yazio 等热量应用。由 Pofu 的开发者撰写，存在经济利益关系。"),
 "id": dict(g="Panduan", t="Alat", c="Kalori", q="Tanya Jawab", v="Perbandingan", m="Menu", l="Bahasa", x="Jelajahi",
   gh="Panduan menghitung kalori untuk perempuan", gd="Panduan praktis dengan sumber tentang pencatatan kalori, siklus menstruasi, dan timbangan: dari akurasi pencatatan lewat foto sampai menghitung kalori tanpa rasa bersalah.",
   th="Kalkulator gratis untuk perempuan", td="Kalkulator gratis untuk berat badan saat menstruasi dan kebutuhan kalori sepanjang siklus. Tanpa daftar.",
   vh="Pofu dibandingkan dengan penghitung kalori lain", vd="Perbandingan jujur Pofu dengan MyFitnessPal, Noom, Cronometer, Yazio, dan aplikasi kalori lain. Ditulis oleh pengembang Pofu, yang memiliki kepentingan finansial."),
 "vi": dict(g="Hướng dẫn", t="Công cụ", c="Calo", q="Hỏi đáp", v="So sánh", m="Menu", l="Ngôn ngữ", x="Khám phá",
   gh="Hướng dẫn đếm calo dành cho phụ nữ", gd="Hướng dẫn thực tế, có nguồn, về theo dõi calo, chu kỳ kinh nguyệt và cân nặng: từ độ chính xác của ghi bằng ảnh đến đếm calo không áy náy.",
   th="Công cụ tính miễn phí cho phụ nữ", td="Công cụ tính miễn phí về cân nặng khi có kinh và nhu cầu calo theo chu kỳ. Không cần đăng ký.",
   vh="Pofu so với các ứng dụng đếm calo khác", vd="So sánh thẳng thắn Pofu với MyFitnessPal, Noom, Cronometer, Yazio và các ứng dụng calo khác. Do nhà phát triển Pofu viết, người có lợi ích tài chính."),
 "th": dict(g="คู่มือ", t="เครื่องมือ", c="แคลอรี่", q="ถาม-ตอบ", v="เปรียบเทียบ", m="เมนู", l="ภาษา", x="สำรวจ",
   gh="คู่มือนับแคลอรี่สำหรับผู้หญิง", gd="คู่มือใช้งานจริงพร้อมแหล่งอ้างอิงเรื่องการบันทึกแคลอรี่ รอบเดือน และเครื่องชั่ง ตั้งแต่ความแม่นยำของการบันทึกด้วยรูปถ่าย ไปจนถึงการนับแคลอรี่โดยไม่รู้สึกผิด",
   th="เครื่องคิดเลขฟรีสำหรับผู้หญิง", td="เครื่องคิดเลขฟรีเรื่องน้ำหนักช่วงมีประจำเดือนและความต้องการแคลอรี่ตลอดรอบเดือน ไม่ต้องสมัครสมาชิก",
   vh="เปรียบเทียบ Pofu กับแอปนับแคลอรี่อื่น", vd="เปรียบเทียบ Pofu กับ MyFitnessPal, Noom, Cronometer, Yazio และแอปแคลอรี่อื่นอย่างตรงไปตรงมา เขียนโดยผู้พัฒนา Pofu ซึ่งมีผลประโยชน์ทางการเงินเกี่ยวข้อง"),
 "hi": dict(g="गाइड", t="टूल", c="कैलोरी", q="सवाल-जवाब", v="तुलना", m="मेनू", l="भाषाएँ", x="देखें",
   gh="महिलाओं के लिए कैलोरी गिनने की गाइड", gd="कैलोरी ट्रैकिंग, मासिक चक्र और वज़न मशीन पर स्रोतों सहित व्यावहारिक गाइड: फ़ोटो से लॉगिंग कितनी सटीक है से लेकर बिना अपराधबोध के कैलोरी गिनने तक।",
   th="महिलाओं के लिए मुफ़्त कैलकुलेटर", td="पीरियड्स के दौरान वज़न और चक्र भर में कैलोरी की ज़रूरत के लिए मुफ़्त कैलकुलेटर। साइन-अप की ज़रूरत नहीं।",
   vh="Pofu की दूसरे कैलोरी ऐप्स से तुलना", vd="Pofu की MyFitnessPal, Noom, Cronometer, Yazio और दूसरे कैलोरी ऐप्स से ईमानदार तुलना। इसे Pofu के डेवलपर ने लिखा है, जिनका इसमें आर्थिक हित है।"),
 "ar": dict(g="الأدلة", t="الأدوات", c="السعرات", q="أسئلة", v="مقارنات", m="القائمة", l="اللغات", x="استكشف",
   gh="أدلة حساب السعرات الحرارية للنساء", gd="أدلة عملية مدعومة بمصادر عن تتبع السعرات والدورة الشهرية والميزان: من دقة التسجيل بالصور إلى حساب السعرات دون شعور بالذنب.",
   th="حاسبات مجانية للنساء", td="حاسبات مجانية لوزن فترة الدورة واحتياج السعرات الحرارية خلال الدورة. بدون تسجيل.",
   vh="مقارنة Pofu مع تطبيقات السعرات الأخرى", vd="مقارنات صريحة بين Pofu وMyFitnessPal وNoom وCronometer وYazio وتطبيقات سعرات أخرى. كتبها مطوّر Pofu الذي له مصلحة مالية."),
}


# ----------------------------------------------------------------------------- helpers
def rd(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def wr(p, s):
    """Write only when changed. Returns True if the file changed."""
    p = Path(p)
    if p.exists() and rd(p) == s:
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)
    return True


def rel(p):
    return Path(p).resolve().relative_to(ROOT).as_posix()


def pages():
    out = []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in fns:
            if fn.endswith(".html"):
                out.append(Path(dp) / fn)
    return sorted(out)


def html_lang(text):
    m = re.search(r"<html[^>]*\blang=\"([^\"]+)\"", text[:600])
    return m.group(1) if m else None


def page_lang(r, text):
    first = r.split("/")[0]
    if "/" in r:
        if first in OTHER:
            return first
        if first in ("tr", "kalori", "sorular"):
            return "tr"
        return "en"
    return "tr" if html_lang(text) == "tr" else "en"


_FD = {}


def food_dir(L):
    if L == "en":
        return "calories"
    if L == "tr":
        return "kalori"
    if L not in _FD:
        _FD[L] = None
        for d in sorted((ROOT / L).iterdir()):
            if d.is_dir() and d.name != "questions" and (d / "index.html").exists():
                _FD[L] = f"{L}/{d.name}"
                break
    return _FD[L]


def qa_dir(L):
    return {"en": "questions", "tr": "sorular"}.get(L, f"{L}/questions")


def prod(L):
    return {"en": "", "tr": "tr/"}.get(L, f"{L}/pofu.html")  # en/tr home is the landing page (pofu.html merged Nov 13)


def href_to(target, frm):
    """Relative URL from page `frm` (posix, relative to ROOT) to `target`; trailing slash kept."""
    d = os.path.dirname(frm) or "."
    r = os.path.relpath(target.rstrip("/"), d).replace(os.sep, "/")
    if target.endswith("/"):
        r = (r + "/") if r != "." else "./"
    return r


def exists(target):
    t = target.rstrip("/")
    return (ROOT / t / "index.html").exists() if target.endswith("/") else (ROOT / t).exists()


def classify(L, r):
    """Section of a page of language L: guides/tools/compare/food/qa or None."""
    for k, v in HUBFILE[L].items():
        if v == r:
            return k
    fd, qd = food_dir(L), qa_dir(L)
    if fd and r.startswith(fd + "/"):
        return "food"
    if r.startswith(qd + "/"):
        return "qa"
    base = os.path.basename(r)
    if base in NON_CONTENT or base.startswith("google"):
        return None
    if base.startswith("pofu-vs-"):
        return "compare"
    if base in TOOL_NAMES or base.endswith(("calculator.html", "hesaplama.html")):
        return "tools"
    return "guides"


def hub_targets(L):
    lab = LABELS[L]
    fd = food_dir(L)
    return [("guides", lab["g"], HUBFILE[L]["guides"]), ("tools", lab["t"], HUBFILE[L]["tools"]),
            ("food", lab["c"], fd + "/" if fd else ""), ("qa", lab["q"], qa_dir(L) + "/"),
            ("compare", lab["v"], HUBFILE[L]["compare"])]


def nav_links(L, r):
    """[(key, label, href, aria-current)] for the hubs that exist."""
    here = classify(L, r)
    out = []
    for key, label, tgt in hub_targets(L):
        if not tgt or not exists(tgt):
            continue
        state = ""
        if r == tgt or (tgt.endswith("/") and r == tgt + "index.html"):
            state = "page"
        elif here == key:
            state = "true"
        out.append((key, label, href_to(tgt, r), state))
    return out


def a_tags(links):
    return "".join(f'<a href="{h}"' + (f' aria-current="{s}"' if s else "") + f">{htmllib.escape(l, quote=False)}</a>"
                   for _, l, h, s in links)


# ----------------------------------------------------------------------------- nav css/blocks
NAV_CSS = """/* nav:css:start */
.top{position:relative}
.top__in{flex-wrap:wrap;gap:.5rem .75rem}
.top__in .btn{margin-inline-start:auto}
.pnav{display:contents}
.pnav__links{display:none}
.pnav__m summary{list-style:none;display:inline-flex;align-items:center;justify-content:center;gap:.45rem;min-width:44px;min-height:44px;padding:0 .8rem;border:1px solid var(--line,rgba(0,0,0,.18));border-radius:999px;background:var(--card,#fff);color:var(--ink,#222);font-weight:600;font-size:.95rem;line-height:1;cursor:pointer}
.pnav__m summary::-webkit-details-marker{display:none}
.pnav__m[open] summary{background:var(--soft,rgba(222,81,135,.12))}
.pnav__m svg{width:20px;height:20px;flex:none}
.pnav__m summary span{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.pnav__panel{position:absolute;inset-inline:0;top:100%;z-index:30;display:flex;flex-direction:column;padding:.4rem max(1rem,env(safe-area-inset-left)) 1rem;background:var(--bg,#fff);border-bottom:1px solid var(--line,rgba(0,0,0,.18));box-shadow:0 14px 26px rgba(0,0,0,.14)}
.pnav__panel a,.pnav__links a{display:flex;align-items:center;min-height:44px;color:var(--ink,#222);font-weight:600;text-decoration:none}
.pnav__panel a{padding:.4rem .2rem;border-bottom:1px solid var(--line,rgba(0,0,0,.14))}
.pnav a[aria-current]{color:var(--pink-text,#A32F5E)}
.pnav__panel a[aria-current]{box-shadow:inset 3px 0 0 var(--pink,#DE5187);padding-inline-start:.7rem}
.pnav a:hover{text-decoration:underline}
@media (max-width:24rem){.top__in{gap:.5rem}.top__in .btn{padding:.5rem .7rem;font-size:.85rem}.brand{font-size:1.1rem}}
@media (min-width:30rem){.pnav__m summary span{position:static;width:auto;height:auto;clip:auto}}
@media (min-width:44rem){
.pnav__m{display:none}
.pnav__links{display:flex;flex-wrap:wrap;gap:.35rem .5rem;flex-basis:100%;order:3;padding-bottom:.1rem}
.pnav__links a{min-height:2.5rem;padding:0 .95rem;border:1px solid var(--line,rgba(0,0,0,.14));border-radius:999px;background:var(--card,#fff);font-size:.95rem}
.pnav__links a[aria-current]{background:var(--soft,rgba(222,81,135,.12));border-color:transparent}
}
.pfoot{margin-top:1.1rem;padding-top:1rem;border-top:1px solid var(--line,rgba(0,0,0,.14))}
.pfoot nav{display:flex;flex-wrap:wrap;align-items:center;gap:0 1rem;margin:0 0 .5rem}
.pfoot strong{color:var(--ink,#222)}
.pfoot a{display:inline-flex;align-items:center;min-height:2.5rem}
.pfoot [aria-current]{font-weight:700}
.plang{order:2}
.plang summary{list-style:none;display:inline-flex;align-items:center;gap:.3rem;min-width:44px;min-height:44px;padding:0 .7rem;border:1px solid var(--line,rgba(0,0,0,.18));border-radius:999px;background:var(--card,#fff);color:var(--ink,#222);font-weight:600;font-size:.9rem;line-height:1;cursor:pointer}
.plang summary::-webkit-details-marker{display:none}
.plang[open] summary{background:var(--soft,rgba(222,81,135,.12))}
.plang__panel{position:absolute;inset-inline:0;top:100%;z-index:31;display:grid;grid-template-columns:repeat(auto-fill,minmax(9.5rem,1fr));gap:0 .75rem;padding:.4rem max(1rem,env(safe-area-inset-left)) 1rem;background:var(--bg,#fff);border-bottom:1px solid var(--line,rgba(0,0,0,.18));box-shadow:0 14px 26px rgba(0,0,0,.14)}
.plang__panel a{display:flex;align-items:center;min-height:44px;padding:0 .2rem;color:var(--ink,#222);text-decoration:none;border-bottom:1px solid var(--line,rgba(0,0,0,.1))}
.plang__panel a[aria-current]{color:var(--pink-text,#A32F5E);font-weight:700}
.plang__panel a:hover{text-decoration:underline}
/* nav:css:end */"""

MENU_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 7h16M4 12h16M4 17h16" '
             'fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>')


def lang_menu(L, r, text):
    """Header language switcher: every translation of this page (from its hreflang links), current one marked."""
    have = dict(alt_links(text, r))
    have[L] = href_to(r, r)
    for c in ALL:  # no translation of this page: send that language to its home page
        home = "index.html" if c == "en" else "tr/index.html" if c == "tr" else f"{c}/pofu.html"
        if c not in have and exists(home):
            have[c] = href_to(home, r)
    l = htmllib.escape(LABELS[L]["l"], quote=False)
    items = sorted(have.items(), key=lambda a: ALL.index(a[0]) if a[0] in ALL else 99)
    links = "".join(f'<a href="{h}" hreflang="{c}" lang="{c}"' + (' aria-current="page"' if c == L else "")
                    + f">{NAMES.get(c, c)}</a>" for c, h in items)
    return (f'<details class="plang"><summary aria-label="{l}">\U0001F310 {L.split("-")[0].upper()}</summary>'
            f'<nav class="plang__panel" aria-label="{l}">{links}</nav></details>\n')


def header_block(L, r, text=""):
    links = a_tags(nav_links(L, r))
    m = htmllib.escape(LABELS[L]["m"], quote=False)
    return ("<!-- nav:start -->\n"
            f'<div class="pnav">\n<nav class="pnav__links" aria-label="{m}">{links}</nav>\n'
            f'<details class="pnav__m"><summary>{MENU_ICON}<span>{m}</span></summary>'
            f'<nav class="pnav__panel" aria-label="{m}">{links}</nav></details>\n'
            + lang_menu(L, r, text) + "</div>\n<!-- nav:end -->")


def alt_links(text, r):
    """[(hreflang, relative href)] for existing alternates (other pages) from <link rel=alternate hreflang>."""
    out = []
    base = SITE + r
    for tag in re.findall(r"<link\b[^>]*>", text):
        if 'rel="alternate"' not in tag:
            continue
        hl = re.search(r'hreflang="([^"]+)"', tag)
        hf = re.search(r'href="([^"]+)"', tag)
        if not hl or not hf or hl.group(1) == "x-default":
            continue
        u = urlparse(urljoin(base, hf.group(1)))
        if u.netloc and u.netloc != "getpofu.com":
            continue
        tgt = u.path.lstrip("/") or "./"
        if tgt == r or not exists(tgt if tgt != "./" else "index.html"):
            continue
        out.append((hl.group(1), href_to(tgt, r)))
    return out


def policy_link(L, r):
    """Footer link to the 'content and sources' page (label from data/trust/<L>.json)."""
    tgt = "editorial-policy.html" if L == "en" else "icerik-ve-kaynak-politikasi.html" if L == "tr" else f"{L}/editorial-policy.html"
    tf = ROOT / "data" / "trust" / f"{L}.json"
    if not exists(tgt) or not tf.exists():
        return ""
    label = json.loads(rd(tf)).get("method", {}).get("nav")
    if not label:
        return ""
    cur = ' aria-current="page"' if r == tgt else ""
    return f'<a href="{href_to(tgt, r)}"{cur}>{htmllib.escape(label, quote=False)}</a>'


def footer_block(L, r, text):
    lab = LABELS[L]
    x = htmllib.escape(lab["x"], quote=False)
    out = ['<!-- footnav:start -->', '<div class="wrap pfoot">',
           f'<nav aria-label="{x}"><strong>{x}</strong>{a_tags(nav_links(L, r))}{policy_link(L, r)}</nav>']
    stripped = re.sub(r"<!-- footnav:start -->.*?<!-- footnav:end -->", "", text, flags=re.S)
    if 'class="langs"' not in stripped:  # page already has its own language switcher
        alts = alt_links(text, r)
        if alts:
            l = htmllib.escape(lab["l"], quote=False)
            items = "".join(f'<a href="{h}" hreflang="{c}" lang="{c}">{NAMES.get(c, c)}</a>' for c, h in alts)
            out.append(f'<nav aria-label="{l}"><strong>{l}</strong>{items}</nav>')
    out += ['</div>', '<!-- footnav:end -->']
    return "\n".join(out)


# ----------------------------------------------------------------------------- calculators box
NEW_TOOLS = ["deficit", "protein", "macro", "bmi"]
TOOL_FILE = {"protein": ("protein-calculator-for-women.html", "kadinlar-icin-protein-ihtiyaci-hesaplama.html"),
             "macro": ("macro-calculator-for-women.html", "kadinlar-icin-makro-hesaplama.html"),
             "deficit": ("calorie-deficit-calculator.html", "kalori-acigi-hesaplama.html"),
             "bmi": ("bmi-calculator-for-women.html", "kadinlar-icin-vucut-kitle-endeksi-hesaplama.html"),
             "cycle": ("cycle-calorie-calculator.html", "kadin-gunluk-kalori-ihtiyaci-hesaplama.html")}
RELEVANCE = [("protein", ("protein",)), ("macro", ("macro", "carb", "fat-", "keto")),
             ("bmi", ("bmi", "ideal-weight", "healthy-weight", "overweight")),
             ("cycle", ("cycle", "period", "luteal", "pms", "menstrual", "regl", "ovulation", "pcos", "menopause")),
             ("deficit", ("deficit", "lose", "weight-loss", "kilo", "plateau"))]
_TOOLS_TEXT = {}


def tools_text(L):
    if L not in _TOOLS_TEXT:
        f = ROOT / "data" / "tools" / f"{L}.json"
        _TOOLS_TEXT[L] = json.loads(rd(f)) if f.exists() else None
    return _TOOLS_TEXT[L]


def toolbox_block(L, r):
    """'More free tools' box for guides, Q&A and comparison pages (most relevant calculator first)."""
    d = tools_text(L)
    if not d or classify(L, r) not in ("guides", "qa", "compare") or os.path.basename(r) in NON_CONTENT:
        return ""
    base = os.path.basename(r).lower()
    order = [k for k, words in RELEVANCE if any(w in base for w in words)]
    order += [k for k in NEW_TOOLS + ["cycle"] if k not in order]
    items = []
    for k in order:
        en, tr = TOOL_FILE[k]
        tgt = tr if L == "tr" else en if L == "en" else f"{L}/{en}"
        if not exists(tgt):
            continue
        if k == "cycle":
            label = re.sub(r"<[^>]+>", "", re.search(r"<h1[^>]*>(.*?)</h1>", rd(ROOT / tgt), re.S).group(1)).strip()
        else:
            label = d["tools"][k]["h1"]
        items.append(f'<li><a href="{href_to(tgt, r)}">{htmllib.escape(label, quote=False)}</a></li>')
    if not items:
        return ""
    h = htmllib.escape(d["common"]["rel_h"], quote=False)
    return ("<!-- toolbox:start -->\n<section id=\"free-tools\" class=\"toolbox\">\n"
            f"<h2>{h}</h2>\n<ul>\n" + "\n".join(items) + "\n</ul>\n</section>\n<!-- toolbox:end -->")


# ----------------------------------------------------------------------------- "On this page" menu
def toc_block(L, r, text):
    """(new text, block) — table of contents for guides, Q&A and comparisons with 3+ sections.
    Adds stable ids (sec-N) to h2s whose section has no id. Skips hubs and pages with their own .toc."""
    if classify(L, r) not in ("guides", "qa", "compare") or os.path.basename(r) in NON_CONTENT or 'class="toc"' in text:
        return text, ""
    tf = ROOT / "data" / "trust" / f"{L}.json"
    if not tf.exists():
        return text, ""
    label = json.loads(rd(tf)).get("ui", {}).get("toc")
    m = re.search(r'(<main\b[^>]*>)(.*?)(</main>)', text, re.S)
    if not label or not m:
        return text, ""
    body = m.group(2)
    skip = {"free-tools", "related", "not-medical", "source", "sources"}
    items, n = [], 0

    def sec(mm):
        nonlocal n
        attrs, inner = mm.group(1), mm.group(2)
        sid = re.search(r'\bid="([^"]+)"', attrs)
        if 'class="hero"' in attrs or (sid and sid.group(1) in skip):
            return mm.group(0)
        h = re.search(r"<h2\b([^>]*)>(.*?)</h2>", inner, re.S)
        if not h:
            return mm.group(0)
        n += 1
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h.group(2))).strip()
        if sid:
            target = sid.group(1)
        else:
            hid = re.search(r'\bid="([^"]+)"', h.group(1))
            target = hid.group(1) if hid else f"sec-{n}"
            if not hid:
                inner = inner.replace(h.group(0), f'<h2 id="{target}"{h.group(1)}>{h.group(2)}</h2>', 1)
        items.append((target, title))
        return f"<section{attrs}>{inner}</section>"

    new_body = re.sub(r"<section\b([^>]*)>(.*?)</section>", sec, body, flags=re.S)
    if len(items) < 3:
        return text, ""
    lab = htmllib.escape(label, quote=False)
    lis = "".join(f'<li><a href="#{t}">{htmllib.escape(x, quote=False)}</a></li>' for t, x in items)
    block = (f'<!-- ptoc:start -->\n<nav class="ptoc" aria-label="{lab}">'
             f'<details class="ptoc__m"><summary>{lab}</summary><ol>{lis}</ol></details>'
             f'<div class="ptoc__d"><b>{lab}</b><ol>{lis}</ol></div></nav>\n<!-- ptoc:end -->')
    return text[:m.start(2)] + new_body + text[m.end(2):], block


# ----------------------------------------------------------------------------- app promo (every content page)
# Strings: data/promo/<lang>.json. Four slots, each between its own markers so re-runs replace them:
#   promo:strip (under the header), promo:card (after the hero), promo:panel (middle of <main>),
#   promo:bar (sticky bar before </body>, dismissed for 7 days via localStorage).
# Design reference: https://claude.ai/artifact/Xm9uGCA41AdDMHeD2PvtsV
_PROMO = {}
CYCLE_WORDS = ("period", "cycle", "menstru", "luteal", "regl", "pms", "ovulat", "adet", "dongu")
PROMO_RE = re.compile(r"\n?<!-- promo:(strip|card|panel|bar):start -->.*?<!-- promo:\1:end -->", re.S)


def promo_text(L):
    if L not in _PROMO:
        f = ROOT / "data" / "promo" / f"{L}.json"
        _PROMO[L] = json.loads(rd(f)) if f.exists() else json.loads(rd(ROOT / "data" / "promo" / "en.json"))
    return _PROMO[L]


def store_url(slot, L):
    return f"https://apps.apple.com/app/apple-store/id6778044605?pt=128375664&amp;ct=promo_{slot}_{L}&amp;mt=8"


def promo_blocks(L, r):
    """{slot: html} for a content page, or {} when the page gets no promo."""
    kind = classify(L, r)
    if kind is None or os.path.basename(r) in NON_CONTENT:
        return {}
    t = {k: htmllib.escape(v, quote=True) for k, v in promo_text(L).items()}
    base = os.path.basename(r).lower()
    card = "food" if kind == "food" else "tool" if kind == "tools" else \
        "cycle" if any(w in base for w in CYCLE_WORDS) else "food"
    shot = "demo-cycle.jpg" if card == "cycle" else "demo-scan.jpg"
    icon = href_to("assets/img/icon-96.webp", r)
    img = href_to(f"assets/video/{shot}", r)
    badge = href_to("assets/img/app-store-badge.png", r)
    lang = f' · {t["app_lang"]}' if t.get("app_lang") else ""
    note = t["not_tracker"] if card == "cycle" else t["note"]
    strip = ('<!-- promo:strip:start -->\n<aside class="pp-strip" aria-label="Pofu">'
             f'<div class="pp-strip__in"><img src="{icon}" alt="" width="30" height="30">'
             f'<p><b>Pofu</b> · {t["strip"]}</p><a href="{store_url("strip", L)}">{t["strip_cta"]} →</a></div></aside>\n'
             '<!-- promo:strip:end -->')
    cardb = ('<!-- promo:card:start -->\n<aside class="pp-card" aria-label="Pofu">'
             f'<div class="pp-card__shot"><img src="{img}" alt="{t["shot_alt"]}" loading="lazy" width="92" height="200"></div>'
             f'<div class="pp-card__body"><p class="pp-card__h">{t[card + "_h"]}</p><p>{t[card + "_p"]}</p>'
             f'<a class="pp-btn pp-btn--dark" href="{store_url("card", L)}">{t[card + "_cta"]}</a>'
             f'<p class="pp-small">{note}{lang}</p></div></aside>\n<!-- promo:card:end -->')
    panel = ('<!-- promo:panel:start -->\n<aside class="pp-panel" aria-label="Pofu">'
             f'<div class="pp-panel__text"><div class="pp-id"><img src="{icon}" alt="" width="48" height="48">'
             f'<div><b>Pofu</b><span>{t["tagline"]}</span></div></div>'
             f'<p class="pp-panel__h">{t["panel_h"]}</p>'
             f'<ul><li>{t["panel_1"]}</li><li>{t["panel_2"]}</li><li>{t["panel_3"]}</li></ul>'
             f'<div class="pp-panel__cta"><a href="{store_url("panel", L)}"><img src="{badge}" alt="{t["badge_alt"]}" width="150" height="50" loading="lazy"></a>'
             f'<span>{t["panel_note"]}{lang}</span></div></div>'
             f'<div class="pp-panel__phone"><img src="{img}" alt="{t["shot_alt"]}" loading="lazy" width="230" height="500"></div>'
             '</aside>\n<!-- promo:panel:end -->')
    bar = ('<!-- promo:bar:start -->\n<aside class="pp-bar" id="pp-bar" hidden aria-label="Pofu">'
           f'<img src="{icon}" alt="" width="44" height="44"><p><b>Pofu</b><span>{t["bar_sub"]}</span></p>'
           f'<a class="pp-btn" href="{store_url("bar", L)}">{t["bar_cta"]}</a>'
           f'<button type="button" class="pp-bar__x" aria-label="{t["close"]}">×</button></aside>\n'
           "<script>(function(){var b=document.getElementById('pp-bar'),k='pofu-bar-closed',n=Date.now();"
           "try{if(+localStorage.getItem(k)>n)return}catch(e){}"
           "function s(){if(scrollY>300){b.hidden=false;removeEventListener('scroll',s)}}addEventListener('scroll',s,{passive:true});s();"
           "b.querySelector('button').onclick=function(){b.hidden=true;try{localStorage.setItem(k,n+6048e5)}catch(e){}}})();</script>\n"
           "<!-- promo:bar:end -->")
    return {"strip": strip, "card": cardb, "panel": panel, "bar": bar}


SKIP_MID = ("hero", "related", "faq", "source", "sources", "free-tools")


def apply_promo(L, r, text):
    text = PROMO_RE.sub("", text)
    b = promo_blocks(L, r)
    if not b or "</main>" not in text:
        return text
    hi = text.find("</header>")
    if hi != -1:
        hi += len("</header>")
        text = text[:hi] + "\n" + b["strip"] + text[hi:]
    hero = re.search(r'<section class="hero">.*?</section>', text, re.S)
    if hero:
        text = text[:hero.end()] + "\n" + b["card"] + text[hero.end():]
    m = re.search(r"<main\b[^>]*>(.*)</main>", text, re.S)
    secs = [s for s in re.finditer(r"<section\b([^>]*)>", text[m.start(1):m.end(1)])
            if not re.search(r'(class="hero"|id="(%s)")' % "|".join(SKIP_MID), s.group(1))] if m else []
    if len(secs) >= 2:
        at = m.start(1) + secs[len(secs) // 2].start()
        text = text[:at] + b["panel"] + "\n" + text[at:]
    elif "</main>" in text:
        i = text.rindex("</main>")
        text = text[:i] + b["panel"] + "\n" + text[i:]
    i = text.rindex("</body>")
    return text[:i] + b["bar"] + "\n" + text[i:]


STD_HEADER = re.compile(r'(<header class="top">\s*<div class="wrap top__in">.*?)(\s*</div>\s*</header>)', re.S)


def process(path, text=None, write=True):
    """Inject nav pieces. Returns (kind, changed|new text) with kind standard/legal/skipped."""
    r = rel(path)
    text = rd(path) if text is None else text
    if path.name.startswith("google") or "<html" not in text[:400].lower() or r in LANDING:
        return "skipped", False
    L = page_lang(r, text)
    new = text
    standard = bool(STD_HEADER.search(new)) or "<!-- nav:start -->" in new
    css = f"<style>{NAV_CSS}</style>"
    if "/* nav:css:start */" in new:
        new = re.sub(r"<style>/\* nav:css:start \*/.*?/\* nav:css:end \*/</style>", lambda m: css, new, flags=re.S)
    else:
        new = new.replace("</head>", css + "\n</head>", 1)
    # site skin (assets/site.css + fonts) after the page's own styles, standard pages only
    new = re.sub(r"\n?<!-- skin:start -->.*?<!-- skin:end -->", "", new, flags=re.S)
    if standard:
        skin = ("<!-- skin:start -->\n"
                '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
                '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
                '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&amp;family=Figtree:wght@400;600;700&amp;display=swap">\n'
                f'<link rel="stylesheet" href="{href_to("assets/site.css", r)}?v={SKIN_V}">\n'
                "<!-- skin:end -->")
        new = new.replace("</head>", skin + "\n</head>", 1)
    else:  # legal pages keep styles.css; only the fonts change
        skin = ("<!-- skin:start -->\n"
                '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&amp;family=Figtree:wght@400;600;700&amp;display=swap">\n'
                f'<link rel="stylesheet" href="{href_to("assets/site-legal.css", r)}?v={SKIN_V}">\n'
                "<!-- skin:end -->")
        new = new.replace("</head>", skin + "\n</head>", 1)
    if standard:
        hb = header_block(L, r, new)
        if "<!-- nav:start -->" in new:
            new = re.sub(r"<!-- nav:start -->.*?<!-- nav:end -->", lambda m: hb, new, flags=re.S)
        else:
            new = STD_HEADER.sub(lambda m: m.group(1) + "\n" + hb + m.group(2), new, count=1)
    new = re.sub(r"\n?<!-- ptoc:start -->.*?<!-- ptoc:end -->", "", new, flags=re.S)
    if standard:
        new, pt = toc_block(L, r, new)
        if pt:
            hero = re.search(r'<section class="hero">.*?</section>', new, re.S)
            if hero:
                new = new[:hero.end()] + "\n" + pt + new[hero.end():]
    tb = toolbox_block(L, r)
    new = re.sub(r"\n?<!-- toolbox:start -->.*?<!-- toolbox:end -->", "", new, flags=re.S)
    if tb and "</main>" in new:
        i = new.rindex("</main>")
        new = new[:i] + tb + "\n" + new[i:]
    fb = footer_block(L, r, new)
    if "<!-- footnav:start -->" in new:
        new = re.sub(r"<!-- footnav:start -->.*?<!-- footnav:end -->", lambda m: fb, new, flags=re.S)
    elif standard and "</footer>" in new:
        i = new.rindex("</footer>")
        new = new[:i] + fb + "\n" + new[i:]
    else:  # legal pages with their own footer element
        new = new.replace("</body>", fb + "\n</body>", 1)
    if standard:
        new = apply_promo(L, r, new)
    return ("standard" if standard else "legal"), (wr(path, new) if write else new)


# ----------------------------------------------------------------------------- hubs
def info(path):
    t = rd(path)
    h = re.search(r"<h1[^>]*>(.*?)</h1>", t, re.S)
    d = re.search(r'<meta name="description" content="([^"]*)"', t)
    title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h.group(1))).strip() if h else path.stem
    return title, d.group(1) if d else ""


def hub_pages(L, kind):
    """[(path rel ROOT, title, description, page language)] for the hub kind."""
    if L == "en":
        cands = [p for p in ROOT.glob("*.html") if html_lang(rd(p)) == "en"]
    elif L == "tr":
        cands = [p for p in ROOT.glob("*.html") if html_lang(rd(p)) == "tr"] + list((ROOT / "tr").glob("*.html"))
    else:
        cands = list((ROOT / L).glob("*.html"))
    found = [(p, L) for p in cands if rel(p) not in LANDING and classify(L, rel(p)) == kind and rel(p) not in HUBFILE[L].values()]
    if kind == "compare" and not found:  # no translation yet: link the English comparisons
        found = [(p, "en") for p in ROOT.glob("pofu-vs-*.html")]
    order = GUIDE_ORDER if kind == "guides" else TOOL_ORDER if kind == "tools" else []
    found.sort(key=lambda x: (order.index(x[0].name) if x[0].name in order else len(order), x[0].name))
    return [(rel(p), *info(p), pl) for p, pl in found]


def jld(obj):
    return '<script type="application/ld+json">\n' + json.dumps(obj, ensure_ascii=False) + "\n</script>"


def build_hub(L, kind):
    tpl_p = ROOT / TEMPLATE.get(L, f"{L}/{TEMPLATE['en']}")
    if not tpl_p.exists():
        return None
    lab = LABELS[L]
    hub_rel = HUBFILE[L][kind]
    name = {"guides": lab["g"], "tools": lab["t"], "compare": lab["v"]}[kind]
    h1 = lab[{"guides": "gh", "tools": "th", "compare": "vh"}[kind]]
    desc = lab[{"guides": "gd", "tools": "td", "compare": "vd"}[kind]]
    e = lambda s: htmllib.escape(s, quote=True)  # noqa: E731
    url = SITE + hub_rel
    items = hub_pages(L, kind)
    t = rd(tpl_p)
    t = re.sub(r"<title>.*?</title>", lambda m: f"<title>{e(h1)} | Pofu</title>", t, count=1, flags=re.S)
    t = re.sub(r'<meta name="description" content="[^"]*">', lambda m: f'<meta name="description" content="{e(desc)}">', t, count=1)
    t = re.sub(r'<link rel="canonical" href="[^"]*">', lambda m: f'<link rel="canonical" href="{url}">', t, count=1)
    t = re.sub(r'\s*<link rel="alternate" hreflang="[^"]*" href="[^"]*">', "", t)
    hl = "".join(f'\n<link rel="alternate" hreflang="{c}" href="{SITE}{HUBFILE[c][kind]}">' for c in ALL)
    hl += f'\n<link rel="alternate" hreflang="x-default" href="{SITE}{HUBFILE["en"][kind]}">'
    t = re.sub(r'(<link rel="canonical" href="[^"]*">)', lambda m: m.group(1) + hl, t, count=1)
    t = t.replace('<meta property="og:type" content="article">', '<meta property="og:type" content="website">')
    t = re.sub(r'<meta property="og:title" content="[^"]*">', lambda m: f'<meta property="og:title" content="{e(h1)}">', t, count=1)
    t = re.sub(r'<meta property="og:description" content="[^"]*">', lambda m: f'<meta property="og:description" content="{e(desc)}">', t, count=1)
    t = re.sub(r'<meta property="og:url" content="[^"]*">', lambda m: f'<meta property="og:url" content="{url}">', t, count=1)
    t = re.sub(r'\s*<meta property="article:[^>]*>', "", t)
    t = re.sub(r'\s*<script type="application/ld\+json">.*?</script>', "", t, flags=re.S)
    ld = jld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Pofu", "item": SITE + prod(L)},
        {"@type": "ListItem", "position": 2, "name": name, "item": url}]})
    ld += "\n" + jld({"@context": "https://schema.org", "@type": "CollectionPage", "name": h1, "description": desc,
                      "url": url, "inLanguage": html_lang(t) or L,
                      "isPartOf": {"@type": "WebSite", "name": "Pofu", "url": SITE},
                      "mainEntity": {"@type": "ItemList", "numberOfItems": len(items), "itemListElement": [
                          {"@type": "ListItem", "position": i + 1, "name": htmllib.unescape(ti), "url": SITE + pr}
                          for i, (pr, ti, _, _) in enumerate(items)]}})
    t = t.replace("</head>", ld + "\n</head>", 1)
    lis = []
    for pr, ti, de, pl in items:
        extra = f' hreflang="{pl}" lang="{pl}"' if pl != L else ""
        lis.append(f'<li><a href="{href_to(pr, hub_rel)}"{extra}><strong>{ti}</strong></a>'
                   + (f'<br><span class="fine">{de}</span>' if de else "") + "</li>")
    note = ""
    if kind == "compare" and items and items[0][3] != L and lab.get("vn"):
        note = f'<p class="fine">{e(lab["vn"])}</p>\n'
    pills = []
    for k, lb, tgt in hub_targets(L):
        if k == kind or not tgt or not exists(tgt):
            continue
        pills.append(f'<li><a href="{href_to(tgt, hub_rel)}">{e(lb)}</a></li>')
    main = (f'<!-- hub:generated ({kind}) -->\n<main id="main" class="wrap">\n<section class="hero">\n'
            f'<p class="pill">{e(name)}</p>\n<h1>{e(h1)}</h1>\n<p class="lede">{e(desc)}</p>\n</section>\n'
            f'<section>\n{note}<ul>\n' + "\n".join(lis) + '\n</ul>\n</section>\n'
            f'<section>\n<nav class="toc" aria-label="{e(lab["x"])}"><h2>{e(lab["x"])}</h2><ul>' + "".join(pills)
            + '</ul></nav>\n</section>\n</main>')
    t = re.sub(r"<main\b.*?</main>", lambda m: main, t, count=1, flags=re.S)
    # per-page App Store campaign token
    t = re.sub(r"((?:&amp;|\?)ct=)[A-Za-z0-9_-]+",
               lambda m: m.group(1) + "web_" + ("" if L == "en" else L.lower().replace("-", "") + "_") + "hub_" + kind, t)
    if L == "tr":  # root-level Turkish template points its brand/legal "Pofu" link at the English page
        t = t.replace('<a class="brand" href="pofu.html"', '<a class="brand" href="tr/pofu.html"')
        t = t.replace('<nav aria-label="Yasal bilgiler ve destek">\n<a href="pofu.html">', '<nav aria-label="Yasal bilgiler ve destek">\n<a href="tr/pofu.html">')
    # strip the template's injected nav pieces; process() adds fresh ones for this page
    t = re.sub(r"<!-- nav:start -->.*?<!-- nav:end -->\n?", "", t, flags=re.S)
    t = re.sub(r"\n?<!-- footnav:start -->.*?<!-- footnav:end -->", "", t, flags=re.S)
    t = re.sub(r"<style>/\* nav:css:start \*/.*?/\* nav:css:end \*/</style>\n?", "", t, flags=re.S)
    return t


def make_hubs():
    made = kept = 0
    for L in ALL:
        for kind in ("guides", "tools", "compare"):
            p = ROOT / HUBFILE[L][kind]
            if p.exists() and "<!-- hub:generated" not in rd(p):
                kept += 1
                continue
            t = build_hub(L, kind)
            if t is not None:
                made += wr(p, process(p, t, write=False)[1])
    return made, kept


def update_sitemap():
    p = ROOT / "sitemap.xml"
    s = rd(p)
    add = []
    for kind in ("guides", "tools", "compare"):
        for L in ALL:
            f = HUBFILE[L][kind]
            if (ROOT / f).exists() and f"<loc>{SITE}{f}</loc>" not in s:
                alts = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{c}" href="{SITE}{HUBFILE[c][kind]}"/>' for c in ALL)
                alts += f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE}{HUBFILE["en"][kind]}"/>'
                add.append(f"  <url>\n    <loc>{SITE}{f}</loc>\n    <lastmod>{TODAY}</lastmod>{alts}\n  </url>\n")
    if add:
        wr(p, s.replace("</urlset>", "".join(add) + "</urlset>"))
    return len(add)


# ----------------------------------------------------------------------------- home sections
def home_sections():
    changed = 0
    esc = lambda s: htmllib.escape(s, quote=False)  # noqa: E731
    for r, L in (("index.html", "en"), ("tr/index.html", "tr")):  # landing.css pages
        p = ROOT / r
        t = rd(p)
        lab = LABELS[L]
        items = "".join(f'<li><a href="{h}">{esc(l)}</a></li>' for _, l, h, _ in nav_links(L, r))
        sec = ('<!-- hubs:start -->\n<section class="hubs" aria-labelledby="hubs-title">\n'
               '<style>.hubs{padding:64px 0;background:var(--bg1)}.hubs h2{font-size:clamp(1.8rem,6vw,2.6rem);line-height:1.08;letter-spacing:-.025em;margin:0 0 12px}'
               '.hubs p{margin:0;max-width:60ch;color:var(--ink2);font-size:1.1rem;line-height:1.5}.hubs ul{list-style:none;padding:0;margin:22px 0 0;display:flex;flex-wrap:wrap;gap:10px}'
               '.hubs li a{display:inline-flex;align-items:center;min-height:44px;padding:0 20px;border-radius:999px;background:var(--card);color:var(--card-ink);box-shadow:var(--shadow-sm);font-weight:600;text-decoration:none}'
               '.hubs li a:hover{background:var(--card-soft)}</style>\n'
               f'<div class="wrap">\n<h2 id="hubs-title">{esc(lab["fh"])}</h2>\n<p>{esc(lab["fd"])}</p>\n'
               f'<ul>{items}</ul>\n</div>\n</section>\n<!-- hubs:end -->')
        if "<!-- hubs:start -->" in t:
            t2 = re.sub(r"<!-- hubs:start -->.*?<!-- hubs:end -->", lambda m: sec, t, flags=re.S)
        else:
            i = t.index('<section class="final"')
            t2 = t[:i] + sec + "\n\n    " + t[i:]
        changed += wr(p, t2)
    return changed


OLD_HOME = {"pofu.html": "/", "tr/pofu.html": "/tr/"}  # redirect stubs since the Nov 13 2026 merge


def home_links():
    """Generators still emit links to pofu.html / tr/pofu.html; point them at the landing pages instead."""
    changed = 0
    files = [f for f in ROOT.rglob("*.html") if not SKIP_DIRS & set(f.relative_to(ROOT).parts)]
    for f in files + [ROOT / "sitemap.xml", ROOT / "llms.txt"]:
        r = f.relative_to(ROOT).as_posix()
        if r in OLD_HOME:
            continue
        t = rd(f)

        def fix(m):
            h = m.group(2)
            target = posixpath.normpath(posixpath.join(posixpath.dirname(r), h))
            return m.group(1) + OLD_HOME.get(target, h) + m.group(3)

        t2 = re.sub(r'(href=")((?:\.\./)*(?:tr/)?pofu\.html)(["#])', fix, t)
        t2 = re.sub(r"https://getpofu\.com/(tr/)?pofu\.html", lambda m: "https://getpofu.com/" + (m.group(1) or ""), t2)
        changed += wr(f, t2)
    return changed


# ----------------------------------------------------------------------------- check
class _P(HTMLParser):
    VOID = {"meta", "link", "br", "img", "hr", "input", "source", "use", "path", "circle", "rect", "g", "symbol",
            "stop", "wbr", "area", "base", "col", "embed", "track", "ellipse", "line", "polygon", "polyline"}
    OPT = {"p", "li", "td", "th", "tr", "tbody", "thead", "dt", "dd", "option", "caption"}  # end tag optional

    def __init__(s):
        super().__init__(convert_charrefs=True)
        s.stack, s.errors, s.links, s.ld, s._in_ld = [], [], [], [], False

    def handle_starttag(s, tag, attrs):
        a = dict(attrs)
        for k in ("href", "src"):
            if a.get(k):
                s.links.append(a[k])
        if tag == "script" and a.get("type") == "application/ld+json":
            s._in_ld = True
            s.ld.append("")
        if tag not in s.VOID:
            s.stack.append(tag)

    def handle_startendtag(s, tag, attrs):
        for k, v in attrs:
            if k in ("href", "src") and v:
                s.links.append(v)

    def handle_endtag(s, tag):
        if tag == "script":
            s._in_ld = False
        if tag in s.VOID:
            return
        if tag in s.stack:
            while s.stack and s.stack[-1] != tag:
                x = s.stack.pop()
                if x not in s.OPT:
                    s.errors.append(f"unclosed <{x}>")
            s.stack.pop()
        else:
            s.errors.append(f"stray </{tag}>")

    def handle_data(s, d):
        if s._in_ld:
            s.ld[-1] += d


def check():
    bad = {"parse": [], "ld": [], "links": [], "dup": []}
    total = nav_pages = 0
    for p in pages():
        r = rel(p)
        t = rd(p)
        total += 1
        P = _P()
        try:
            P.feed(t)
            P.close()
        except Exception as ex:  # noqa: BLE001
            bad["parse"].append((r, str(ex)))
        if P.errors:
            bad["parse"].append((r, P.errors[:2]))
        for j in P.ld:
            try:
                json.loads(j)
            except Exception as ex:  # noqa: BLE001
                bad["ld"].append((r, str(ex)))
        for m in ("<!-- nav:start -->", "<!-- nav:end -->", "<!-- footnav:start -->", "<!-- footnav:end -->", "/* nav:css:start */"):
            if t.count(m) > 1:
                bad["dup"].append((r, m))
        nav_pages += "<!-- nav:start -->" in t
        for h in P.links:
            if re.match(r"^(https?:|mailto:|tel:|data:|#|javascript:|//)", h):
                continue
            u = urlparse(h)
            if not u.path:
                continue
            fp = ROOT / os.path.normpath(u.path.lstrip("/") if u.path.startswith("/") else os.path.join(os.path.dirname(r), u.path))
            if u.path.endswith("/") or fp.is_dir():
                fp = fp / "index.html"
            if not fp.exists():
                bad["links"].append((r, h))
    print(f"pages={total} with header nav={nav_pages}")
    for k, v in bad.items():
        print(f"{k}: {len(v)}", v[:6])
    return bad


def main():
    if "--check" in sys.argv:
        check()
        return
    if "--no-hubs" not in sys.argv:
        made, kept = make_hubs()
        print(f"hubs written={made} kept(hand-edited)={kept}")
    counts = {"standard": 0, "legal": 0, "skipped": 0}
    changed = 0
    for p in pages():
        kind, ch = process(p)
        counts[kind] += 1
        changed += ch
    hl = home_links()
    sm = update_sitemap()
    hs = home_sections()
    print(f"pages processed={counts} changed={changed}; home links fixed={hl}; home sections changed={hs}; sitemap urls added={sm}")


if __name__ == "__main__":
    main()
