#!/usr/bin/env python3
"""补全 xiaoshengchu 构建中"官方有、POI 无"的学校（2026-09-10）。

来源：scripts/primary/build_xiaoshengchu_all.py 各区 MAP 的空列表条目（官方 2026 文件在册、POI 库缺失）。
策略（显式全量匹配，沿用 scripts/primary/backfill_schools.py 评分体系）：
  A. 高德 place/text 逐校检索（city=对应区 adcode），评分 ≥900 直接采用；
  B. 高德未命中但 data/middle/schools-gz.json 有同法人记录 → 复用其坐标补 primary 记录（src=from_middle）；
  C. 均未命中 → 输出待核清单（人工处理，不写入）。
特例：沙步小学（2026 并入铁铮学校）、知识城南安置区（二期）小学（暂定名）→ 跳过并注明。

输出：
  data/primary/schools-backfill.json  追加 items（留痕）
  data/primary/schools-gz.json        追加 POI（src=backfill/from_middle）
用法: python3 scripts/primary/backfill_xiaoshengchu_missing.py [--dry-run]
"""
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import ast

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "primary")
BUILD = os.path.join(ROOT, "scripts", "primary", "build_xiaoshengchu_all.py")

ADCODES = {
    'YX_MAP': '440104', 'LW_MAP': '440103', 'BW_MAP': '440111', 'PY_MAP': '440113',
    'HZ_MAP': '440105', 'TH_MAP': '440106', 'HP_MAP': '440112',
}
SKIP = {  # 无需补 POI：官方撤并/2026 新校（暂定名）
    '沙步小学（2026并入铁铮学校）': '2026 年并入铁铮学校（附件4 #27），无独立招生，不补 POI',
    '知识城南安置区（二期）小学（暂定名）': '2026 新校（暂定名），首届招生，高德/官方均无稳定 POI',
}

VARIANTS = {"穂": "穗", "敎": "教", "學": "学", "朮": "术", "甦": "苏"}


def norm(n):
    n = unicodedata.normalize("NFKC", str(n))
    n = n.replace("广州市", "").replace("番禺区", "").replace("番禺", "")
    for a, b in VARIANTS.items():
        n = n.replace(a, b)
    n = re.sub(r"[（(].*?[)）]", "", n)
    n = n.replace("小学校", "小学").replace("镇", "").strip()
    return n


def load_key():
    env_path = os.path.join(ROOT, ".env")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("AMAP_WEB_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("未找到 .env 的 AMAP_WEB_KEY")


def api(key, params):
    params["key"] = key
    url = "https://restapi.amap.com/v3/place/text?" + urllib.parse.urlencode(params)
    for a in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return json.load(r)
        except Exception as e:
            if a == 2:
                return {"error": str(e)}
            time.sleep(1.5)


def score_match(school, p):
    """评分逻辑：1000 exact / 980 括号归一 / 800 更名猜测或包含（不自动写盘）。
    非学校实体排除须查原始名——norm 会删括号，"(公交站)"等后缀必须用 raw 判断。"""
    nx = norm(school)
    raw = p.get("name") or ""
    pn = norm(raw)
    t = p.get("type") or ""
    if not any(w in t or w in pn for w in ("学校", "小学", "附小", "教育")):
        return 0, "非学校POI"
    if any(b in raw for b in ("培训", "托辅", "托管", "辅导", "自习", "成长中心",
                              "学习中心", "文具", "书店", "幼儿园", "工地", "公交", "地铁",
                              "路口", "停车场", "小区", "花园", "站")):
        return 0, "非学校实体"
    nx_eq = nx.replace("学校", "小学").replace("实验学校", "实验")
    pn_eq = pn.replace("学校", "小学").replace("实验学校", "实验")
    if nx == pn:
        return 1000, "exact"
    if nx.replace("（", "(").replace("）", ")") == pn:
        return 980, "括号归一"
    if nx_eq == pn or nx == pn_eq:
        return 800, "更名猜测(学校↔小学)，需人工确认"   # 不再自动写盘：显式匹配原则
    if nx in pn or pn in nx:
        short = nx if len(nx) <= len(pn) else pn
        if len(short) < 4:
            return 0, "过短不判"
        return 800, "包含关系"
    return 0, "无匹配"


def search(key, school, adcode, second_round=False):
    cands = {}
    kws = [school, re.sub(r"（.*?）$", "", school), re.sub(r"\(.*?\)$", "", school)]
    if second_round:  # 第二轮：扩关键词变体 + 放宽城市限制
        kws += [school.replace("小学", ""), f"广州{school}", f"广州市{school}",
                school.replace("小学", "学校"), re.sub(r"^广州市", "", school)]
    for kw in kws[:4]:
        d = api(key, {"keywords": kw, "city": adcode, "citylimit": "true",
                      "offset": "10", "page": "1", "extensions": "all"})
        for p in (d.get("pois") or []):
            cands.setdefault(p["id"], p)
        time.sleep(0.3)
    if second_round and not cands:
        d = api(key, {"keywords": school, "offset": "10", "page": "1", "extensions": "all"})
        for p in (d.get("pois") or []):
            cands.setdefault(p["id"], p)
        time.sleep(0.3)
    best = None
    for p in cands.values():
        s, reason = score_match(school, p)
        if s >= 900:
            best = (s, reason, p)
            break
    return best


def extract_missing():
    src = open(BUILD, encoding="utf-8").read()
    tree = ast.parse(src)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id not in ADCODES or not isinstance(node.value, ast.Dict):
                continue
            for k, v in zip(node.value.keys, node.value.values):
                if isinstance(v, ast.List) and len(v.elts) == 0:
                    out.append((node.targets[0].id, ast.literal_eval(k)))
    return out


def main():
    dry = "--dry-run" in sys.argv
    key = load_key()
    backfill = json.load(open(os.path.join(DATA, "schools-backfill.json"), encoding="utf-8"))
    schools = json.load(open(os.path.join(DATA, "schools-gz.json"), encoding="utf-8"))
    poi_names = {s["name"] for s in schools["schools"]}
    mids = {s["name"]: s for s in json.load(open(os.path.join(DATA, "..", "middle", "schools-gz.json"), encoding="utf-8"))["schools"]}

    missing = extract_missing()
    print(f"[补全] 官方有、POI 无共 {len(missing)} 所")
    added, from_middle, pending, map_suggest = [], [], [], []
    round1_miss = []
    for round_no in (1, 2):
        todo = missing if round_no == 1 else round1_miss
        for map_name, official in todo:
            if official in SKIP:
                if round_no == 1:
                    print(f"  [跳过] {official} —— {SKIP[official]}")
                continue
            hit = search(key, official, ADCODES[map_name], second_round=(round_no == 2))
            if hit:
                s, reason, p = hit
                loc = (p.get("location") or "0,0").split(",")
                pname = p["name"]
                # 已存在同名 POI → 记录为 MAP 映射建议（同校不同校区/更名）
                if pname in poi_names and round_no == 1:
                    map_suggest.append({"official": official, "poi": pname,
                                        "note": f"POI 已存在({reason})，应回填 MAP 映射而非新增"})
                    print(f"  [映射建议] {official} → 复用已有 POI {pname}")
                    continue
                if pname in poi_names:
                    continue
                poi = {"name": pname, "lng": float(loc[0]), "lat": float(loc[1]),
                       "adcode": ADCODES[map_name]}
                added.append({"school": official, "poi": {**poi, "src": "backfill"},
                              "score": s, "match_rule": reason, "note": f"高德POI:{pname}"})
                if not dry:
                    schools["schools"].append(poi)
                poi_names.add(pname)
                print(f"  [高德] {official} → {pname} ({s}, {reason})")
                continue
            # 高德未命中 → 中学层同法人复用
            base = official.replace("（小学部）", "").replace("(小学部)", "").replace("（2026并入铁铮学校）", "")
            base_core = norm(base).replace("小学", "")
            mhit = None
            for mn, ms in mids.items():
                mc = norm(mn).replace("初中部", "").replace("小学", "")
                if mc and (mc == base_core or base_core in mc or mc in base_core):
                    mhit = ms
                    break
            if mhit:
                poi = {"name": f"{base}(小学部)" if "小学" not in official else official,
                       "lng": mhit["lng"], "lat": mhit["lat"], "adcode": ADCODES[map_name]}
                if poi["name"] not in poi_names:
                    from_middle.append({"school": official, "poi": {**poi, "src": "from_middle"},
                                        "score": 900, "match_rule": "middle_entity",
                                        "note": f"复用中学层POI:{mhit['name']}"})
                    if not dry:
                        schools["schools"].append(poi)
                    poi_names.add(poi["name"])
                    print(f"  [中学层复用] {official} → {poi['name']}（坐标取自 {mhit['name']}）")
                else:
                    print(f"  [已存在] {official} → POI 已有 {poi['name']}")
                continue
            if round_no == 1:
                round1_miss.append((map_name, official))
                print(f"  [一轮未中] {official} —— 进入第二轮关键词扩展")
            else:
                pending.append(official)
                print(f"  [待核] {official} —— 两轮高德未命中、中学层无对应")
    # 已存在但属于映射问题的（第二轮不会再处理）→ 直接记录
    if dry:
        print("\n[dry-run] 未写盘。")
        print(f"[补全] 高德新增 {len(added)}、中学层复用 {len(from_middle)}、待核 {len(pending)}、映射建议 {len(map_suggest)}")
        if pending:
            print("待核清单:", json.dumps(pending, ensure_ascii=False))
        return
    schools["schools"].sort(key=lambda s: s["name"])
    json.dump(schools, open(os.path.join(DATA, "schools-gz.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    if added or from_middle:
        backfill.setdefault("items", [])
        backfill["items"] += [{"school": x["school"], "poi": x["poi"],
                               "score": x["score"], "match_rule": x["match_rule"],
                               "note": x["note"]} for x in added + from_middle]
        backfill["updated"] = "2026-09-10"
        json.dump(backfill, open(os.path.join(DATA, "schools-backfill.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(f"\n[补全] 高德新增 {len(added)}、中学层复用 {len(from_middle)}、待核 {len(pending)}")
    if pending:
        print("待核清单:", json.dumps(pending, ensure_ascii=False))


if __name__ == "__main__":
    main()
