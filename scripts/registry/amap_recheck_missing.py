#!/usr/bin/env python3
"""高德 POI 复查：对 education_groups.json 中"7区内真实缺失"的成员校，按名称重新搜索高德，
检查是否存在与现有 POI 重叠的点位（名称变体/新旧名/建设中），输出候选 POI 供比对。"""
import json, os, time, urllib.request, urllib.parse, sys

ROOT = "/Users/bytedance/Developer/gz_school_research"
ADCODE = {"黄埔": "440112", "白云": "440111"}

def load_key():
    with open(os.path.join(ROOT, ".env")) as f:
        for line in f:
            line = line.strip()
            if line.startswith("AMAP_WEB_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("no key")

def api(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return json.load(r)
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(1.5)

def search(key, keywords, adcode):
    """text 搜索：返回 (名称, 地址, 坐标, 类型) 列表"""
    p = {"key": key, "keywords": keywords, "city": adcode, "citylimit": "true",
         "offset": "10", "page": "1", "extensions": "all"}
    url = "https://restapi.amap.com/v3/place/text?" + urllib.parse.urlencode(p)
    d = api(url)
    out = []
    if d.get("status") != "1":
        return [("API_ERROR", d.get("info", ""), "", "", "")]
    for poi in (d.get("pois") or []):
        out.append((
            poi.get("name") or "",
            (poi.get("address") or "").replace("\n", " "),
            poi.get("location") or "",
            poi.get("type") or "",
        ))
    return out

# 载入现有 POI 三层，用于重叠比对
def load_poi(path, stage):
    try:
        d = json.load(open(os.path.join(ROOT, path)))
    except FileNotFoundError:
        return []
    return [{"name": s["name"], "lnglat": s.get("lnglat", ""), "adcode": s.get("adcode", ""), "stage": stage}
            for s in d.get("schools", [])]

poi_all = []
for p, st in [("data/primary/schools-gz.json", "小学"), ("data/middle/schools-gz.json", "初中"),
              ("data/high/schools-gz.json", "高中")]:
    poi_all += load_poi(p, st)

def dist_km(l1, l2):
    """近似距离（度→km 粗算）"""
    try:
        x1, y1 = map(float, l1.split(","))
        x2, y2 = map(float, l2.split(","))
        return ((x1-x2)**2 + (y1-y2)**2) ** 0.5 * 97
    except Exception:
        return None

# 待查名单
MISSING = [
    ("黄埔", "铁铮学校"),
    ("黄埔", "九佛中学"),
    ("黄埔", "九佛第二中学"),
    ("黄埔", "广州市黄埔区铁英学校"),
    ("白云", "广州市白云区凤凰小学"),
    ("白云", "白云湖数字科技城八方物流地块配建学校"),
    ("白云", "广州市白云区南悦中学"),
    ("白云", "广州市白云区三元里中学"),
    ("白云", "广州市白云区新新中学"),
    ("白云", "越秀天悦金沙配建小学"),
    ("白云", "广龙地块配建学校"),
    ("白云", "广州市白云区江高镇中心小学"),
]

key = load_key()
for district, name in MISSING:
    adcode = ADCODE[district]
    print(f"\n{'='*70}\n### {name}（{district} {adcode}）")
    results = search(key, name, adcode)
    if not results:
        print("  无结果")
        continue
    for rname, addr, loc, ptype in results[:6]:
        # 与现有 POI 比对：同名或距离 < 1km 视为重叠候选
        overlap = []
        for p in poi_all:
            if p["name"] == rname:
                overlap.append(f"同名POI[{p['stage']}] {p['name']}")
            elif p["lnglat"]:
                d = dist_km(loc, p["lnglat"])
                if d is not None and d < 1.0:
                    overlap.append(f"近距POI[{p['stage']}]{d:.2f}km {p['name']}")
        tag = "  ← 重叠候选: " + "; ".join(overlap) if overlap else ""
        print(f"  · {rname} | {addr} | {loc} | {ptype}{tag}")
    time.sleep(0.4)
