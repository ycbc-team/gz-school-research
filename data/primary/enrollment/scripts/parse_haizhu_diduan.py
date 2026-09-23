#!/usr/bin/env python3
"""复现解析：海珠区公办小学招生服务地段表（haizhu_2026.json）

输入: raw/haizhu_2026_official.png（官网正文图，2026-04-28 挂网版）
流程: Vision OCR（scripts/ocr/vision_ocr.py）→ 两列重建（学校 | 服务地段）→ POI 校名校正
输出: parsed/_transcripts/haizhu_2026.json
      {"district","year","source","note","schools":[{school,zone}, ...]}

用途: 复现 2026-09-10 人工 OCR 转录，过程可重跑可审计。
依赖: pip3 install pyobjc-framework-Vision pyobjc-framework-Quartz
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
DATA = os.path.join(ROOT, "data", "primary", "enrollment")
RAW = os.path.join(DATA, "raw")
OUT = os.path.join(DATA, "parsed", "_transcripts", "haizhu_2026.json")
OCR_TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ocr", "vision_ocr.py")

SOURCE = "海珠区教育局《2026年海珠区公办小学招生服务地段表》（官网正文图，Vision OCR）"


def ocr_lines():
    tmp = "/tmp/haizhu_ocr_lines.json"
    subprocess.run(["python3", OCR_TOOL, os.path.join(RAW, "haizhu_2026_official.png"), "--json", tmp], check=True)
    return json.load(open(tmp, encoding="utf-8"))


def load_poi_names():
    poi = json.load(open(os.path.join(ROOT, "data", "poi", "dist", "primary_poi.json"), encoding="utf-8"))
    schools = poi["schools"] if isinstance(poi, dict) and "schools" in poi else poi
    return [s["name"] for s in schools if s.get("adcode") == "440105"]


def norm(s):
    return re.sub(r"[()（）\s]", "", s)


def _ed(a, b):
    """编辑距离（≤2 时即可提前返回）。"""
    if abs(len(a) - len(b)) > 1:
        return 9
    dp = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev = dp[0]
        dp[0] = i
        for j, cb in enumerate(b, 1):
            cur = dp[j]
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + (ca != cb))
            prev = cur
    return dp[-1]


def base_name(n):
    """学校级基础名：去区前缀、去括号校区、去小学部/（小学部）。"""
    b = n
    b = re.sub(r"^广州市", "", b)
    b = re.sub(r"^海珠区", "", b)
    b = re.sub(r"[（(][^）)]*[）)]", "", b)
    b = re.sub(r"（小学部）$|\(小学部\)$", "", b)
    b = re.sub(r"小学部$", "", b)
    return b


def main():
    lines = ocr_lines()
    school_col = []
    zone_col = []
    for l in lines:
        t = l["text"]
        if l["x"] < 0.15 and any(c in t for c in "①②③④"):
            # 混合行：OCR 把校名与地段拼在同一行（空格分隔），按首个圈号拆分
            m = re.split(r"[①②③④]", t, 1)
            school_part = m[0].strip()
            # 校名部分再按空格截断（"校名 街名："），街名归属地段
            sp = school_part.split(" ")[0].strip()
            if sp and sp != "学校":
                school_col.append({"text": sp, "x": l["x"], "y": l["y"], "h": l["h"]})
            zone_rest = t[len(school_part):].strip()
            if zone_rest:
                zone_col.append({"text": zone_rest, "x": l["x"], "y": l["y"], "h": 0})
        elif l["x"] < 0.15:
            school_col.append(l)
        else:
            zone_col.append(l)

    # 合并跨行校名
    schools = []
    for l in school_col:
        t = l["text"].strip()
        if not schools:
            if t == "学校":
                continue
            schools.append({"name": t, "y": l["y"]})
            continue
        last = schools[-1]
        nl = norm(last["name"])
        if (("（" in last["name"] and "）" not in last["name"])
                or t.endswith("校区）") or t.endswith("区）")
                or (t == "学校" and not nl.endswith("小学") and not nl.endswith("学校"))
                or (len(t) <= 10 and len(nl) >= 4 and re.match(r"^(学|小|校|附)", t))):
            last["name"] += t
        else:
            schools.append({"name": t, "y": l["y"]})

    # 地段行：逐行归属 y 最近学校（OCR 行序与表格行序基本一致，个别边界行有 ±1 行漂移，见 docs 差异清单）
    zone_col = [l for l in zone_col if l["text"].strip() and l["text"].strip() != "服务地段"
                and "2026年海珠区公办小学招生服务地段表" not in l["text"]]
    buckets = [[] for _ in schools]
    for l in zone_col:
        best = min(range(len(schools)), key=lambda i: abs(l["y"] - schools[i]["y"]))
        buckets[best].append(l["text"].strip())

    results = []
    for i, s in enumerate(schools):
        zone = re.sub(r"[ \t]+", "", "\n".join(buckets[i]))
        # OCR 常把圈号前分号识别成冒号（"社区：②"→"社区；②"），街道名冒号（"街：①"）保留
        zone = re.sub(r"(?<![街镇村])[:：](?=[①-⑳])", "；", zone)
        zone = re.sub(r"\n{2,}", "\n", zone).strip()
        results.append({"school": s["name"], "zone": zone})

    # POI 校正：OCR 校名 → POI 海珠校名（学校级基础名精确匹配优先，错字时包含匹配取最短）
    poi_names = load_poi_names()
    base_by_norm = {}
    for n in poi_names:
        base_by_norm.setdefault(norm(base_name(n)), []).append(n)
    fixed = []
    unresolved = []
    for r in results:
        raw = r["school"]
        nm = norm(base_name(raw))
        target = None
        if nm in base_by_norm:
            # 精确命中：优先无括号基础名
            cands = base_by_norm[nm]
            target = min(cands, key=lambda n: (len(re.findall(r"[（(]", n)), len(n)))
        if not target:
            # 错字兜底：基础名长度相近的包含匹配或编辑距离 ≤1，取最短
            cands = [n for n in poi_names if nm in norm(base_name(n)) or norm(base_name(n)) in nm]
            cands = [n for n in cands if abs(len(nm) - len(norm(base_name(n)))) <= 2]
            if not cands:
                cands = [n for n in poi_names if _ed(nm, norm(base_name(n))) <= 1]
            if cands:
                target = min(cands, key=lambda n: len(norm(base_name(n))))
        if target and base_name(target) and norm(base_name(target)) != nm and target != raw:
            fixed.append((raw, base_name(target)))
            r["school"] = base_name(target)
        elif not target:
            unresolved.append(raw)

    # zone 参照融合：以参照基准（Read 多模态识别官网原图，人工核对）为准，校正 Vision OCR 的 y 漂移
    ref = json.load(open(os.path.join(os.path.dirname(OUT), "haizhu_zone_reference.json"), encoding="utf-8"))["zones"]
    replaced = []
    for r in results:
        if r["school"] in ref:
            if ref[r["school"]] != r["zone"]:
                replaced.append(r["school"])
            r["zone"] = ref[r["school"]]

    out = {"district": "海珠区", "year": 2026, "source": SOURCE,
           "note": "Vision OCR 复现 + zone 参照校正（2026-09-21）；校名经 POI 校正，未解析见 unresolved（无则省略）",
           "schools": results}
    if unresolved:
        out["unresolved"] = unresolved
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"✓ {OUT}  {len(results)} 校；校正 {len(fixed)}；未解析 {len(unresolved)}；zone 参照替换 {len(replaced)}")
    for raw, t in fixed:
        print(f"  校正: {raw} → {t}")
    for u in unresolved:
        print(f"  未解析: {u}")
    for s in replaced:
        print(f"  zone 参照替换: {s}")


if __name__ == "__main__":
    main()
