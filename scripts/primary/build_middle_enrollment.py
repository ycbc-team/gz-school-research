#!/usr/bin/env python3
"""构建 2026 各区公办初中招生计划离线库（初中视角）。

输出: data/primary/enrollments/middle_enrollment_2026_<district>.json

数据源（按区）:
  番禺 panyu : _raw/panyu_2026_official.json "公办初中招生范围、计划" sheet
  白云 baiyun: _raw/baiyun_2026_juniors.json
  荔湾 liwan : _raw/liwan_2026_groups.json（派位组）
  越秀/海珠/天河/黄埔: xiaoshengchu_<district>.json 反推（班数/范围 raw 未抽，留空）

mechanism 枚举（区级定义，UI 据此渲染）:
  single_zone     单校划片（对口直升/直接安排，无落选概念）
  group_paidui    多校电脑派位（组内学校兜底，不安排到组外）
  single_lottery  单校电脑抽签（自愿报名+超额抽签，未中签回原学区）
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "primary", "enrollments", "_raw")
OUT = os.path.join(ROOT, "data", "primary", "enrollments")

# 复用项目统一的 POI 匹配管道（实体表别名优先，不另起 norm 逻辑）
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from match_poi import load_poi as _load_poi_all, load_aliases as _load_aliases, match_school as _match_school

_POI_ALL = (
    _load_poi_all(os.path.join(ROOT, "data/primary/schools-gz.json"), "小学")
    + _load_poi_all(os.path.join(ROOT, "data/middle/schools-gz.json"), "初中")
    + _load_poi_all(os.path.join(ROOT, "data/high/schools-gz.json"), "高中")
)
_ALIAS_MAP = _load_aliases(os.path.join(ROOT, "data/registry/entities.json"))

def match_school_id(name):
    """官方名单校名 → POI school_id；未命中返回 None。统一走 match_poi 管道（实体表别名优先）。"""
    if not name: return None
    r = _match_school(name, _POI_ALL, _ALIAS_MAP)
    return r.get("school_id") or None

# 区级枚举定义：UI 直接用 label / lose_text
MECHANISMS = {
    "single_zone":    {"label": "单校划片",     "can_lose": False, "lose_text": None},
    "group_paidui":   {"label": "多校电脑派位", "can_lose": False, "lose_text": "派位组内学校随机分配，组内兜底，不安排到组外。"},
    "single_lottery": {"label": "单校电脑抽签", "can_lose": True,  "lose_text": "符合报名条件 ≠ 一定录取。报名人数超计划时由区教育局统一组织电脑抽签；未中签者按区招生简章回户籍地学区申请入读公办初中，不保证安排到本校。"},
}

# ---------- 番禺 ----------
def build_panyu():
    d = json.load(open(os.path.join(RAW, "panyu_2026_official.json")))
    rows = d["sheets"]["公办初中招生范围、计划"]
    src_url = d["source"]
    recs = []
    group_tail = ""  # 学区列空则沿用上一行
    for r in rows[3:]:  # 跳表头3行
        school = (r[1] or "").strip()
        if not school or school.startswith("说明"): continue
        plan = r[2]
        scope = (r[3] or "").strip()
        note = (r[4] or "").strip()
        try:
            plan_n = int(float(plan)) if plan else None
        except: plan_n = None

        if "电脑抽签" in note:
            mech = "single_lottery"
        elif "电脑派位" in note:
            mech = "group_paidui"
        else:
            mech = "single_zone"

        # 亚运城派位组成员从备注提取
        members = None
        if mech == "group_paidui" and "铁英" in note:
            members = ["广铁一中番禺校区", "广铁一中铁英学校(西校区)", "广铁一中铁英学校(东校区)"]
        # 市桥城区多校派位组（番实验+其他7校）
        if mech == "group_paidui" and school == "番禺区实验中学":
            members = ["广东仲元中学一校区（初中部）","广东番禺中学附属学校","番禺区实验中学","市桥东风中学","市桥侨联中学","市桥星海中学","市桥桥城中学","市桥桥兴中学"]

        sid = match_school_id(school)
        recs.append({
            "school": school, "school_id": sid,
            "plan_classes": plan_n, "scope": scope,
            "mechanism": mech, "mechanism_note": note or None,
            "group_members": members,
        })
    return {
        "year": 2026, "district": "番禺区",
        "source": "番禺区教育局《2026年番禺区义务教育阶段学校招生计划、招生地段及条件》+《2026年番禺区区属初中面向全区招生简章》",
        "source_url": src_url,
        "mechanisms": MECHANISMS,
        "records": recs,
    }

# ---------- 白云 ----------
def build_baiyun():
    raw = json.load(open(os.path.join(RAW, "baiyun_2026_juniors.json")))
    recs = []
    for r in raw:
        school = (r.get("school") or "").strip()
        if not school: continue
        try: plan_n = int(r.get("plan")) if r.get("plan") else None
        except: plan_n = None
        feed = (r.get("feed") or "").strip()
        note = (r.get("note") or "").strip()
        # 机制判断
        if "摇号" in feed or "摇号" in note:
            mech = "group_paidui"
        elif feed.count("、") >= 2 or feed.count(",") >= 2:
            mech = "group_paidui"
        else:
            mech = "single_zone"
        sid = match_school_id(school)
        recs.append({
            "school": school, "school_id": sid,
            "plan_classes": plan_n, "scope": feed or None,
            "mechanism": mech, "mechanism_note": note or None,
            "group_members": None,
        })
    return {
        "year": 2026, "district": "白云区",
        "source": "白云区教育局 2026 公办初中招生计划（_raw/baiyun_2026_juniors.json）",
        "source_url": None,
        "mechanisms": MECHANISMS,
        "records": recs,
    }

# ---------- 荔湾（从派位组） ----------
def build_liwan():
    raw = json.load(open(os.path.join(RAW, "liwan_2026_groups.json")))
    rec_map = {}  # school -> rec
    for g in raw:
        cells = g.get("cells", [])
        if len(cells) < 3: continue
        group_name = cells[0][0] if cells[0] else ""
        if not re.match(r"^\d+组$", group_name): continue
        middle_col = cells[1] if len(cells) > 1 else []
        # cells[1] 是 list[str]，每个中学一个元素
        members = [s.strip() for s in middle_col if s.strip()]
        for m in members:
            if m not in rec_map:
                rec_map[m] = {"school": m, "school_id": None, "plan_classes": None,
                              "scope": None, "mechanism": "group_paidui",
                              "mechanism_note": f"荔湾区{group_name}电脑派位",
                              "group_members": members}
            else:
                # 同一初中可能在多组（如真光本部在多个组），保留成员列表并集
                rec_map[m]["group_members"] = list(set(rec_map[m]["group_members"] or []) | set(members))
    recs = []
    for m, r in rec_map.items():
        r["school_id"] = match_school_id(m)
        recs.append(r)
    return {
        "year": 2026, "district": "荔湾区",
        "source": "荔湾区教育局 2026 公办初中招生派位组表（_raw/liwan_2026_groups.json）",
        "source_url": None,
        "mechanisms": MECHANISMS,
        "records": recs,
    }

# ---------- 从 xiaoshengchu 反推（越秀/海珠/天河/黄埔） ----------
def build_from_xiaoshengchu(district_key, district_name, adcode):
    xs = json.load(open(os.path.join(OUT, f"xiaoshengchu_{district_key}.json")))
    # 初中名 -> 记录
    rec_map = {}
    # 派位组：group 名 -> 成员初中列表
    group_members_map = {}
    for r in xs["records"]:
        group = r.get("group") or ""
        juniors = r.get("feed_junior_highs") or []
        if not juniors: continue
        for j in juniors:
            if j not in rec_map:
                rec_map[j] = {"school": j, "school_id": None, "plan_classes": None,
                              "scope": None, "mechanism": None,
                              "mechanism_note": None, "group_members": None}
            # 机制判定：先排除"不参加电脑派位"，再判派位/直升
            if "不参加" in group or "不参与" in group:
                continue
            elif "对口直升" in group or "单校" in group or "九年制" in group or "内部直升" in group:
                mech = "single_zone"
            elif "电脑派位" in group or "多校" in group:
                mech = "group_paidui"
            else:
                mech = "group_paidui"
            # 同一初中在多个小学记录里出现，取最严格机制（single_lottery > group_paidui > single_zone）
            order = {"single_zone":1, "group_paidui":2, "single_lottery":3}
            cur = rec_map[j]["mechanism"]
            if cur is None or order.get(mech,0) > order.get(cur,0):
                rec_map[j]["mechanism"] = mech
                rec_map[j]["mechanism_note"] = group
            # 组内成员：同一 group 名下的所有初中
            if mech == "group_paidui":
                group_members_map.setdefault(group, set()).add(j)
    # 回填 group_members；mechanism 为 None 的（"不参加电脑派位"记录里的初中）默认 single_zone
    for j, rec in rec_map.items():
        if rec["mechanism"] is None:
            rec["mechanism"] = "single_zone"
            rec["mechanism_note"] = "对口直升（不参加电脑派位）"
        if rec["mechanism"] == "group_paidui" and rec["mechanism_note"]:
            rec["group_members"] = sorted(group_members_map.get(rec["mechanism_note"], set()))
    recs = []
    for j, r in rec_map.items():
        r["school_id"] = match_school_id(j)
        recs.append(r)
    return {
        "year": 2026, "district": district_name,
        "source": f"由 xiaoshengchu_{district_key}.json 反推（班数/范围 raw 未抽，待补）",
        "source_url": None,
        "mechanisms": MECHANISMS,
        "records": recs,
    }

BUILDERS = {
    "panyu": build_panyu,
    "baiyun": build_baiyun,
    "liwan": build_liwan,
    "yuexiu": lambda: build_from_xiaoshengchu("yuexiu", "越秀区", "440104"),
    "haizhu": lambda: build_from_xiaoshengchu("haizhu", "海珠区", "440105"),
    "tianhe": lambda: build_from_xiaoshengchu("tianhe", "天河区", "440106"),
    "huangpu": lambda: build_from_xiaoshengchu("huangpu", "黄埔区", "440112"),
}

if __name__ == "__main__":
    targets = sys.argv[1:] or list(BUILDERS.keys())
    for dk in targets:
        data = BUILDERS[dk]()
        out = os.path.join(OUT, f"middle_enrollment_2026_{dk}.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        # 统计
        total = len(data["records"])
        matched = sum(1 for r in data["records"] if r["school_id"])
        mech_count = {}
        for r in data["records"]:
            mech_count[r["mechanism"]] = mech_count.get(r["mechanism"],0)+1
        print(f"{dk:8s} -> {out}")
        print(f"         总{total}所, POI匹配{matched}, 机制分布: {mech_count}")
