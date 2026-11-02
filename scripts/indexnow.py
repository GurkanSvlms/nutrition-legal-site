#!/usr/bin/env python3
"""Ping IndexNow (Bing/Yandex/etc.) with every URL in the live sitemap.
The key is the name of the <key>.txt file at the site root. Run after each deploy:
  python3 scripts/indexnow.py
"""
import glob, json, os, urllib.request, xml.etree.ElementTree as ET
BASE = "https://gurkansvlms.github.io/nutrition-legal-site"
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
key = os.path.basename(glob.glob(os.path.join(root, "[0-9a-f]" * 32 + ".txt"))[0])[:-4]
ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
urls = [u.text for u in ET.fromstring(urllib.request.urlopen(BASE + "/sitemap.xml").read()).findall("s:url/s:loc", ns)]
body = json.dumps({"host": "gurkansvlms.github.io", "key": key, "keyLocation": f"{BASE}/{key}.txt", "urlList": urls}).encode()
req = urllib.request.Request("https://api.indexnow.org/IndexNow", data=body, headers={"Content-Type": "application/json; charset=utf-8"})
print("IndexNow", urllib.request.urlopen(req).status, len(urls), "urls")
