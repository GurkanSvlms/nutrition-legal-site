#!/usr/bin/env python3
"""Check data/trust/<lang>.json against en.json: same keys/list lengths and same {placeholders}.
    python3 scripts/check_trust.py [lang ...]"""
import json, re, sys
from pathlib import Path
D = Path(__file__).resolve().parent.parent / "data" / "trust"
en = json.loads((D / "en.json").read_text(encoding="utf-8"))


def walk(a, b, path, errs):
    if isinstance(a, dict):
        if not isinstance(b, dict) or set(a) != set(b):
            errs.append(f"{path}: keys differ"); return
        for k in a: walk(a[k], b[k], f"{path}.{k}", errs)
    elif isinstance(a, list):
        if not isinstance(b, list) or len(a) != len(b):
            errs.append(f"{path}: list length differs"); return
        for i, (x, y) in enumerate(zip(a, b)): walk(x, y, f"{path}[{i}]", errs)
    elif isinstance(a, str):
        if not isinstance(b, str) or not b.strip():
            errs.append(f"{path}: empty"); return
        if set(re.findall(r"\{\w+\}", a)) != set(re.findall(r"\{\w+\}", b)):
            errs.append(f"{path}: placeholders differ")
        if sorted(re.findall(r'href="([^"]+)"', a)) != sorted(re.findall(r'href="([^"]+)"', b)):
            errs.append(f"{path}: links differ")


langs = sys.argv[1:] or sorted(p.stem for p in D.glob("*.json") if p.stem != "en")
bad = 0
for L in langs:
    errs = []
    try:
        walk(en, json.loads((D / f"{L}.json").read_text(encoding="utf-8")), L, errs)
    except Exception as e:
        errs.append(str(e))
    print(L, "ok" if not errs else errs[:10]); bad += bool(errs)
sys.exit(1 if bad else 0)
