#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 data/middle/tier1_schools_all.json 生成 data/middle/tier1.js（window.GZ_MIDDLE_TIER1）。

为每所初中生成：
  - 支撑信号摘要（中考成绩、示范性高中、教育集团、建校年份、指标到校）
  - 校名匹配别名（供地图点位匹配，含校区/简称变体）
  - POI 匹配模拟验证（与地图页同算法），未命中的梯队学校尝试高德 API 补坐标
  - 输出未命中清单 data/middle/tier1_unmatched.json

用法：python3 scripts/build_middle_tier1_js.py
"""
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "middle" / "tier1_schools_all.json"
OUT = ROOT / "data" / "middle" / "tier1.js"
POI_SRC = ROOT / "data" / "middle" / "schools.js"
UNMATCHED_OUT = ROOT / "data" / "middle" / "tier1_unmatched.json"
COORDS_CACHE = ROOT / "data" / "middle" / "amap_coords_cache.json"

# 手工补充的匹配别名（tier1 规范名 -> 额外别名，用于校区/旧称/惯用简称）
ALIAS_EXTRA = {
    "广东实验中学（初中部）": ["省实", "广东实验中学初中部"],
    "广州市执信中学（执信路校区）": ["广州市执信中学初中部", "执信中学"],
    "广州市执信中学（天河校区）": ["执信中学(天河校区)", "执信中学天河校区", "广州市执信中学天河校区"],
    "广州市第二中学（初中部）": ["广州市第二中学初中部", "广州市第二中学应元路校区"],
    "广州市第二中学（科学城校区）": ["广州市第二中学科学城校区"],
    "广州大学附属中学（黄华路校区）": ["广大附中", "广州大学附属中学黄华路校区"],
    "广州大学附属中学（大学城校区）": ["广州大学附属中学大学城校区", "广大附中大学城"],
    "广州市铁一中学（越秀校区）": ["铁一中学", "广州市铁一中学越秀校区"],
    "广州市铁一中学（番禺校区/亚运城）": ["广州市铁一中学(番禺校区)", "广州市铁一中学番禺校区", "铁一中番禺校区", "广铁一中亚运城"],
    "广州市第七中学（本部）": ["广州市第七中学初中部"],
    "广州市第十六中学（本部）": ["广州市第十六中学初中部"],
    "广州市培正中学（初中部）": ["广州市培正中学初中部", "培正中学初中部"],
    "广东广雅中学（初中部）": ["广雅中学", "广东广雅中学初中部"],
    "广州市荔湾区西关广雅实验学校（西雅）": ["西关广雅实验学校", "西关广雅", "广州市西关广雅实验学校"],
    "广东实验中学荔湾学校（省实荔湾）": ["省实荔湾", "广东实验中学荔湾学校"],
    "广州市真光中学（校本部）": ["广州市真光中学初中部", "真光中学"],
    "广州市西关外国语学校": ["西关外国语学校"],
    "华南师范大学附属中学（初中部）": ["华附", "华南师大附中", "华南师范大学附属中学初中部"],
    "华南师范大学附属中学（知识城校区）": ["华南师范大学附属中学知识城校区", "华附知识城"],
    "广州市天河外国语学校（珠江新城校区）": ["天河外国语学校", "广州天河外国语学校", "广州市天河外国语学校珠江新城校区"],
    "清华附中湾区学校": ["清华附中湾区学校", "清华大学附属中学湾区学校"],
    "广州市天河区汇景实验学校": ["广州市第四十七中汇景实验学校", "汇景实验学校", "四十七中汇景实验学校"],
    "广州天省实验学校（民办）": ["天省实验学校", "广东实验中学附属天河学校", "省实附中"],
    "广州市白云区金广实验学校（金广附/广大附中实验中学）": ["广大附中实验中学", "金广实验学校", "金广附", "白云广附实验学校"],
    "广东实验中学永平校区（省实永平）": ["省实永平", "广东实验中学永平校区", "广东实验中学白云校区"],
    "广州市培英中学（云城校区）": ["广州市培英中学云城校区", "培英中学"],
    "广州市白云区华赋学校（民办）": ["华赋学校"],
    "广州市白云实验学校（白云省实，民办）": ["白云实验学校", "白云省实"],
    "广州市白云区云雅实验学校（云雅/白云广雅，民办）": ["广州云雅实验学校", "云雅实验学校", "云雅", "白云广雅"],
    "广州市白云区铁一学校（白云铁一）": ["白云铁一", "广州市白云区铁一学校"],
    "广州大学附属中学黄埔实验学校（黄埔广附）": ["黄埔广附", "广州大学附属中学黄埔实验学校", "广大附中黄埔实验学校"],
    "广州市黄埔区苏元学校（二中苏元）": ["二中苏元", "苏元学校", "广州市黄埔区苏元实验学校"],
    "广州市玉岩中学": ["玉岩中学"],
    "广州市黄埔区铁英学校（黄埔铁英）": ["广铁一中铁英中学", "铁英学校", "黄埔铁英"],
    "广州市番禺区桥城中学": ["桥城中学"],
    "广东仲元中学（初中部）": ["仲元中学", "广东仲元中学初中部"],
    "广州市番禺区祈福新邨学校（小金龙，民办）": ["祈福新邨学校", "祈福学校", "小金龙"],
    "广州市番禺区恒润实验学校（民办）": ["恒润实验学校"],
    "广州市番禺区番外外国语学校（番外，民办）": ["番外外国语学校", "番外"],
    "广州市番禺执信中学（星执学校，民办）": ["星执学校", "番禺执信中学", "星执"],
}

# 高德 POI 无主点位、经 Amap Web API（v3/place/text）补充坐标的学校
# 坐标系 GCJ-02，与地图瓦片（高德）一致；source 记录取点来源
EXTRA_COORDS = {
    "广州市越秀区育才实验学校": {
        "lng": 113.303041, "lat": 23.108523,
        "addr": "二沙岛（育才实验学校西南门旁）",
        "source": "高德POI：广州市育才实验学校求索楼（typecode 141200）",
    },
    "广州市荔湾区西关广雅实验学校（西雅）": {
        "lng": 113.228027, "lat": 23.130194,
        "addr": "南岸路悦康街1号",
        "source": "高德POI：西关广雅实验学校(南岸路校区)（typecode 141200）",
    },
    "广州市天河外国语学校（珠江新城校区）": {
        "lng": 113.337398, "lat": 23.123623,
        "addr": "海乐路9号",
        "source": "高德POI：广州市天河外国语学校(珠江新城校区)（typecode 141202）",
    },
    "清华附中湾区学校": {
        "lng": 113.391030, "lat": 23.138670,
        "addr": "天坤二路99号",
        "source": "高德POI：清华附中湾区学校（typecode 141200）",
    },
    "广州天省实验学校（民办）": {
        "lng": 113.346508, "lat": 23.177128,
        "addr": "天源路399号",
        "source": "高德POI：广州天省实验学校（typecode 141200）",
    },
    "广东实验中学永平校区（省实永平）": {
        "lng": 113.318298, "lat": 23.246398,
        "addr": "白云大道北570号",
        "source": "高德POI：广东实验中学(白云校区)（即省实永平校区，typecode 141202）",
    },
    "广州市白云实验学校（白云省实，民办）": {
        "lng": 113.255178, "lat": 23.229573,
        "addr": "夏茅沙园坊十字大街58号",
        "source": "高德POI：省实白云实验学校（typecode 141202）",
    },
    "广州市白云区铁一学校（白云铁一）": {
        "lng": 113.281860, "lat": 23.258571,
        "addr": "均禾街新石路163号（与铁一白云校区同址办学）",
        "source": "高德POI：广州市铁一中学白云校区(初中部)（白云铁一无独立POI，取同址点位）",
    },
    "广州大学附属中学黄埔实验学校（黄埔广附）": {
        "lng": 113.464533, "lat": 23.107536,
        "addr": "悦府二街1号（东校区；另有西校区在护林路）",
        "source": "高德POI：广大附中黄埔实验学校(东校区)（typecode 141202）",
    },
    "广州市黄埔区苏元学校（二中苏元）": {
        "lng": 113.473692, "lat": 23.182952,
        "addr": "水西路17号",
        "source": "高德POI：广州市黄埔区苏元学校(西校区)（typecode 141202）",
    },
    "广州市番禺区祈福新邨学校（小金龙，民办）": {
        "lng": 113.331605, "lat": 22.962648,
        "addr": "祈福新邨福荫路（中学部）",
        "source": "高德POI：广州市祈福新邨学校中学部（typecode 141202）",
    },
    "广州市番禺区恒润实验学校（民办）": {
        "lng": 113.277278, "lat": 23.033409,
        "addr": "洛浦街浦华路238号",
        "source": "高德POI：恒润实验学校（typecode 141200）",
    },
    "广州市番禺区番外外国语学校（番外，民办）": {
        "lng": 113.372089, "lat": 22.975547,
        "addr": "东环街莲花大道中202号",
        "source": "高德POI：广州番外外国语学校（typecode 141200）",
    },
    "广州市番禺执信中学（星执学校，民办）": {
        "lng": 113.338271, "lat": 23.024491,
        "addr": "星光大道东（星执学校）",
        "source": "高德POI：广州市星执学校（typecode 141202）",
    },
}

DISTRICTS = ["越秀区", "荔湾区", "海珠区", "天河区", "白云区", "黄埔区", "番禺区"]

# 过短的通用别名（去区名后只剩通用后缀），禁止作为前缀匹配键，避免误配
GENERIC_SHORT = {
    "实验学校", "附属学校", "实验中学", "第一中学", "第二中学", "第三中学",
    "第四中学", "第五中学", "第六中学", "第七中学", "第八中学", "中学", "学校",
}


def norm_paren(name: str) -> str:
    """去 广州市 前缀，括号归一为半角，保留括号内容（校区信息在初中阶段很重要）。"""
    n = str(name).replace("广州市", "")
    n = n.replace("（", "(").replace("）", ")")
    return n.strip()


def strip_parenthesis(name: str) -> str:
    return re.sub(r"[（(].*?[)）]", "", name).strip()


def norm_short(name: str) -> str:
    """去 广州市 前缀 + 去括号 + 去区名，用于宽松匹配。"""
    n = norm_paren(name)
    n = strip_parenthesis(n)
    for d in DISTRICTS:
        n = n.replace(d, "")
    return n.strip()


def zhongkao_str(s: dict) -> str:
    z = s.get("zhongkao") or {}
    if not z or not z.get("data"):
        return "未查到"
    year = z.get("year") or "近年"
    scope = z.get("scope") or ""
    data = str(z["data"]).strip()
    if len(data) > 150:
        data = data[:150] + "…"
    head = f"{year}年" + (f"（{scope}）" if scope else "")
    official = z.get("official")
    tail = "" if official else "（网传，非官方）"
    return f"{head}：{data}{tail}"


def demonstration_high_str(s: dict) -> str:
    d = s.get("demonstration_high") or {}
    if not d or not d.get("level"):
        return "未查到"
    level = d["level"]
    year = d.get("year")
    return (f"{year}年评" if year else "") + level


def education_group_str(s: dict) -> str:
    g = s.get("education_group") or {}
    if not g or not g.get("name"):
        return "未查到"
    name = g["name"]
    role = g.get("role")
    return name + (f"（{role}）" if role and role != "未查到" else "")


def founded_str(s: dict) -> str:
    f = s.get("founded") or {}
    if not f or not f.get("year"):
        return "未查到"
    year = f["year"]
    note = f.get("note")
    return f"{year}年建校" + (f"（{note}）" if note else "")


def quota_allocation_str(s: dict) -> str:
    q = s.get("quota_allocation") or {}
    if not q or not q.get("data"):
        return None
    year = q.get("year") or ""
    data = str(q["data"]).strip()
    if len(data) > 130:
        data = data[:130] + "…"
    return (f"{year}年" if year else "") + data


def load_amap_key() -> str:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("AMAP_WEB_KEY="):
            return line.split("=", 1)[1].strip()
    return ""


def amap_fetch(name: str, key: str):
    """按学校名查询高德 POI，返回 (lng, lat, addr, poi_name, typecode) 或 None。"""
    params = {
        "key": key,
        "keywords": name,
        "city": "广州",
        "citylimit": "true",
        "offset": "5",
        "page": "1",
        "extensions": "base",
    }
    url = "https://restapi.amap.com/v3/place/text?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            d = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"    [amap error] {name}: {e}")
        return None
    if d.get("status") != "1" or not d.get("pois"):
        return None
    core = norm_short(name)
    best = None
    best_score = 0
    for p in d["pois"]:
        pn = norm_paren(p.get("name") or "")
        pn_strip = strip_parenthesis(pn)
        score = 0
        if core and pn_strip == core:
            score = 4
        elif core and (pn_strip.startswith(core) or core.startswith(pn_strip)) and len(core) >= 4:
            score = 3
        elif core and (core in pn_strip or pn_strip in core):
            score = 2
        elif core and core[:4] and pn_strip.startswith(core[:4]):
            score = 1
        if score > best_score:
            best_score = score
            best = p
    if not best:
        return None
    loc = (best.get("location") or "").split(",")
    if len(loc) != 2:
        return None
    return {
        "lng": float(loc[0]),
        "lat": float(loc[1]),
        "addr": best.get("address") or "",
        "poi_name": best.get("name") or "",
        "typecode": best.get("typecode") or "",
    }


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    schools = []
    for dist, meta in data["districts"].items():
        for s in meta["schools"]:
            aliases = []
            base_keep = norm_paren(s["name"])
            aliases.append(base_keep)
            base_strip = strip_parenthesis(base_keep)
            if base_strip and base_strip != base_keep:
                aliases.append(base_strip)
            short = norm_short(s["name"])
            if short and short not in aliases and len(short) >= 4 and short not in GENERIC_SHORT:
                aliases.append(short)
            for extra in ALIAS_EXTRA.get(s["name"], []):
                ne = norm_paren(extra)
                if ne and ne not in aliases:
                    aliases.append(ne)
            rec = {
                "name": s["name"],
                "district": dist,
                "verdict": s.get("conclusion", ""),
                "rumor_tier": s.get("rumor_tier", "第一梯队"),
                "rumor_notes": (s.get("rumor_notes") or "")[:120],
                "conclusion_basis": s.get("conclusion_basis", ""),
                "signals": {
                    "zhongkao": zhongkao_str(s),
                    "demonstration_high": demonstration_high_str(s),
                    "education_group": education_group_str(s),
                    "founded": founded_str(s),
                },
                "aliases": aliases,
            }
            qa = quota_allocation_str(s)
            if qa:
                rec["signals"]["quota_allocation"] = qa
            if s["name"] in EXTRA_COORDS:
                ec = EXTRA_COORDS[s["name"]]
                rec["coords"] = {"lng": ec["lng"], "lat": ec["lat"]}
                rec["coord_addr"] = ec["addr"]
                rec["coord_source"] = ec["source"]
            schools.append(rec)
    out = {
        "updated": data.get("verified_date", ""),
        "title": data.get("title", ""),
        "note": "民间梯队标签核验数据：verdict 取值 有支撑/部分支撑/不支撑（民间口径，非官方评价）。",
        "schools": schools,
    }
    print(f"loaded: {SRC}  ({len(schools)} schools)")

    # ---- 匹配模拟验证：与地图页同算法（tier1.js 预生成别名，长别名优先） ----
    src = POI_SRC.read_text(encoding="utf-8")
    m = re.search(r"window\.GZ_MIDDLE_SCHOOLS\s*=\s*(\{.*?\});?\s*$", src, re.S)
    poi_data = json.loads(m.group(1))
    poi_names = [x["name"] for x in poi_data["schools"]]

    table = []  # (norm_alias, school_name)
    seen_keys = set()
    for sc in schools:
        for a in sc["aliases"]:
            na = norm_paren(a)
            if not na or na in seen_keys:
                continue
            seen_keys.add(na)
            table.append((na, sc["name"]))
    # 长别名优先，避免短前缀抢先
    table.sort(key=lambda x: -len(x[0]))

    def match(poi_norm: str):
        for na, sn in table:
            if poi_norm == na or (len(na) >= 4 and poi_norm.startswith(na)):
                return sn
        return None

    hits = {}
    for p in poi_names:
        sn = match(norm_paren(p))
        if sn:
            hits.setdefault(sn, []).append(p)

    missing = [sc["name"] for sc in schools if sc["name"] not in hits]
    print("\n== POI 未命中（地图上无点位的梯队学校）==")
    for x in missing:
        print("  -", x)
    print("\n== 命中学校数:", len(hits), "/", len(schools), "==")
    print("== 命中点位总数:", sum(len(v) for v in hits.values()), "==")
    dup = [k for k, v in hits.items() if len(v) > 1]
    print("== 多点位学校（校区集群，正常）:", len(dup), "==")
    for k in dup:
        print("  ", k, "->", hits[k])

    # ---- 未命中学校：高德 API 补坐标 ----
    key = load_amap_key()
    cache = {}
    if COORDS_CACHE.exists():
        try:
            cache = json.loads(COORDS_CACHE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            cache = {}
    unmatched_out = []
    print("\n== 高德 API 补点 ==")
    for sc in schools:
        if sc["name"] in hits:
            continue
        coords = None
        if sc["name"] in EXTRA_COORDS:
            ec = EXTRA_COORDS[sc["name"]]
            coords = {"lng": ec["lng"], "lat": ec["lat"], "addr": ec["addr"], "source": ec["source"], "poi_name": ec.get("poi_name", sc["name"])}
        elif sc["name"] in cache:
            coords = cache[sc["name"]]
        elif key:
            res = amap_fetch(sc["name"], key)
            if res:
                coords = {
                    "lng": res["lng"], "lat": res["lat"], "addr": res["addr"],
                    "source": f"高德POI：{res['poi_name']}（typecode {res['typecode']}）",
                    "poi_name": res["poi_name"],
                }
                cache[sc["name"]] = coords
        if coords:
            sc["coords"] = {"lng": coords["lng"], "lat": coords["lat"]}
            sc["coord_addr"] = coords["addr"]
            sc["coord_source"] = coords["source"]
            print(f"  + {sc['name']}  <-  {coords['poi_name']}  ({coords['lng']},{coords['lat']})  {coords['addr']}")
            unmatched_out.append({"name": sc["name"], "district": sc["district"], "coord_added": True})
        else:
            print(f"  ! {sc['name']}  未查到可信坐标")
            unmatched_out.append({"name": sc["name"], "district": sc["district"], "coord_added": False})

    # 重新序列化并写出 tier1.js（含补充坐标）
    js = "/* 由 scripts/build_middle_tier1_js.py 生成，勿手改 */\nwindow.GZ_MIDDLE_TIER1 = " + json.dumps(out, ensure_ascii=False, indent=1) + ";\n"
    OUT.write_text(js, encoding="utf-8")
    n_coords = sum(1 for s in schools if "coords" in s)
    print(f"\nwritten: {OUT}  ({len(schools)} schools, {n_coords} with coords)")
    if cache:
        COORDS_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\ncoords cache: {COORDS_CACHE}  ({len(cache)} entries)")

    UNMATCHED_OUT.write_text(json.dumps(unmatched_out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"unmatched list: {UNMATCHED_OUT}  ({len(unmatched_out)} schools, {sum(1 for x in unmatched_out if not x['coord_added'])} 无坐标)")


if __name__ == "__main__":
    main()
