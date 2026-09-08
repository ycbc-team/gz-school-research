#!/usr/bin/env python3
"""采集广州七区小学 POI 与区边界，输出项目共享数据目录 data/。

用法: python3 scripts/fetch_schools.py
依赖: 项目根 .env 中的 AMAP_WEB_KEY（Web 服务类型 Key）
数据源: 高德地图 Web 服务 API（place/text 与 config/district）
输出:
  data/schools.js   页面加载用（window.GZ_SCHOOLS，多端共用）
  data/schools-gz.json  可读复核用
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # map-app/
ROOT = os.path.dirname(BASE)  # 项目根

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
    """翻页采集某区名称含「小学」的 POI，单次搜索最多 100 条（平台上限）"""
    out, page, offset = [], 1, 25
    while True:
        q = urllib.parse.urlencode({
            "key": key, "keywords": "小学", "city": adcode, "citylimit": "true",
            "offset": str(offset), "page": str(page), "extensions": "all",
        })
        d = api("https://restapi.amap.com/v3/place/text?" + q)
        if d.get("status") != "1":
            print(f"  [warn] {adcode} page {page}: {d.get('info')}")
            break
        pois = d.get("pois") or []
        for p in pois:
            loc = (p.get("location") or "").split(",")
            if len(loc) != 2:
                continue
            name = p.get("name") or ""
            if "小学" not in name:
                continue
            out.append({
                "name": name,
                "lng": float(loc[0]),
                "lat": float(loc[1]),
                "adcode": adcode,
            })
        count = int(d.get("count") or 0)
        if not pois or page * offset >= count or page * offset >= 100:
            break
        page += 1
        time.sleep(0.4)
    # 按 名称+坐标 去重
    seen, uniq = set(), []
    for s in out:
        k = (s["name"], round(s["lng"], 5), round(s["lat"], 5))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(s)
    return uniq


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
    result = {
        "updated": time.strftime("%Y-%m-%d"),
        "source": "高德地图 Web 服务 API (place/text + config/district)",
        "note": "每区最多 100 所（高德单次搜索上限）",
        "districts": [],
        "schools": [],
    }
    for name, adcode in DISTRICTS:
        print(f"== {name} ({adcode})")
        schools = fetch_pois(key, adcode)
        print(f"   schools: {len(schools)}")
        boundary = fetch_boundary(key, name)
        print(f"   boundary segments: {len(boundary)}")
        result["districts"].append({"name": name, "adcode": adcode, "boundary": boundary})
        result["schools"].extend(schools)
        time.sleep(0.4)

    data_dir = os.path.join(BASE, "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, "schools-gz.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(data_dir, "schools.js"), "w", encoding="utf-8") as f:
        f.write("window.GZ_SCHOOLS = ")
        json.dump(result, f, ensure_ascii=False)
        f.write(";\n")

    total = len(result["schools"])
    per = {name: sum(1 for s in result["schools"] if s["adcode"] == adcode) for name, adcode in DISTRICTS}
    print(f"\n完成: 共 {total} 所小学")
    print("各区: " + ", ".join(f"{n} {per[n]}" for n, _ in DISTRICTS))
    print(f"输出: {os.path.join(data_dir, 'schools.js')} / schools-gz.json")


if __name__ == "__main__":
    main()
