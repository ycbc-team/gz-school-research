#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 parsed/*.json + dist/specialty_schools.json 生成最终交付 xlsx。
三个 sheet：认定明细 / 学校汇总 / 数据说明。
"""
import json, glob
from pathlib import Path
from collections import Counter
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[3]
SPECIALTY = Path(__file__).resolve().parent.parent
PARSED = SPECIALTY / "parsed"
DIST = SPECIALTY / "dist"
OUT = ROOT / "outputs" / "广州特色校认定汇总_20260920.xlsx"

# ── 样式 ──
HEADER_FILL = PatternFill("solid", fgColor="2F5496")
HEADER_FONT = Font(name="微软雅黑", bold=True, color="FFFFFF", size=11)
CELL_FONT = Font(name="微软雅黑", size=10)
TITLE_FONT = Font(name="微软雅黑", bold=True, size=14, color="2F5496")
SECTION_FONT = Font(name="微软雅黑", bold=True, size=11, color="2F5496")
THIN_BORDER = Border(
    left=Side(style="thin", color="D9D9D9"),
    right=Side(style="thin", color="D9D9D9"),
    top=Side(style="thin", color="D9D9D9"),
    bottom=Side(style="thin", color="D9D9D9"),
)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)

LEVEL_COLORS = {
    "国家级": PatternFill("solid", fgColor="FCE4D6"),
    "省级": PatternFill("solid", fgColor="D6E4F0"),
    "市级": PatternFill("solid", fgColor="E2EFDA"),
}


def load_all_records():
    records = []
    for p in sorted(PARSED.glob("*.json")):
        doc = json.loads(p.read_text("utf-8"))
        for r in doc.get("records", []):
            records.append(r)
    return records


def style_header(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = THIN_BORDER


def auto_width(ws, max_width=50):
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value:
                # Chinese chars count as 2
                length = sum(2 if ord(c) > 127 else 1 for c in str(cell.value))
                max_len = max(max_len, min(length, max_width))
        ws.column_dimensions[col_letter].width = max(max_len + 2, 8)


def build_detail_sheet(wb, records):
    ws = wb.create_sheet("认定明细")
    headers = ["学校名称", "所在区", "类别", "级别", "批次", "认定年份",
               "认定项目全称", "发文单位", "官方来源URL", "备注"]
    ws.append(headers)
    style_header(ws, 1, len(headers))

    # Sort by level, category, district, school
    level_order = {"国家级": 0, "省级": 1, "市级": 2}
    records_sorted = sorted(records, key=lambda r: (
        level_order.get(r.get("level", ""), 9),
        r.get("category", ""),
        r.get("district", ""),
        r.get("school", ""),
    ))

    for i, r in enumerate(records_sorted, 2):
        ws.append([
            r.get("school", ""),
            r.get("district", ""),
            r.get("category", ""),
            r.get("level", ""),
            r.get("batch", ""),
            r.get("year", ""),
            r.get("project", ""),
            r.get("issuer", ""),
            r.get("url", ""),
            r.get("remark", ""),
        ])
        # Color level cell
        level = r.get("level", "")
        if level in LEVEL_COLORS:
            ws.cell(row=i, column=4).fill = LEVEL_COLORS[level]
        for c in range(1, len(headers) + 1):
            ws.cell(row=i, column=c).font = CELL_FONT
            ws.cell(row=i, column=c).border = THIN_BORDER
            ws.cell(row=i, column=c).alignment = WRAP

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(records_sorted)+1}"
    auto_width(ws)
    # URL column wider
    ws.column_dimensions["I"].width = 55
    ws.column_dimensions["J"].width = 40
    return ws


def build_school_summary_sheet(wb):
    dist = json.loads((DIST / "specialty_schools.json").read_text("utf-8"))
    ws = wb.create_sheet("学校汇总")
    headers = ["学校名称", "所在区", "school_id", "匹配状态", "认定数",
               "认定类别", "认定级别", "最早年份", "最近年份"]
    ws.append(headers)
    style_header(ws, 1, len(headers))

    schools = sorted(dist["schools"], key=lambda s: (
        0 if s["school_ids"] else 1,
        s["school"],
    ))

    DISTRICT_MAP = {"440103":"荔湾区","440104":"越秀区","440105":"海珠区","440106":"天河区",
                    "440111":"白云区","440112":"黄埔区","440113":"番禺区","440114":"花都区",
                    "440115":"南沙区","440117":"从化区","440118":"增城区"}

    for i, s in enumerate(schools, 2):
        recs = s.get("recognitions", [])
        cats = sorted(set(r.get("category", "") for r in recs))
        levels = sorted(set(r.get("level", "") for r in recs))
        years = [int(r["year"]) for r in recs if str(r.get("year", "")).isdigit()]
        # Try to get district from first recognition
        district = ""
        for r in recs:
            if r.get("remark", "").find("区") >= 0:
                pass
        # Get district from school_id adcode if matched
        if s["school_ids"]:
            sid = s["school_ids"][0]
            adcode = sid.split("-")[1] if "-" in sid else ""
            district = DISTRICT_MAP.get(adcode, "")

        ws.append([
            s["school"],
            district,
            ", ".join(s["school_ids"]) if s["school_ids"] else "",
            "已匹配" if s["school_ids"] else "未匹配",
            len(recs),
            "、".join(cats),
            "、".join(levels),
            min(years) if years else "",
            max(years) if years else "",
        ])
        if not s["school_ids"]:
            ws.cell(row=i, column=4).fill = PatternFill("solid", fgColor="FCE4D6")
        for c in range(1, len(headers) + 1):
            ws.cell(row=i, column=c).font = CELL_FONT
            ws.cell(row=i, column=c).border = THIN_BORDER
            ws.cell(row=i, column=c).alignment = WRAP

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(schools)+1}"
    auto_width(ws)
    return ws


def build_doc_sheet(wb, records):
    ws = wb.create_sheet("数据说明")
    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 80

    row = 1
    def write_title(text):
        nonlocal row
        ws.cell(row=row, column=1, value=text).font = TITLE_FONT
        row += 1

    def write_section(text):
        nonlocal row
        ws.cell(row=row, column=1, value=text).font = SECTION_FONT
        row += 1

    def write_kv(k, v):
        nonlocal row
        ws.cell(row=row, column=1, value=k).font = Font(name="微软雅黑", bold=True, size=10)
        ws.cell(row=row, column=1).alignment = WRAP
        c = ws.cell(row=row, column=2, value=v)
        c.font = CELL_FONT
        c.alignment = WRAP
        row += 1

    def write_blank():
        nonlocal row
        row += 1

    dist = json.loads((DIST / "specialty_schools.json").read_text("utf-8"))
    summary = dist["summary"]

    write_title("广州市各级特色校认定数据汇总 — 数据说明")
    write_blank()

    write_section("一、数据概览")
    write_kv("数据截止", "2026-09-20")
    write_kv("认定记录总数", f"{summary['total_records']} 条（同一学校多类别/级别认定保留多行，不合并去重）")
    write_kv("涉及学校总数", f"{summary['total_schools']} 所")
    write_kv("已匹配 school_id", f"{summary['matched_schools']} 所（{summary['matched_schools']/summary['total_schools']*100:.1f}%）")
    write_kv("未匹配学校", f"{summary['unmatched_schools']} 所（详见下方缺口分析）")
    write_blank()

    write_section("二、覆盖类别与级别")
    cat_counts = Counter(r.get("category", "") for r in records)
    level_counts = Counter(r.get("level", "") for r in records)
    write_kv("按类别", "；".join(f"{k} {v}条" for k, v in cat_counts.most_common()))
    write_kv("按级别", "；".join(f"{k} {v}条" for k, v in level_counts.most_common()))
    write_blank()

    write_section("三、数据来源（均为官方公开通知/附件）")
    sources = [
        ("广东省教育厅 (edu.gd.gov.cn)", "首批/第三批/第四批/第五批广东省中小学艺术教育特色学校；首批/第二批/第三批中华优秀传统文化传承学校；2026年广东省普通高中多样化特色发展改革试点培育对象（科学高中）；首批广东省中小学科学教育示范区/示范校/实验校"),
        ("广州市教育局 (jyj.gz.gov.cn)", "第五/六/七批广州市中小学心理健康教育特色学校；首批广州市中小学学科美育教学改革试点项目校；广东省青少年校园冰雪体育传统特色学校名单"),
        ("教育部 (moe.gov.cn)", "全国青少年校园足球特色学校（2015/2023/2024/2025批次）；全国青少年校园篮球特色学校（2017首批）；首批全国中小学科学教育实验校（2024）"),
    ]
    for k, v in sources:
        write_kv(k, v)
    write_blank()

    write_section("四、缺口与未匹配分析")
    write_kv("未匹配学校总数", f"{summary['unmatched_schools']} 所（去重后约142所）")
    write_kv("远郊区POI覆盖缺口", "约123所（花都/南沙/增城/从化的小学/初中POI数据基本未覆盖：小学POI中远郊区0所，初中各仅1所）")
    write_kv("职业/师范学校", "约10所（城市建设职校、财经商贸职校、交通运输职校、轻工职业学校、信息技术职业学校、白云行知职校、从化职校、幼儿师范学校等，POI层仅覆盖中小学）")
    write_kv("特殊教育/体校", "约2所（启聪学校、净慧体校）")
    write_kv("中心区POI遗漏", "约5所（美术中学、第四十四中学、工业大道中小学等）")
    write_kv("民办/新办学校", "约4所（广外附设外语学校、湖南师大黄埔实验学校等）")
    write_blank()

    write_section("五、已修复的匹配问题")
    write_kv("写法差异", "广州市八十六中学 → 已添加alias至实体广州市第八十六中学（gz-440112-0cb5a402）")
    write_kv("区属标注错误", "广州市协和中学/协和小学（原标白云区→修正为荔湾区，匹配广州协和学校 gz-440103-e281e7d0）")
    write_kv("区属标注错误", "广州市启明学校（原标越秀区→修正为白云区，匹配启明小学 gz-440111-2abc753d）")
    write_blank()

    write_section("六、待补充批次")
    write_kv("省级艺术教育第二批", "2018年11月公布，官方PDF未获取到，约涉及广州10+所")
    write_kv("市级心理健康第一至四批", "约2015-2019年间公布，官网历史归档未公开可查")
    write_kv("国家级校园足球2016-2022批次", "广州累计371所，本次仅覆盖2015/2023/2024/2025四批约176所（47%）")
    write_kv("国家级体育传统特色学校", "广州435所，完整名单文件未找到")
    write_kv("省级/市级体育传统项目学校", "完整名单附件未找到")
    write_kv("市级科学教育特色学校", "广州计划至2026年创建100所，首批正式名单尚未公示")
    write_blank()

    write_section("七、字段说明")
    write_kv("学校名称", "官方名单原文校名")
    write_kv("所在区", "官方名单标注区；市属/无法推断的标注'区推断'或'区未知'")
    write_kv("类别", "美育/艺术教育、中华优秀传统文化传承、心理健康教育、科技创新/科学教育、体育-校园足球、体育-篮球、体育-冰雪体育等")
    write_kv("级别", "国家级/省级/市级")
    write_kv("批次/年份", "官方认定批次与发文年份")
    write_kv("认定项目全称", "官方文件中的认定项目完整名称")
    write_kv("发文单位", "发布认定通知的官方机构")
    write_kv("官方来源URL", "可追溯的官方通知/附件链接")
    write_kv("备注", "区推断说明、未匹配registry原因、区属修正记录等")

    return ws


def main():
    records = load_all_records()
    print(f"加载 {len(records)} 条认定记录")

    wb = Workbook()
    wb.remove(wb.active)  # remove default sheet

    build_detail_sheet(wb, records)
    build_school_summary_sheet(wb)
    build_doc_sheet(wb, records)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(OUT))
    print(f"已生成: {OUT}")
    print(f"  Sheet: 认定明细 ({len(records)}行)")
    dist = json.loads((DIST / "specialty_schools.json").read_text("utf-8"))
    print(f"  Sheet: 学校汇总 ({len(dist['schools'])}行)")
    print(f"  Sheet: 数据说明")


if __name__ == "__main__":
    main()
