#!/usr/bin/env python3
"""统一构建 7 区小学招生 dist/2026-<区>.json（B 层，全新方式）。

数据源：parsed/_transcripts/*.json（A 层转录，复现脚本见 parse_*）
匹配：registry/entity 统一 SchoolMatcher（实体表 school_id + 别名机制 + 区/学段收敛 + 去括号）。
      业务侧不再维护 _anchors/NAME_MAP 等手工映射表（2026-09-21 用户定：手工匹配可能出错，
      映射问题一律到实体表别名层解决；此处只做 SchoolMatcher 解析 + POI 定位 + 校区冲突防护）。
输出：dist/2026-<区>.json（最终运行时产物，与旧版格式一致：
      year/district/source/source_url/records/unmatched/ambiguous/poi_leftover/map_fail，
      另含 minban 段（民办小学招生计划：班数/人数，无地段；当前仅番禺官方文件公布民办计划）。
      parsed/ 只保留 A 层转录 _transcripts/（解析层）。
用法：python3 data/primary/enrollment/scripts/build_primary_2026.py <区:yuexiu|liwan|haizhu|tianhe|panyu|baiyun|huangpu|all>
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
TRANSCRIPTS = os.path.join(ROOT, "data", "primary", "enrollment", "parsed", "_transcripts")
OUT_DIR = os.path.join(ROOT, "data", "primary", "enrollment", "dist")

sys.path.insert(0, os.path.join(ROOT, "data", "registry", "entity", "scripts"))
from school_match import SchoolMatcher  # noqa: E402

ADCODES = {
    "yuexiu": "440104", "liwan": "440103", "haizhu": "440105", "tianhe": "440106",
    "panyu": "440113", "baiyun": "440111", "huangpu": "440112",
}
DISTRICT_NAMES = {
    "yuexiu": "越秀区", "liwan": "荔湾区", "haizhu": "海珠区", "tianhe": "天河区",
    "panyu": "番禺区", "baiyun": "白云区", "huangpu": "黄埔区",
}
SOURCE_URLS = {
    "yuexiu": "http://www.yuexiu.gov.cn/gzjg/qzf/qjyj/jyzl/gk/zxjyxx/content/post_10790024.html",
    "liwan": "http://www.lw.gov.cn/zwgkk/zdlyxxgk/jyxx/xxjy/content/post_10791702.html",
    "haizhu": "https://www.haizhu.gov.cn/gzhzjy/gkmlpt/content/10/10788/mpost_10788561.html",
    "tianhe": "http://www.thnet.gov.cn/attachment/8/8016/8016210/10791180.pdf",
    "panyu": "https://www.panyu.gov.cn/jgzy/qzfbm/fzqjyj/jyjgkml/qt/tzgg/content/post_10794082.html",
    "baiyun": "https://www.by.gov.cn/zwfw/zdfw/xwsq/zcwj/content/post_10791741.html",
    "huangpu": "https://www.hp.gov.cn/hpqgzkfqzdlyzl/jyxx/zsks/content/post_10792533.html",
}


def load_matcher():
    return SchoolMatcher.load(
        poi_paths=[(os.path.join(ROOT, "data", "poi", "dist", "primary_poi.json"), "小学"),
                   (os.path.join(ROOT, "data", "poi", "dist", "middle_poi.json"), "初中"),
                   (os.path.join(ROOT, "data", "poi", "dist", "high_poi.json"), "高中")],
        entities_path=os.path.join(ROOT, "data", "registry", "entity", "dist", "entities.json"))


def _poi_for(matcher, school, adcode, poi_pool, r):
    """SchoolMatcher 匹配结果 → 本区 POI 定位 → 校区冲突防护。返回 poi 或 None。"""
    sid = r.get("school_id") if r else None
    if not sid:
        return None
    if r.get("stage") and r.get("stage") not in ("小学", "primary"):
        return None
    poi = next((p for p in poi_pool if p.get("school_id") == sid), None)
    if not poi:
        return None
    # 校区冲突防护仅约束 substring 吸附（变体命中）：「如意坊校区」不得挂「西关培正小学」本部、
    # 「岭南湾畔校区」不得挂「东风西校区」。别名命中（PRIMARY_CAMPUS_ALIAS 显式挂载，如
    # 「南边校区」→「南边路校区」「逸景校区」→「本校区」）信任挂载，不做括号名比较。
    if r.get("poi_match") == "变体命中":
        oc = re.findall(r"[（(]([^）()]*?校区)[)）]", school)
        mc = re.findall(r"[（(]([^）()]*?校区)[)）]", r.get("matched_name") or "")
        # 带「校区」输入必须命中带校区实体（如「汇景实验学校（华园校区）小学部」不得挂
        # 「汇景实验学校（小学部）」）；「岭南湾畔校区」不得挂「东风西校区」
        if oc and not mc:
            return None
        if oc and mc and not (oc[0] in mc[0] or mc[0] in oc[0]):
            return None
    return poi


def resolve_records(matcher, school, adcode, poi_pool):
    """实体表匹配：带校区名 → resolve 单值；无校区名 → resolve_all 展开同法人全部校区
    （用户定：铁英中学等法人多校区应展开为多条校区记录，不再锚定单校区）。"""
    has_campus = bool(re.search(r"[（(][^）()]*[)）]", school))
    if not has_campus:
        rs = matcher.resolve_all(school, preferred_adcode=adcode, preferred_stage="小学")
        pois = [_poi_for(matcher, school, adcode, poi_pool, r) for r in rs]
        return [poi for poi in pois if poi]
    r = matcher.resolve(school, preferred_adcode=adcode, preferred_stage="小学")
    poi = _poi_for(matcher, school, adcode, poi_pool, r)
    return [poi] if poi else []


# ---------- 各区 transcripts → records ----------
def _norm_plan(plan):
    """班数归一：str 数字（openpyxl/xlrd 常读成 str）/ float / int → int；空/非数字 → None"""
    if isinstance(plan, bool) or plan is None:
        return None
    if isinstance(plan, float):
        return int(plan) if plan == int(plan) else None
    if isinstance(plan, int):
        return plan
    if isinstance(plan, str):
        t = plan.strip()
        return int(t) if t.isdigit() else None
    return None


def rec(school, district, plan=None, zone="", note="", phone=""):
    return {"school": school, "district": district, "plan_classes": _norm_plan(plan),
            "zone": zone, "note": note, "phone": phone, "source": f"{district}教育局2026"}


def load_records(district_key):
    dk = district_key
    if dk in ("yuexiu", "haizhu", "tianhe", "huangpu", "liwan", "baiyun"):
        t = json.load(open(os.path.join(TRANSCRIPTS, f"{dk}_2026.json"), encoding="utf-8"))
        out = []
        for s in t["schools"]:
            out.append(rec(s.get("school", ""), DISTRICT_NAMES[dk],
                           s.get("plan_classes"), s.get("zone", ""), s.get("note", ""), s.get("phone", "")))
        return out, t.get("source", f"{DISTRICT_NAMES[dk]}教育局2026")
    if dk == "panyu":
        t = json.load(open(os.path.join(TRANSCRIPTS, "panyu_2026_official.json"), encoding="utf-8"))
        sheets = t["sheets"]
        sh = sheets.get("公办小学招生地段、计划", [])
        out = []
        district = ""
        for r in range(3, len(sh)):
            d = str(sh[r][0]).strip()
            if d:
                district = d.replace("\n", "")
            school = str(sh[r][1]).strip()
            if not school:
                continue
            plan = sh[r][2]
            zone = str(sh[r][3]).strip()
            note = str(sh[r][4]).strip()
            out.append(rec(school, district, plan, zone, note))
        return out, t.get("title", "番禺区教育局2026")
    raise KeyError(dk)


def load_minban(district_key):
    """民办小学招生计划（当前仅番禺官方文件含民办招生计划 sheet）。
    民办不划地段（报名超计划摇号），故只取 班数/人数 计划 + 实体匹配，不进公办 records。
    """
    if district_key != "panyu":
        return []
    t = json.load(open(os.path.join(TRANSCRIPTS, "panyu_2026_official.json"), encoding="utf-8"))
    rows = t["sheets"].get("民办招生计划", [])
    head_i = next((i for i, r in enumerate(rows) if len(r) > 1 and "学校名称" in str(r[1])), None)
    if head_i is None:
        return []
    data = [r for r in rows[head_i + 2:] if len(r) >= 6 and str(r[1]).strip()]
    matcher = load_matcher()
    with open(os.path.join(ROOT, "data", "poi", "dist", "primary_poi.json"), encoding="utf-8") as f:
        poi_pool = [s for s in json.load(f).get("schools", []) if s.get("adcode") == ADCODES[district_key]]
    out, unresolved = [], []
    for r in data:
        name = str(r[1]).strip()
        plan_cls = str(r[2]).strip()
        plan_cnt = str(r[3]).strip()
        if plan_cls in ("", "/", "0"):
            continue  # 无小学计划（仅初中）→ 归初中招生，不进小学产物
        ent = matcher.resolve(name, preferred_adcode=ADCODES[district_key], preferred_stage="小学") \
            or matcher.resolve(name, preferred_adcode=ADCODES[district_key])
        if not ent:
            unresolved.append(name)
            continue
        rec = {"school": name, "district": str(r[0]).strip().replace("\n", ""),
               "plan_classes": int(plan_cls) if plan_cls.isdigit() else None,
               "plan_count": int(plan_cnt) if plan_cnt.isdigit() else None,
               "school_id": ent.get("school_id"), "poi_name": ent.get("matched_name", ""),
               "lng": ent.get("lng"), "lat": ent.get("lat")}
        out.append(rec)
    if unresolved:
        print(f"  [民办未匹配] {len(unresolved)}: {unresolved}")
    return out


def build(district_key):
    records, source = load_records(district_key)
    adcode = ADCODES[district_key]
    with open(os.path.join(ROOT, "data", "poi", "dist", "primary_poi.json"), encoding="utf-8") as f:
        poi_data = json.load(f)
    poi_pool = [s for s in poi_data.get("schools", []) if s.get("adcode") == adcode]
    BAD = ("建设中", "在建", "工地", "装修", "筹备", "规划", "选址")
    poi_pool = [s for s in poi_pool if len(s["name"]) > 2 and not any(b in s["name"] for b in BAD)]

    matcher = load_matcher()
    matched, ambiguous, used = [], [], {}
    has_campus = lambda s: bool(re.search(r"[（(][^）()]*校区[)）]", s))
    # 第一遍：带校区记录（如「龙归学校（珑璟校区）」）先 resolve 占位，
    # 本部记录（「龙归学校」）展开时不得重复占同一校区 POI
    explicit_pois = {}
    for r0 in records:
        if not has_campus(r0["school"]):
            continue
        pois = resolve_records(matcher, r0["school"], adcode, poi_pool)
        if pois:
            explicit_pois[pois[0]["name"]] = r0["school"]
    for idx, r0 in enumerate(records):
        pois = resolve_records(matcher, r0["school"], adcode, poi_pool)
        if not pois:
            continue
        for poi in pois:
            if poi["name"] in used:
                ambiguous.append({"school": r0["school"], "poi": poi["name"], "compete_with": used[poi["name"]]})
                continue
            if not has_campus(r0["school"]) and poi["name"] in explicit_pois:
                continue  # 本部记录展开跳过已显式列出的分校区
            used[poi["name"]] = r0["school"]
            r = dict(r0)
            r["school_id"] = poi.get("school_id")
            r["poi_name"] = poi["name"]
            r["lng"], r["lat"] = poi["lng"], poi["lat"]
            matched.append(r)

    matched_names = {r["school"] for r in matched}
    unmatched = [r["school"] for r in records if r["school"] not in matched_names]
    poi_leftover = [s["name"] for s in poi_pool if s["name"] not in used]
    result = {
        "year": 2026, "district": DISTRICT_NAMES[district_key],
        "source": source, "source_url": SOURCE_URLS[district_key],
        "records": matched, "unmatched": sorted(set(unmatched)),
        "ambiguous": ambiguous, "poi_leftover": sorted(set(poi_leftover)), "map_fail": [],
        "minban": load_minban(district_key),
    }
    with open(os.path.join(OUT_DIR, f"2026-{district_key}.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"[{DISTRICT_NAMES[district_key]}] 官方记录 {len(records)} | 匹配 {len(matched)} / 未匹配 {len(unmatched)} / 歧义 {len(ambiguous)} / POI无记录 {len(poi_leftover)}")
    if unmatched:
        print("  未匹配:", sorted(set(unmatched)))
    if ambiguous:
        print("  歧义:", ambiguous)
    return result


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    keys = list(ADCODES) if target == "all" else [target]
    for k in keys:
        if k not in ADCODES:
            print("未知区。可选:", list(ADCODES), "或 all")
            sys.exit(1)
        build(k)
