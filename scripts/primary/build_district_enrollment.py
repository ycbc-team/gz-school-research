#!/usr/bin/env python3
"""构建广州五区（荔湾/越秀/海珠/天河/番禺）小学招生离线数据库（统一脚本）。

数据源:
  越秀: 新生登记范围 txt（招生简章附件5 doc 转文本）
  荔湾: 官方附件1招生计划 docx + 附件4服务地段划分表 docx
  海珠: data/primary/enrollments/_raw/haizhu_2026.json（官网图片 OCR 转录）
  天河: data/primary/enrollments/_raw/tianhe_2026.json（官方 PDF 附件5 OCR 转录）
  番禺: 番禺区教育局 2026 招生计划 xls（公办+民办两个 sheet）

用法: python3 scripts/primary/build_district_enrollment.py <区名:yuexiu|liwan|haizhu|tianhe|panyu> [越秀txt路径]
      或 python3 scripts/primary/build_district_enrollment.py all
输出: data/primary/enrollments/2026-<区>.json（唯一真源）
"""
import json
import os
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "primary")
OUT_DIR = os.path.join(DATA, "enrollments")
TMP = "/tmp/gzsrc"

NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

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
    # 转录差异：raw sheets 读作「番禺区中学」，官方 xls/实体为「番禺中学」——归一绑定防 rank 漂移
    "广东番禺区中学教育集团兴南学校": "广东番禺中学教育集团兴南学校",
    # 2024 更名：文昌小学并入蒋光鼐纪念小学教育集团（新快网2025-03；xiaoshengchu 同名映射），挂本体文昌小学
    "广州市荔湾区蒋光鼐纪念小学文昌学校": "广州市荔湾区文昌小学",
    # 海鸥学校（九年制，海鸥岛沙北村）小学部 POI 名「沙北小学」（xiaoshengchu 同名映射）
    "石楼镇海鸥学校": "沙北小学",
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
    "智谷第一实验学校小学部": "天河区智谷第一实验学校",
    "广州市荔湾区蒋光鼐纪念小学三元坊学校": "三元坊小学",
    "广州市荔湾区华侨小学汇龙学校": "汇龙小学",
    "石碁镇茂生小学": "茂生纪念学校",
    # 校区名差异（政府文件短名 vs 高德 POI 全名）——人工确认：
    # 宝玉直实验小学（南边校区）地段=南石头街庄头/棣园社区 ↔ POI「南边路校区」同址；
    # 逸景第一小学（逸景校区）地段=凤阳街逸景东/西社区 ↔ POI「本校区」= 逸景第一小学本部
    "宝玉直实验小学（南边校区）": "广州市海珠区宝玉直实验小学(南边路校区)",
    "逸景第一小学（逸景校区）": "逸景第一小学(本校区)",
    # 2026-09-18 高德核实补录（官方名与 POI 名不一致）：
    #   化龙镇复甦小学：招复甦村，高德 POI「复苏小学」（复苏路38号）——与化龙镇中心小学（招东南村等7村居）为两所独立学校，
    #     2026 官方计划双列；化龙镇中心小学搬迁去向未定（用户资料截断），保持缺口（宁可缺失）
    #   新桥小学：大龙街新桥村市莲路桥东大街2号，高德 POI「新桥学校」（市莲路153旁）
    #   石碁镇永善小学：石碁镇永善村义里上街4号，高德 POI「永善学校」（义里上街4号）
    "化龙镇复甦小学": "复苏小学",
    "新桥小学": "新桥学校",
    "石碁镇永善小学": "永善学校",
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

# 统一匹配库：norm 本体（NFKC/繁简/去广州市/删括号/去空白）收敛至 school_match.normName；
# 区名/镇/小学校等输入清洗保留在本地（各区官方表特有前缀）
sys.path.insert(0, os.path.join(ROOT, "data/registry/entity/scripts"))
from school_match import normName as _normName, fold_unicode as _fold


def norm_school(n):
    n = _normName(_fold(n))  # fold=NFKC+繁简（采集输入清洗），norm 本体统一
    for d in ("越秀区", "荔湾区", "海珠区", "天河区", "番禺区", "黄埔区", "白云区"):
        n = n.replace(d, "")
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
    # TXT 缺失时回退 _raw/yuexiu_2026.json（转录产物），保证本地可重跑
    if not os.path.exists(txt_path):
        raw = json.load(open(os.path.join(OUT_DIR, "_raw", "yuexiu_2026.json"), encoding="utf-8"))
        return [{
            "school": s["school"], "district": "越秀区",
            "plan_classes": s.get("plan_classes"), "zone": s.get("zone", ""),
            "note": s.get("note", ""), "phone": s.get("phone", ""),
            "source": "越秀区教育局2026",
        } for s in raw["schools"]]
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
            "school": school, "district": "越秀区",
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
    # 附件4 服务地段划分表: 学校/街道/社区/路名（学校列空=上一所学校地段的延续行，街道列空则继承上一条）
    zones = {}
    cur = None
    last_street = ""
    for row in docx_tables(os.path.join(TMP, "liw_4_服务地段划分表.docx"))[0]:
        if len(row) < 4:
            continue
        school, street, comm, addr = row[0], row[1], row[2], row[3]
        if school and school != "学校":
            cur = school
        if street:
            last_street = street
        if not cur:
            continue
        if not (street or comm or addr):
            continue
        line_street = street or last_street
        zones.setdefault(cur, []).append(f"{line_street}·{comm}：{addr}" if comm else f"{line_street}：{addr}")
    records = []
    for school in plan:
        records.append({
            "school": school, "district": "荔湾区",
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
            "plan_classes": s.get("plan_classes"),
            "zone": s.get("zone", ""), "note": s.get("note", ""),
            "phone": s.get("phone", ""),
            "source": "海珠区教育局2026" if district_key == "haizhu" else "天河区教育局2026",
        })
    return records

# ---------- 番禺 ----------
def parse_panyu(xls_path):
    if os.path.exists(xls_path):
        import xlrd
        wb = xlrd.open_workbook(xls_path)
        sheets = {s.name: [[sh.cell_value(r, c) for c in range(sh.ncols)] for r in range(sh.nrows)]
                  for sh in wb.sheets()}
    else:
        # xls 缺失时复用 _raw 解析产物（同构：sheets 二维数组），保证本地可重跑
        raw = json.load(open(os.path.join(OUT_DIR, "_raw", "panyu_2026_official.json"), encoding="utf-8"))
        sheets = raw["sheets"]
    records = []
    sh = sheets.get("公办小学招生地段、计划", [])
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
        records.append({
            "school": school, "district": district,
            "plan_classes": int(plan) if isinstance(plan, float) and plan == int(plan) else (plan if isinstance(plan, (int, float)) else None),
            "zone": zone, "note": note, "source": "番禺区教育局2026",
        })
    sh2 = sheets.get("民办招生计划", [])
    district2 = ""
    for r in range(5, len(sh2)):
        d = str(sh2[r][0]).strip()
        if d:
            district2 = d.replace("\n", "")
        school = str(sh2[r][1]).strip()
        if not school:
            continue
        classes = sh2[r][2]
        persons = sh2[r][3]
        note = str(sh2[r][6]).strip()
        records.append({
            "school": school, "district": district2,
            "plan_classes": int(classes) if isinstance(classes, float) and classes == int(classes) else (classes if isinstance(classes, (int, float)) else None),
            "plan_count": int(persons) if isinstance(persons, float) and persons == int(persons) else (persons if isinstance(persons, (int, float)) else None),
            "zone": "民办：无地段，报名人数超计划电脑派位（摇号）",
            "note": note, "source": "番禺区教育局2026",
        })
    return records

def load_unified_matcher():
    """统一校名匹配库（school_match.SchoolMatcher）：POI 三学段 + 实体表。供各区 build 脚本复用。"""
    sys.path.insert(0, os.path.join(ROOT, "scripts", "registry"))
    from school_match import SchoolMatcher
    return SchoolMatcher.load(
        poi_paths=[(os.path.join(ROOT, "data", "poi", "dist", "primary_poi.json"), "小学"),
                   (os.path.join(ROOT, "data", "poi", "dist", "middle_poi.json"), "初中"),
                   (os.path.join(ROOT, "data", "poi", "dist", "high_poi.json"), "高中")],
        entities_path=os.path.join(ROOT, "data", "registry", "entities.json"))


def resolve_fallback(matcher, school, adcode, poi_pool, stage="小学"):
    """统一匹配库兜底（自定义规则覆盖不到：小学部括号、校区短名 vs POI 全名等）。
    三重防护 → 拒绝返回 None（宁可缺失、不跨区错配）：
      ① 跨学段（非目标 stage，如星悦实验学校实体仅初中部）；
      ② 跨区（sid 不在本区 POI 池，如桂花岗小学实体误标白云）；
      ③ 校区名冲突（开元学校(西校区) 不可挂东校区实体）。"""
    r = matcher.resolve(school, preferred_adcode=adcode, preferred_stage=stage)
    sid = r.get("school_id") if r else None
    if not sid:
        return None
    if r.get("stage") and r.get("stage") != stage:
        return None
    poi = next((p for p in poi_pool if p.get("school_id") == sid), None)
    if not poi:
        return None
    oc = re.findall(r"[（(]([^）()]*?校区)[)）]", school)
    mc = re.findall(r"[（(]([^）()]*?校区)[)）]", r.get("matched_name") or "")
    if oc and mc and oc[0] != mc[0]:
        return None
    return poi


def match_and_write(district_key, records, source, source_url):
    # 数据真源为 data/poi/dist/primary_poi.json（JSON 唯一真源）
    with open(os.path.join(ROOT, "data", "poi", "dist", "primary_poi.json"), encoding="utf-8") as f:
        data = json.load(f)
    poi_pool = [s for s in data.get("schools", []) if s.get("adcode") == DISTRICTS[district_key]["adcode"]]
    # 排除泛名/在建类 POI（如「学校」「建设中」）
    BAD_POI = ("建设中", "在建", "工地", "装修", "筹备", "规划", "选址")
    poi_pool = [s for s in poi_pool if len(s["name"]) > 2 and not any(b in s["name"] for b in BAD_POI)]

    _matcher = load_unified_matcher()

    # 历史锚定基线（data/primary/enrollments/_anchors.json）：HEAD 各区 records 的
    # 「政府文件校名 → 实体 school_id」人工修正映射。重跑时锚定优先于一切规则，
    # 防止「省实荔湾第一小学部」「万松园小学」「康有为校本部」等历史修正被规则漂移覆盖。
    _anchors = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_anchors.json"), encoding="utf-8"))

    bindings = []  # (score, rec_idx, poi)
    map_fail = []
    for idx, rec in enumerate(records):
        # 0. 历史锚定优先（1200，最高）：HEAD 人工修正映射不可被规则覆盖
        _anchor_sid = _anchors.get(rec["school"])
        if _anchor_sid:
            _apoi = next((p for p in poi_pool if p.get("school_id") == _anchor_sid), None)
            if _apoi:
                bindings.append((1200, idx, _apoi))
                continue
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
            continue
        # 自定义规则未命中 → 统一匹配库兜底（区上下文 + 小学学段）
        poi = resolve_fallback(_matcher, rec["school"], DISTRICTS[district_key]["adcode"], poi_pool)
        if poi:
            bindings.append((1050, idx, poi))  # 统一匹配库兜底（低于 NAME_MAP/自定义规则）
        # 拒绝（跨区/跨学段/校区冲突）→ 保持 unmatched，供报告与人工核查
    bindings.sort(key=lambda x: -x[0])

    matched, ambiguous, used = [], [], {}
    for score, idx, poi in bindings:
        if poi["name"] in used:
            ambiguous.append({"school": records[idx]["school"], "poi": poi["name"],
                              "compete_with": used[poi["name"]]})
            continue
        used[poi["name"]] = records[idx]["school"]
        rec = dict(records[idx])
        # 事实表直接引用实体主键；不能以同名 POI 作临时键，否则跨区同名学校会在后续回填时错配。
        rec["school_id"] = poi.get("school_id")
        rec["poi_name"] = poi["name"]
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
    with open(os.path.join(OUT_DIR, f"2026-{district_key}.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

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
