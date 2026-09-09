#!/usr/bin/env python3
"""采集广州七区初中 POI 与区边界，输出项目共享数据目录 data/middle/。

范围：7 区（荔湾/越秀/海珠/天河/白云/黄埔/番禺），与小学同口径，排除远郊南沙/花都/从化/增城。

用法: python3 scripts/fetch_middle_schools.py
依赖: 项目根 .env 中的 AMAP_WEB_KEY（Web 服务类型 Key）
数据源: 高德地图 Web 服务 API（place/text 与 config/district）
输出:
  data/middle/schools.js       页面加载用（window.GZ_MIDDLE_SCHOOLS）
  data/middle/schools-gz.json  可读复核用

初中采集特殊点（相对小学）：
- 广州大量初中名为「XX中学」或为完全中学（初高中一体），仅查 types=141201 会漏。
- 三路查询合并去重：
  1. types=141201（初中分类）——最准
  2. keywords=初中——兜底名称含「初中」的
  3. types=141200（中学分类）——捕获「XX中学」命名的初中和完全中学
- 过滤：保留名称含「初中」的；保留名称含「中学」但不含「高中/高级中学」的
  （即完全中学和纯初中命名为中学的）；剔除名称含「高中/高级中学」且不含
  「初中」的纯高中；剔除培训机构/辅导/托管/国际课程中心等非学历教育 POI。
- 去重：按 (name, round(lng,5), round(lat,5))，同校多门点合并。
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

# 非学历教育 / 非初中 POI 特征词（名称命中即剔除）
NON_SCHOOL = [
    "培训", "辅导", "托辅", "托管", "自习", "成长中心", "学习中心",
    "学习规划", "国际教育", "国际课程", "教育咨询", "教育科技", "教育文化",
    "复读", "补习", "家教", "艺术", "奥数", "研学", "留学", "出国", "考研",
    "成人", "电大", "函授", "夜校", "驾校", "幼儿园", "早教", "文具", "书店",
    "少年宫", "活动中心", "体育馆",
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
    """翻页采集某区初中 POI（三路查询合并）。"""
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

    # 三路合并：初中分类 / 关键词「初中」/ 中学分类
    collect({"key": key, "types": "141201", "city": adcode, "citylimit": "true"})
    time.sleep(0.4)
    collect({"key": key, "keywords": "初中", "city": adcode, "citylimit": "true"})
    time.sleep(0.4)
    collect({"key": key, "types": "141200", "city": adcode, "citylimit": "true"})

    # 过滤：初中 + 完全中学（初高中一体），剔除纯高中与培训机构
    def is_middle(n):
        if not n:
            return False
        if any(b in n for b in NON_SCHOOL):
            return False
        # 附属小学 / 小学部：非初中点位，剔除（「XX初中部(XX小学校区)」含初中，保留）
        if "小学" in n and "初中" not in n:
            return False
        if "初中" in n:
            return True
        if "中学" in n:
            # 名称含「高中/高级中学」且不含「初中」→ 纯高中（或高中校区），剔除
            if "高中" in n or "高级中学" in n:
                return False
            return True  # 「XX中学」命名的初中 / 完全中学
        return False

    keep, seen = [], set()
    for s in out:
        n = s["name"]
        if not is_middle(n):
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
    # 可选参数：只采集指定区（如 python3 fetch_middle_schools.py 440118）
    only = {a for a in sys.argv[1:] if re.fullmatch(r"\d{6}", a)}
    districts = [d for d in DISTRICTS if not only or d[1] in only]
    result = {
        "updated": "2026-09-09",
        "source": "高德地图 Web 服务 API (place/text + config/district)",
        "note": "初中分类(types=141201)+关键词「初中」+中学分类(types=141200)三路翻页采集合并，"
                "保留初中与完全中学，剔除纯高中/培训机构，无 100 条限制",
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

    data_dir = os.path.join(BASE, "data", "middle")
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, "schools-gz.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(data_dir, "schools.js"), "w", encoding="utf-8") as f:
        f.write("window.GZ_MIDDLE_SCHOOLS = ")
        json.dump(result, f, ensure_ascii=False)
        f.write(";\n")

    total = len(result["schools"])
    per = {name: sum(1 for s in result["schools"] if s["adcode"] == adcode) for name, adcode in districts}
    print(f"\n完成: 共 {total} 所初中/完全中学")
    print("各区: " + ", ".join(f"{n} {per[n]}" for n, _ in districts))
    print(f"输出: {os.path.join(data_dir, 'schools.js')} / schools-gz.json")


if __name__ == "__main__":
    main()
