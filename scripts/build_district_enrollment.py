#!/usr/bin/env python3
"""构建广州五区（荔湾/越秀/海珠/天河/番禺）小学招生离线数据库（统一脚本）。

数据源:
  越秀: 新生登记范围 txt（招生简章附件5 doc 转文本）
  荔湾: 官方附件1招生计划 docx + 附件4服务地段划分表 docx
  海珠: data/primary/enrollments/_raw/haizhu_2026.json（官网图片 OCR 转录）
  天河: data/primary/enrollments/_raw/tianhe_2026.json（官方 PDF 附件5 OCR 转录）
  番禺: 番禺区教育局 2026 招生计划 xls（公办+民办两个 sheet）

用法: python3 scripts/build_district_enrollment.py <区名:yuexiu|liwan|haizhu|tianhe|panyu> [越秀txt路径]
      或 python3 scripts/build_district_enrollment.py all
输出: data/primary/enrollments/2026-<区>.json + .js
"""
import json
import os
import re
import sys
import unicodedata
import zipfile
from xml.etree import ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "primary")
OUT_DIR = os.path.join(DATA, "enrollments")
TMP = "/tmp/gzsrc"

NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

VARIANTS = {"穂": "穗", "敎": "教", "學": "学", "朮": "术", "甦": "苏"}
CAMPUS_WORDS = ["东校区", "西校区", "南校区", "北校区", "大龙校区", "首开校区",
                "新校区", "校区", "校本部"]
GENERIC_TAILS = ("中心小学", "第二小学", "第一小学", "第三小学", "第四小学",
                 "第五小学", "实验小学", "实验学校", "附小")
# 番禺镇街前缀 + 教育集团前缀：官方名单带「市桥/石碁/…」镇街前缀或「XX教育集团」集团前缀，POI 一般不带
PREFIXES = ["市桥", "钟村", "石壁", "大石", "洛浦", "南村", "化龙", "新造",
            "小谷围街", "石楼", "石碁", "沙湾", "桥南", "东环", "沙头",
            "华阳教育集团", "体育东路教育集团", "广州华阳集团", "华阳集团", "广东番禺中学教育集团"]

# 名称映射表（官方名 → 高德 POI 名）：同一学校、通用规则匹配不到的别名/托管/集团校名
# 依据：校名前缀关系（真光中学附属/第四中学附属/教育集团等托管更名）、用户确认（养正小学=王圣堂温浩根养正学校，均广园西路78号）、
#       校区名一致（小北校区=小北路校区）、POI 为该校小学部/招生处（星执、智谷第一实验学校）
NAME_MAP = {
    "养正小学": "王圣堂温浩根养正学校",
    "华侨外国语学校（小学部）": "广州市华侨外国语学校-华侨小学",
    "回民小学": "广州市回民小学北校区",
    "小北路小学（小北校区）": "小北路小学(小北路校区)",
    "广州市真光中学附属坑口小学": "广州市坑口小学",
    "广州市真光中学附属西塱小学": "西塱小学",
    "广州市真光中学附属鹤洞小学": "鹤洞小学",
    "广州市第四中学附属耀华小学": "耀华小学",
    "广东番禺中学教育集团培兰小学": "培兰小学",
    "蚬涌俊贤小学": "市桥实验小学蚬涌俊贤学校",
    "华阳教育集团新塘小学": "新塘小学",
    "中国教育科学研究院荔湾实验学校（小学部）": "中国教育科学研究院荔湾实验学校小学部",
    "广州市星执学校": "广州市星执学校小学招生处",
    "智谷第一实验学校小学部": "天河区智谷第一实验学校",
    "广州市荔湾区蒋光鼐纪念小学三元坊学校": "三元坊小学",
    "广州市荔湾区华侨小学汇龙学校": "汇龙小学",
    "石碁镇茂生小学": "茂生纪念学校",
}

DISTRICTS = {
    "yuexiu": {"name": "越秀区", "adcode": "440104", "zone_field": "zone"},
    "liwan": {"name": "荔湾区", "adcode": "440103", "zone_field": "zone"},
    "haizhu": {"name": "海珠区", "adcode": "440105", "zone_field": "zone"},
    "tianhe": {"name": "天河区", "adcode": "440106", "zone_field": "zone"},
    "panyu": {"name": "番禺区", "adcode": "440113", "zone_field": "zone"},
}

def is_generic(s):
    return any(s == g or s.endswith(g) for g in GENERIC_TAILS)

def strip_prefix(n):
    for p in PREFIXES:
        if n.startswith(p):
            return n[len(p):]
    return n

def norm_school(n):
    n = unicodedata.normalize("NFKC", str(n))
    n = n.replace("广州市", "")
    for d in ("越秀区", "荔湾区", "海珠区", "天河区", "番禺区", "黄埔区", "白云区"):
        n = n.replace(d, "")
    for a, b in VARIANTS.items():
        n = n.replace(a, b)
    n = n.replace("小学校", "小学")
    n = n.replace("镇", "")
    n = n.strip()
    return n

def strip_paren(n):
    return re.sub(r"[（(][^）()]*[)）]", "", n).strip()

def extract_campus(n):
    m = re.search(r"[（(]([^（）()]*?校区)[)）]", n)
    return m.group(1) if m else None

def same_campus(a, b):
    if not a or not b:
        return False
    return a == b or a in b or b in a

def ratio_ok(short, long):
    """包含类匹配防护：短侧需占长侧 ≥ 60%，防「养正小学」误配「王圣堂温浩根养正学校」"""
    return len(short) * 5 >= len(long) * 3

def is_campus(n):
    return bool(extract_campus(n)) or any(w in n for w in CAMPUS_WORDS)

def rank_candidates(rec_school, poi_list):
    """与番禺版一致的保守匹配规则 + 校区名一致性约束。

    校区规则：
      - 官方记录含校区名 → 只匹配 POI 中校区名相同者（不同校区互斥，不抢本部 POI）
      - 官方记录不含校区名 → 可匹配本部 POI（优先）或校区 POI（降档）
    """
    nx = norm_school(rec_school)
    nxc = strip_paren(nx)
    rc = extract_campus(rec_school)
    out = []
    for p in poi_list:
        pn = norm_school(p["name"])
        pnc = strip_paren(pn)
        pc = extract_campus(p["name"])
        if rc and pc and not same_campus(rc, pc):
            continue
        score = 0
        tag = ""
        if not rc and pc:
            # 本部记录 vs 校区 POI：降档
            if nx == pn or nxc == pnc:
                score, tag = 700, "本部-校区全名"
            elif nx in pn or pn in nx or nxc in pnc or pnc in nxc:
                score, tag = 550, "本部-校区包含"
        elif rc and not pc:
            # 校区记录 vs 本部 POI：若 POI 名包含官方校区名（如官方「锦城校区」vs POI「…锦城花园校区」）按同校区高匹配
            if rc in pn or pn in rc:
                if nxc == pnc:
                    score, tag = 900, "校区名内含"
                elif (len(nxc) >= 3 and nxc in pnc) or (len(pnc) >= 3 and pnc in nxc):
                    score, tag = 700, "校区名内含-核心包含"
            else:
                if nxc == pn:
                    score, tag = 650, "校区-本部核心名"
                elif (len(nxc) >= 3 and nxc in pn) or (len(pn) >= 3 and pn in nxc):
                    score, tag = 500, "校区-本部包含"
        else:
            nxsp = strip_prefix(nx)
            nxspc = strip_prefix(nxc)
            pnsp = strip_prefix(pn)
            pnspc = strip_prefix(pnc)
            nxc_eq = nxc.replace("学校", "小学")
            nxspc_eq = nxspc.replace("学校", "小学")
            pnc_eq = pnc.replace("学校", "小学")
            pnspc_eq = pnspc.replace("学校", "小学")
            if nx == pn:
                score, tag = 1000, "全名"
            elif rc and pc and (nxspc == pnspc or (len(nxspc) >= 3 and nxspc in pnspc and ratio_ok(nxspc, pnspc))):
                score, tag = 750, "校区-校区核心"
            elif nxsp == pn or nxspc == pnc:
                score, tag = 950, "官方前缀strip"
            elif nx == pnsp or nxc == pnspc:
                score, tag = 900, "POI前缀strip"
            elif nxc == pnc:
                score, tag = 900, "去括号等价"
            elif nxspc_eq == pnc or nxc_eq == pnspc_eq:
                score, tag = 850, "词尾等价"
            elif nx in pn or pn in nx:
                short, long = (nx, pn) if len(nx) <= len(pn) else (pn, nx)
                if not is_generic(short) and ratio_ok(short, long):
                    score, tag = 600 + min(len(nx), len(pn)), "互相包含"
            elif (len(nxspc) >= 3 and nxspc in pnc and not is_generic(nxspc) and ratio_ok(nxspc, pnc)) or \
                 (len(pnspc) >= 3 and pnspc in nxspc and not is_generic(pnspc) and ratio_ok(pnspc, nxspc)):
                score, tag = 500 + min(len(nxspc), len(pnspc)), "核心包含"
            elif (len(nxspc_eq) >= 3 and nxspc_eq in pnc_eq and not is_generic(nxspc_eq) and ratio_ok(nxspc_eq, pnc_eq)) or \
                 (len(pnspc_eq) >= 3 and pnspc_eq in nxspc_eq and not is_generic(pnspc_eq) and ratio_ok(pnspc_eq, nxspc_eq)):
                score, tag = 450 + min(len(nxspc_eq), len(pnspc_eq)), "词尾等价包含"
        if score <= 0:
            continue
        out.append((score, tag, p))
    out.sort(key=lambda x: -x[0])
    return out

# ---------- 越秀 ----------
def parse_yuexiu(txt_path):
    with open(txt_path, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    blocks = []  # (school, lines[])
    cur = None
    for l in lines:
        # 标题：可选（编号）半/全角括号 + 学校名 + 一年级新生登记范围
        m = re.match(r"^(?:[（(]\s*\d+\s*[)）]\s*)?(.+?一年级新生登记范围)\s*$", l)
        if m and "新生登记范围" in m.group(1):
            title = m.group(1)
            school = title.replace("2026年", "").replace("广州市", "").replace("越秀区", "")
            school = re.sub(r"一年级新生登记范围\s*$", "", school).strip()
            if school:
                cur = {"school": school, "lines": []}
                blocks.append(cur)
                continue
        if cur is not None:
            cur["lines"].append(l)
    # 合并同校多块 + 提取班数
    merged = {}
    for b in blocks:
        key = b["school"]
        if key not in merged:
            merged[key] = {"classes": None, "parts": []}
        text = "\n".join(b["lines"])
        m = re.search(r"计划招生\s*(\d+)\s*个班", text)
        if m:
            merged[key]["classes"] = int(m.group(1))
        parts = [x for x in b["lines"] if x and x not in ("行政街", "范 围", "范围") and not x.startswith("说明")]
        merged[key]["parts"].append("\n".join(parts))
    records = []
    for school, v in merged.items():
        zone = "\n".join(p for p in v["parts"] if p.strip())
        records.append({
            "school": school, "district": "越秀区", "nature": "公办",
            "plan_classes": v["classes"],
            "zone": zone, "note": "", "source": "越秀区教育局2026",
        })
    return records

# ---------- 荔湾 ----------
def docx_paragraphs(path):
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    return ["".join(t.text or "" for t in p.iter(NS + "t")).strip()
            for p in root.iter(NS + "p") if "".join(t.text or "" for t in p.iter(NS + "t")).strip()]

def docx_tables(path):
    """返回 [[[cell_text...], ...rows], ...tables]"""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    tables = []
    for tbl in root.iter(NS + "tbl"):
        rows = []
        for tr in tbl.iter(NS + "tr"):
            cells = []
            for tc in tr.iter(NS + "tc"):
                txt = "".join(t.text or "" for p in tc.iter(NS + "p") for t in p.iter(NS + "t")).strip()
                cells.append(txt)
            if any(cells):
                rows.append(cells)
        tables.append(rows)
    return tables

def parse_liwan():
    # 附件1 招生计划: 序号/学校/班数
    plan = {}
    for row in docx_tables(os.path.join(TMP, "liw_1_招生计划.docx"))[0]:
        if len(row) >= 3 and row[1] and row[1] != "学校":
            m = re.match(r"^(\d+)$", row[0])
            if m:
                school = row[1]
                cls = row[2]
                plan[school] = int(cls) if cls.isdigit() else None
    # 附件4 服务地段划分表: 学校/街道/社区/路名
    zones = {}
    for row in docx_tables(os.path.join(TMP, "liw_4_服务地段划分表.docx"))[0]:
        if len(row) >= 4 and row[0] and row[0] != "学校":
            school, street, comm, addr = row[0], row[1], row[2], row[3]
            zones.setdefault(school, []).append(f"{street}·{comm}：{addr}" if comm else f"{street}：{addr}")
    records = []
    for school in plan:
        records.append({
            "school": school, "district": "荔湾区", "nature": "公办",
            "plan_classes": plan[school],
            "zone": "\n".join(zones.get(school, [])) or "",
            "note": "", "source": "荔湾区教育局2026",
        })
    return records

# ---------- 海珠/天河（OCR 转录） ----------
def parse_raw(district_key):
    raw = json.load(open(os.path.join(OUT_DIR, "_raw", f"{district_key}_2026.json"), encoding="utf-8"))
    records = []
    for s in raw["schools"]:
        records.append({
            "school": s["school"], "district": DISTRICTS[district_key]["name"],
            "nature": "公办",
            "plan_classes": s.get("plan_classes"),
            "zone": s.get("zone", ""), "note": s.get("note", ""),
            "phone": s.get("phone", ""),
            "source": "海珠区教育局2026" if district_key == "haizhu" else "天河区教育局2026",
        })
    return records

# ---------- 番禺 ----------
def parse_panyu(xls_path):
    import xlrd
    wb = xlrd.open_workbook(xls_path)
    records = []
    sh = wb.sheet_by_name("公办小学招生地段、计划")
    district = ""
    for r in range(3, sh.nrows):
        d = str(sh.cell_value(r, 0)).strip()
        if d:
            district = d.replace("\n", "")
        school = str(sh.cell_value(r, 1)).strip()
        if not school:
            continue
        plan = sh.cell_value(r, 2)
        zone = str(sh.cell_value(r, 3)).strip()
        note = str(sh.cell_value(r, 4)).strip()
        records.append({
            "school": school, "district": district, "nature": "公办",
            "plan_classes": int(plan) if isinstance(plan, float) and plan == int(plan) else (plan if isinstance(plan, (int, float)) else None),
            "zone": zone, "note": note, "source": "番禺区教育局2026",
        })
    sh2 = wb.sheet_by_name("民办招生计划")
    district2 = ""
    for r in range(5, sh2.nrows):
        d = str(sh2.cell_value(r, 0)).strip()
        if d:
            district2 = d.replace("\n", "")
        school = str(sh2.cell_value(r, 1)).strip()
        if not school:
            continue
        classes = sh2.cell_value(r, 2)
        persons = sh2.cell_value(r, 3)
        note = str(sh2.cell_value(r, 6)).strip()
        records.append({
            "school": school, "district": district2, "nature": "民办",
            "plan_classes": int(classes) if isinstance(classes, float) and classes == int(classes) else (classes if isinstance(classes, (int, float)) else None),
            "plan_count": int(persons) if isinstance(persons, float) and persons == int(persons) else (persons if isinstance(persons, (int, float)) else None),
            "zone": "民办：无地段，报名人数超计划电脑派位（摇号）",
            "note": note, "source": "番禺区教育局2026",
        })
    return records

def match_and_write(district_key, records, source, source_url):
    js = open(os.path.join(DATA, "schools.js"), encoding="utf-8").read()
    m = re.search(r"window\.GZ_SCHOOLS\s*=\s*(\{.*?\});?\s*$", js, re.S)
    data = json.loads(m.group(1))
    poi_pool = [s for s in data.get("schools", []) if s.get("adcode") == DISTRICTS[district_key]["adcode"]]
    # 排除泛名/在建类 POI（如「学校」「建设中」）
    BAD_POI = ("建设中", "在建", "工地", "装修", "筹备", "规划", "选址")
    poi_pool = [s for s in poi_pool if len(s["name"]) > 2 and not any(b in s["name"] for b in BAD_POI)]

    bindings = []  # (score, rec_idx, poi)
    map_fail = []
    for idx, rec in enumerate(records):
        mapped = NAME_MAP.get(rec["school"])
        if mapped:
            poi = next((p for p in poi_pool if p["name"] == mapped), None)
            if poi:
                bindings.append((1100, idx, poi))  # 映射绑定，优先于通用匹配
            else:
                map_fail.append(rec["school"])
            continue
        cands = rank_candidates(rec["school"], poi_pool)
        if cands:
            bindings.append((cands[0][0], idx, cands[0][2]))
    bindings.sort(key=lambda x: -x[0])

    matched, ambiguous, used = [], [], {}
    for score, idx, poi in bindings:
        if poi["name"] in used:
            ambiguous.append({"school": records[idx]["school"], "poi": poi["name"],
                              "compete_with": used[poi["name"]]})
            continue
        used[poi["name"]] = records[idx]["school"]
        rec = dict(records[idx])
        rec["school_id"] = poi["name"]
        rec["lng"], rec["lat"] = poi["lng"], poi["lat"]
        matched.append(rec)

    poi_leftover = [s["name"] for s in poi_pool if s["name"] not in used]
    matched_names = {r["school"] for r in matched}
    unmatched = [r["school"] for r in records if r["school"] not in matched_names]

    result = {
        "year": 2026, "district": DISTRICTS[district_key]["name"],
        "source": source, "source_url": source_url,
        "records": matched, "unmatched": sorted(set(unmatched)),
        "ambiguous": ambiguous, "poi_leftover": sorted(set(poi_leftover)),
        "map_fail": sorted(set(map_fail)),
    }
    var = f"GZ_ENROLL_{district_key.upper()}"
    with open(os.path.join(OUT_DIR, f"2026-{district_key}.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DIR, f"2026-{district_key}.js"), "w", encoding="utf-8") as f:
        f.write(f"window.{var} = ")
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    print(f"[{DISTRICTS[district_key]['name']}] 官方记录 {len(records)} | 匹配 {len(matched)} / 未匹配 {len(unmatched)} / 歧义 {len(ambiguous)} / POI无记录 {len(poi_leftover)}")
    if unmatched:
        print("  未匹配:", sorted(set(unmatched)))
    if ambiguous:
        print("  歧义:", ambiguous)
    return result

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    jobs = ["yuexiu", "liwan", "haizhu", "tianhe", "panyu"] if target == "all" else [target]
    for dk in jobs:
        if dk == "yuexiu":
            txt = sys.argv[2] if len(sys.argv) > 2 else os.path.join(TMP, "yuexiu_5_新生登记范围.txt")
            recs = parse_yuexiu(txt)
            match_and_write(dk, recs,
                "越秀区教育局《2026年越秀区小学新生登记范围》（招生简章附件5）",
                "http://www.yuexiu.gov.cn/gzjg/qzf/qjyj/jyzl/gk/zxjyxx/content/post_10790024.html")
        elif dk == "liwan":
            recs = parse_liwan()
            match_and_write(dk, recs,
                "荔湾区教育局《2026年广州市荔湾区公办小学一年级招生工作方案》附件1招生计划、附件4服务地段划分表",
                "https://www.lw.gov.cn/zwgkk/zdlyxxgk/ggqsy/qsydwxxgs/jyxx/content/post_10791703.html")
        elif dk == "panyu":
            xls = sys.argv[2] if len(sys.argv) > 2 else "/Users/bytedance/Downloads/panyu_2026.xls"
            recs = parse_panyu(xls)
            match_and_write(dk, recs,
                "番禺区教育局《2026年番禺区义务教育阶段学校招生计划、招生地段及条件》",
                "https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10794/mpost_10794083.html")
        elif dk in ("haizhu", "tianhe"):
            recs = parse_raw(dk)
            src = "海珠区教育局《2026年海珠区公办小学招生服务地段表》" if dk == "haizhu" else \
                  "天河区教育局《2026年天河区公办小学招生地段及招生计划表》（附件5）"
            url = "https://www.haizhu.gov.cn/gzhzjy/gkmlpt/content/10/10788/mpost_10788561.html" if dk == "haizhu" else \
                  "http://www.thnet.gov.cn/attachment/8/8016/8016210/10791180.pdf"
            match_and_write(dk, recs, src, url)

if __name__ == "__main__":
    main()
