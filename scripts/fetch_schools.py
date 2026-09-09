#!/usr/bin/env python3
"""采集广州七区小学 POI 与区边界，输出项目共享数据目录 data/primary/。

用法: python3 scripts/fetch_schools.py
依赖: 项目根 .env 中的 AMAP_WEB_KEY（Web 服务类型 Key）
数据源: 高德地图 Web 服务 API（place/text 与 config/district）
输出:
  data/primary/schools-gz.json  唯一数据真源（JSON）
  apps/web/legacy/_generated/primary/schools.js  旧页面兼容产物（window.GZ_SCHOOLS）
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根（scripts/ 的上层）
ROOT = BASE

DISTRICTS = [
    ("荔湾区", "440103"),
    ("越秀区", "440104"),
    ("海珠区", "440105"),
    ("天河区", "440106"),
    ("白云区", "440111"),
    ("黄埔区", "440112"),
    ("番禺区", "440113"),
]


def load_key():
    env_path = os.path.join(ROOT, ".env")
    if not os.path.exists(env_path):
        raise SystemExit("未找到项目根 .env，请先写入 AMAP_WEB_KEY")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("AMAP_WEB_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("项目根 .env 中未配置 AMAP_WEB_KEY")


def api(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return json.load(r)
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(1.5)


def fetch_pois(key, adcode):
    """翻页采集某区小学 POI。

    查询方式（合并去重）：
      1. types=141203（高德「小学」分类）——分类最准，含「XX学校(小学部)」等
      2. keywords=小学 —— 兜底补充名称含「小学」但未归入该分类的
    无 100 条上限：高德单次搜索可按 offset/page 翻页，实际返回数远超 100。
    """
    out = []

    def collect(params):
        page = 1
        while True:
            p = dict(params)
            p.update({"offset": "25", "page": str(page), "extensions": "all"})
            d = api("https://restapi.amap.com/v3/place/text?" + urllib.parse.urlencode(p))
            if d.get("status") != "1":
                print(f"  [warn] {adcode} {params.get('types') or params.get('keywords')} page {page}: {d.get('info')}")
                break
            pois = d.get("pois") or []
            for poi in pois:
                loc = (poi.get("location") or "").split(",")
                if len(loc) != 2:
                    continue
                out.append({
                    "name": poi.get("name") or "",
                    "lng": float(loc[0]),
                    "lat": float(loc[1]),
                    "adcode": adcode,
                })
            count = int(d.get("count") or 0)
            if not pois or page * 25 >= count:
                break
            page += 1
            time.sleep(0.4)

    collect({"key": key, "types": "141203", "city": adcode, "citylimit": "true"})
    time.sleep(0.4)
    collect({"key": key, "keywords": "小学", "city": adcode, "citylimit": "true"})

    # 只保留小学/学校类 POI：名称含「小学/学校/附小/小学部」且非培训机构
    NON_SCHOOL = ["培训", "托辅", "托管", "辅导", "自习", "成长中心", "学习中心",
                  "学习规划", "国际教育", "教育咨询", "文具", "书店", "幼儿园",
                  "工地", "城门楼", "教师楼", "智云书房", "博通教育", "知了托管",
                  "玩具店", "童趣园", "感统", "口才"]
    keep, seen = [], set()
    for s in out:
        n = s["name"]
        if not n:
            continue
        if not ("小学" in n or "学校" in n or "附小" in n or "小学部" in n):
            continue
        if any(b in n for b in NON_SCHOOL):
            continue
        k = (n, round(s["lng"], 5), round(s["lat"], 5))
        if k in seen:
            continue
        seen.add(k)
        keep.append(s)
    return keep


def fetch_boundary(key, name):
    """获取某区边界多边形（polyline -> [[[lng,lat],...], ...]）"""
    q = urllib.parse.urlencode({
        "key": key, "keywords": name, "subdistrict": "0", "extensions": "all",
    })
    d = api("https://restapi.amap.com/v3/config/district?" + q)
    if d.get("status") != "1":
        raise SystemExit(f"district 查询失败: {name} {d.get('info')}")
    ds = d.get("districts") or []
    if not ds:
        raise SystemExit(f"district 未找到: {name}")
    polyline = ds[0].get("polyline") or ""
    paths = []
    for seg in polyline.split("|"):
        pts = []
        for pair in seg.split(";"):
            if not pair:
                continue
            lng, lat = pair.split(",")
            pts.append([float(lng), float(lat)])
        if len(pts) >= 3:
            paths.append(pts)
    return paths


def main():
    key = load_key()
    # 可选参数：只采集指定区（如 python3 fetch_schools.py 440113）
    only = {a for a in sys.argv[1:] if re.fullmatch(r"\d{6}", a)}
    districts = [d for d in DISTRICTS if not only or d[1] in only]
    result = {
        "updated": time.strftime("%Y-%m-%d"),
        "source": "高德地图 Web 服务 API (place/text + config/district)",
        "note": "小学分类(types=141203)翻页采集 + 关键词补充，无 100 条限制",
        "districts": [],
        "schools": [],
    }
    for name, adcode in districts:
        print(f"== {name} ({adcode})")
        schools = fetch_pois(key, adcode)
        print(f"   schools: {len(schools)}")
        boundary = fetch_boundary(key, name)
        print(f"   boundary segments: {len(boundary)}")
        result["districts"].append({"name": name, "adcode": adcode, "boundary": boundary})
        result["schools"].extend(schools)
        time.sleep(0.4)

    data_dir = os.path.join(BASE, "data", "primary")
    legacy_dir = os.path.join(BASE, "apps", "web", "legacy", "_generated", "primary")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(legacy_dir, exist_ok=True)
    with open(os.path.join(data_dir, "schools-gz.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(legacy_dir, "schools.js"), "w", encoding="utf-8") as f:
        f.write("window.GZ_SCHOOLS = ")
        json.dump(result, f, ensure_ascii=False)
        f.write(";\n")

    total = len(result["schools"])
    per = {name: sum(1 for s in result["schools"] if s["adcode"] == adcode) for name, adcode in districts}
    print(f"\n完成: 共 {total} 所小学")
    print("各区: " + ", ".join(f"{n} {per[n]}" for n, _ in districts))
    print(f"输出: {os.path.join(data_dir, 'schools-gz.json')} / {os.path.join(legacy_dir, 'schools.js')}")


if __name__ == "__main__":
    main()
