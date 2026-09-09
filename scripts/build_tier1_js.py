#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 data/tier1_schools_all.json 生成浏览器可加载的 data/tier1.js（window.GZ_TIER1）。

为每所学校生成：
  - 支撑信号摘要（出口机制、教育集团、2026班数、学位预警、省一级称号）
  - 校名匹配别名（供地图点位匹配，含校区/旧称变体）

用法：python3 scripts/build_tier1_js.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "tier1_schools_all.json"
OUT = ROOT / "data" / "tier1.js"

# 手工补充的匹配别名（tier1 规范名 -> 额外别名，用于校区/旧称/惯用简称）
ALIAS_EXTRA = {
    "广州协和学校（小学部，原广州市协和小学）": ["广州协和学校", "协和学校", "协和小学"],
    "广州市越秀区东风东路小学": ["东风东路小学"],
    "广州市越秀区文德路小学": ["文德路小学"],
    "广州市越秀区东山培正小学": ["东山培正小学", "培正小学"],
    "广州市越秀区小北路小学": ["小北路小学"],
    "广州市越秀区农林下路小学": ["农林下路小学"],
    "广州市越秀区铁一小学": ["铁一小学"],
    "广州市荔湾区乐贤坊小学": ["乐贤坊小学"],
    "广州市荔湾区沙面小学": ["沙面小学"],
    "广州市荔湾区康有为纪念小学": ["康有为纪念小学"],
    "广州市海珠区实验小学（穗花校区/富基校区）": ["海珠区实验小学", "广州市海珠区实验小学"],
    "广州市海珠区同福中路第一小学": ["同福中路第一小学", "海珠区同福中路第一小学"],
    "广州市海珠区宝玉直小学": ["宝玉直小学"],
    "广州市海珠区昌岗中路小学": ["昌岗中路小学"],
    "广州市天河区华阳小学": ["华阳小学", "天河区华阳小学"],
    "广州市天河区华景小学": ["华景小学"],
    "广州市天河区龙口西小学": ["龙口西小学"],
    "广州市天河区天府路小学": ["天府路小学", "天河区天府路小学"],
    "广州市天河区体育东路小学（含兴国学校、海明学校）": [
        "体育东路小学", "体育东路小学兴国学校", "体育东路小学海明学校",
    ],
    "广州市白云区京溪小学": ["京溪小学"],
    "广州市白云区景泰小学": ["景泰小学"],
    "广州市白云区广园小学": ["广园小学"],
    "广州市白云区黄边小学": ["黄边小学"],
    "广州市白云区三元里小学": ["三元里小学"],
    "广州市白云区华师附中实验小学": ["华师附中实验小学", "白云区华师附中实验小学"],
    "广州市白云区同和小学": ["同和小学"],
    "广州市白云区握山小学": ["握山小学"],
    "广州市白云区明德小学": ["明德小学"],
    "广州市白云区人和镇第二小学": ["人和镇第二小学"],
    "广州市白云区江村小学": ["江村小学"],
    "广州市白云区太和第一小学（校本部/和龙校区）": ["太和第一小学"],
    "广州市黄埔区怡园小学（东、西、北校区）": ["怡园小学"],
    "广州市黄埔区荔园小学": ["荔园小学"],
    "广州市黄埔区港湾小学": ["港湾小学"],
    "广州市黄埔区下沙小学": ["下沙小学"],
    "广州市黄埔区文冲小学": ["文冲小学"],
    "广州市黄埔区广州石化小学（东、西校区）": ["广州石化小学"],
    "广州市黄埔区东荟花园小学（东、南、北校区）": ["东荟花园小学"],
    "广州市黄埔区玉泉学校（小学部）": ["玉泉学校"],
    "广州市黄埔区黄埔军校小学（暂借怡园小学西校区办学）": ["黄埔军校小学"],
    "广州市番禺区市桥中心小学": ["市桥中心小学"],
    "广州市番禺区市桥东城小学": ["市桥东城小学"],
    "广州市番禺区市桥南阳里小学": ["市桥南阳里小学", "南阳里小学"],
    "广州市番禺区市桥德兴小学": ["市桥德兴小学", "德兴小学"],
    "广州市番禺区市桥实验小学": ["市桥实验小学"],
    "广州市番禺区石碁镇中心小学": ["石碁镇中心小学"],
    "广州市番禺区石楼镇中心小学": ["石楼镇中心小学"],
    "广州市番禺区南村镇中心小学": ["南村镇中心小学"],
    "广州市番禺区洛溪新城小学": ["洛溪新城小学"],
    "广东番禺中学附属学校（小学部）": ["广东番禺中学附属学校", "番禺中学附属学校", "番中附小"],
    "广东仲元中学附属学校（小学部）": ["广东仲元中学附属学校", "仲元中学附属学校"],
    "白云区民航学校（校本部·小学部）": ["白云区民航学校", "民航学校", "白云区民航学校小学部"],
    "广州市黄埔区沙步小学": ["沙步小学", "黄埔区沙步小学"],
}

# 高德 POI 无主点位、经 Amap Web API（v3/place/text）补充坐标的学校
# 坐标系 GCJ-02，与地图瓦片（高德）一致；source 记录取点来源
EXTRA_COORDS = {
    "广州协和学校（小学部，原广州市协和小学）": {
        "lng": 113.241217, "lat": 23.144465,
        "addr": "荔湾区西村街道西湾路93号",
        "source": "高德POI：广州协和学校（typecode 141200）",
    },
    "广州市黄埔区沙步小学": {
        "lng": 113.534107, "lat": 23.083552,
        "addr": "黄埔区南岗街道沙步社区（校门西南门点位）",
        "source": "高德POI：广东省广州市黄埔区沙步小学(西南门)（无主POI，取校门点位）",
    },
    "广州市番禺区市桥东城小学": {
        "lng": 113.373635, "lat": 22.933305,
        "addr": "番禺区市桥街德祥路21号",
        "source": "高德POI：东城小学（typecode 141203）",
    },
}

DISTRICTS = ["越秀区", "荔湾区", "海珠区", "天河区", "白云区", "黄埔区", "番禺区"]

# 过短的通用别名（去区名后只剩通用后缀），禁止作为前缀匹配键，避免误配
GENERIC_SHORT = {
    "实验小学", "中心小学", "附属小学", "实验学校", "附属学校",
    "第一小学", "第二小学", "第三小学", "第四小学", "第五小学",
    "第六小学", "第七小学", "第八小学", "小学", "学校",
}


def strip_parenthesis(name: str) -> str:
    return re.sub(r"[（(].*?[)）]", "", name).strip()


def norm_short(name: str) -> str:
    """去 广州市 前缀 + 去括号 + 去区名，用于宽松匹配。"""
    n = str(name).replace("广州市", "")
    n = strip_parenthesis(n)
    for d in DISTRICTS:
        n = n.replace(d, "")
    return n.strip()


def xiaoshengchu_str(s: dict) -> str:
    x = s.get("xiaoshengchu") or {}
    if not x:
        return "未查到"
    parts = []
    if x.get("direct_feed"):
        parts.append("直升：" + x["direct_feed"])
    if x.get("group"):
        g = "派位" + x["group"]
        fh = x.get("feed_junior_highs") or []
        if fh:
            shown = "、".join(fh[:4]) + ("等" if len(fh) > 4 else "")
            g += "（含" + shown + "）"
        parts.append(g)
    return "；".join(parts) if parts else "未查到"


def education_group_str(s: dict) -> str:
    g = s.get("education_group") or {}
    if not g or not g.get("name"):
        return "未查到"
    name = g["name"]
    role = g.get("role")
    return name + (f"（{role}）" if role and role != "未查到" else "")


def provincial_str(s: dict) -> str:
    p = s.get("provincial_level_title") or {}
    if not p or not p.get("year"):
        return "无"
    return f"{p['year']}年评定省一级"


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    schools = []
    for dist, meta in data["districts"].items():
        for s in meta["schools"]:
            aliases = []
            base = strip_parenthesis(s["name"]).replace("广州市", "")
            aliases.append(base)
            short = norm_short(s["name"])
            if short and short != base and len(short) >= 4 and short not in GENERIC_SHORT:
                aliases.append(short)
            for extra in ALIAS_EXTRA.get(s["name"], []):
                if extra not in aliases:
                    aliases.append(extra)
            rec = {
                "name": s["name"],
                "district": dist,
                "verdict": s.get("conclusion", ""),
                "rumor_tier": s.get("rumor_tier", "第一梯队"),
                "rumor_notes": (s.get("rumor_notes") or "")[:120],
                "conclusion_basis": s.get("conclusion_basis", ""),
                "signals": {
                    "xiaoshengchu": xiaoshengchu_str(s),
                    "education_group": education_group_str(s),
                    "plan_classes_2026": s.get("plan_classes_2026"),
                    "degree_warning": s.get("degree_warning", "未查到"),
                    "provincial_level_title": provincial_str(s),
                },
                "aliases": aliases,
            }
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
    js = "/* 由 scripts/build_tier1_js.py 生成，勿手改 */\nwindow.GZ_TIER1 = " + json.dumps(out, ensure_ascii=False, indent=1) + ";\n"
    OUT.write_text(js, encoding="utf-8")
    print(f"written: {OUT}  ({len(schools)} schools)")

    # ---- 匹配模拟验证：与地图页同算法（仅用 tier1.js 中预生成别名，无二次短化） ----
    src = (ROOT / "data" / "schools.js").read_text(encoding="utf-8")
    m = re.search(r"window\.GZ_SCHOOLS\s*=\s*(\{.*?\});?\s*$", src, re.S)
    poi_data = json.loads(m.group(1))
    poi_names = [x["name"] for x in poi_data["schools"]]

    def norm_poi(n: str) -> str:
        n = str(n).replace("广州市", "")
        return strip_parenthesis(n).strip()

    table = []  # (norm_alias, school_name)
    for sc in schools:
        for a in sc["aliases"]:
            na = norm_poi(a)
            if na not in [t[0] for t in table]:
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
        sn = match(norm_poi(p))
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


if __name__ == "__main__":
    main()
