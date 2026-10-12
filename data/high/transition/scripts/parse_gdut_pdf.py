#!/usr/bin/env python3
"""
广工 2024 本科录取名单 → 各中学录取人数统计

输入: raw/gdut_2024_enrollment.pdf（广工招办官方 PDF，2024-08-29）
输出: dist/gdut_2024_school_counts.json
      {"all": [[学校名, 人数], ...], "guangzhou": [[广州学校, 人数], ...]}

排版结构（v4 解析，2026-10-12）:
- PDF 为三列布局：学校名列(x≈88-180)、人数列(x≈208)、录取名单列(x≈239)。
- 名单列是纯姓名（顿号分隔），解析时整列忽略。
- 学校名可能跨 y 拆段：前半段(不完整) → 人数 → 补全段。
  例: 「广州市番禺区象贤中」+28+「学」；「珠海市华中师范大学」+14+
      「（珠海）附属中学」；「广州市海珠外国语实」+14+「验中学」。
- 补全段可能带新学校开头：「学南海实验高级中学」= 补全字「学」+
  新学校「南海实验高级中学」。
- 学校名也可能整行完整，人数同行或隔 1-2 行（名单行）出现。

解析原理（count 锚定）:
- 每个学校恰好对应人数列一个数字；人数是学校边界锚点。
- 学校名前半段 = 人数 y 之前最近且未结算的学校名段；
- 若前半段不以完整结尾词结束（中学/学校/学院/校区/大学/书院/高中…），
  或下一段以「（」/「附属」开头，则拼接人数 y 之后最近的名段（补全段）。
- 补全段以单字「学/校/院」开头且前半不完整时：首字补全前半，
  剩余文字作为新学校前半段。

验证基准:
- 总人数: 各校人数求和应 ≈ 10191（PDF 首页声明本科新生数），允许 ±2%。
- 广州 43 所区属示范已知正确值必须复现（象贤 28、仲元 83、真光 57 等）。

用法: python3 scripts/parse_gdut_pdf.py
"""
import json
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "raw" / "gdut_2024_enrollment.pdf"
OUT = ROOT / "dist" / "gdut_2024_school_counts.json"

# 学校名完整结尾词（含繁体与「X中」式简称）
_COMPLETE_END = re.compile(
    r"(中学|学校|学院|校区|大学|书院|高级中学|实验中学|附属中学|外国语学校|职业技术学校|高中|中心|"
    r"中學|學校|學院|大學|書院|"
    r"[一二三四五六七八九十]+中)$"
)


def is_complete_name(name: str) -> bool:
    """学校名是否已完整（不再需要补段）。

    - 正常完整：以「中学/学校/学院/校区/大学/书院/高中/中心」等词结尾；
    - 简写完整：「一中/二中」等数字+中（但「第X中」是拆段，需补「学」）；
    - 括号完整：以「)」结尾且内部已含完整词（如「…教师进修学校)」、
      「(厦门市科技中学)」），此时后续出现的「广州XX中学」是下一所学校。
    """
    if not name:
        return False
    if re.search(r"第[一二三四五六七八九十]+中$", name):
        return False  # 拆段：第X中 + 学
    if _COMPLETE_END.search(name):
        return True
    if name.endswith((")", "）")) and re.search(r"中学|学校|学院|校区|大学|书院|高中", name):
        return True
    return False
# 补全段开头（单字补全 or 括号校区 or 附属续接）
_COMPLETION_PREFIX = re.compile(r"^([学校院]|（|\(|附属|附中)")


def page_records(page):
    """从一页提取 (y, kind, text) 序列：kind ∈ name/count"""
    words = page.get_text("words")
    items = []
    for w in words:
        x0, y0, x1, text = w[0], w[1], w[2], w[4]
        if x0 < 180:
            items.append((y0, "name", text))
        elif 180 <= x0 < 230 and re.fullmatch(r"\d{1,4}", text):
            items.append((y0, "count", int(text)))
    # 按 y 聚行（3pt 容差），行内按 x 排序
    rows = {}
    for y0, kind, text in items:
        key = round(y0 / 3)
        rows.setdefault(key, []).append((y0, kind, text))
    out = []
    for k in sorted(rows):
        row = sorted(rows[k], key=lambda r: r[0])
        # 合并同 kind 文本
        names = [t for _, kind, t in row if kind == "name"]
        counts = [t for _, kind, t in row if kind == "count"]
        ntext = "".join(names) if names else ""
        ctext = counts[0] if counts else None
        if ntext or ctext is not None:
            out.append((k, ntext, ctext))
    return out


def parse():
    doc = pymupdf.open(PDF)

    # 跨页收集: 每页按 y 排序的记录序列
    all_pages = []
    for page in doc:
        all_pages.append(page_records(page))

    # 全局拼接（页间可跨行拆名，故页间保留 pending 状态连续处理）
    records = []  # [学校名, 人数]
    pending_name = ""    # 未结算的学校名前半
    pending_count = None  # 人数已见但名未完整（珠海模式）
    settled_at = None     # 当前记录从哪个位置开始

    def finish():
        nonlocal pending_name, pending_count
        if pending_name and pending_count is not None:
            records.append([pending_name, pending_count])
        pending_name = ""
        pending_count = None

    for page_items in all_pages:
        i, n = 0, len(page_items)

        while i < n:
            key, ntext, ctext = page_items[i]

            # ---- 处理名段（每条记录只处理一次）----
            if ntext:
                if not pending_name:
                    # 新学校开始：先占位，ctext 由下方人数块结算
                    pending_name = ntext
                    settled_at = i
                else:
                    # 1) 补全字开头（学/校/院）且前半不完整 → 拆出补全字
                    m = re.match(r"^([学校院])(.*)$", ntext)
                    if m and not is_complete_name(pending_name):
                        pending_name += m.group(1)
                        if is_complete_name(pending_name) and pending_count is not None:
                            records.append([pending_name, pending_count])
                            pending_name, pending_count = "", None
                        rest = m.group(2)
                        if rest:
                            # rest 若是独立完整学校名（完整词结尾且≥6字）→ 新学校
                            if is_complete_name(rest) and len(rest) >= 6:
                                pending_name = rest
                            else:
                                pending_name += rest  # 校区续接（如「学深圳学校」）
                            settled_at = i
                    # 2) 括号续接（珠海模式）：前半完整但被续接
                    elif re.match(r"^[（(]", ntext) and is_complete_name(pending_name):
                        pending_name += ntext
                        if is_complete_name(pending_name) and pending_count is not None:
                            records.append([pending_name, pending_count])
                            pending_name, pending_count = "", None
                    # 3) 前半不完整 → 普通补全段
                    elif not is_complete_name(pending_name):
                        pending_name += ntext
                        if is_complete_name(pending_name) and pending_count is not None:
                            records.append([pending_name, pending_count])
                            pending_name, pending_count = "", None
                    # 4) 前半已完整，新名段 = 新学校开始
                    else:
                        if pending_count is not None:
                            records.append([pending_name, pending_count])
                        pending_name = ntext
                        pending_count = None
                        settled_at = i

            # ---- 处理人数（独立于名段，同一记录内名段人数可同时存在）----
            if ctext is not None:
                if not pending_name:
                    # 无名的孤立人数（理论不出现，防御忽略）
                    pass
                elif is_complete_name(pending_name):
                    # 前半已完整 → 直接结算
                    records.append([pending_name, ctext])
                    pending_name, pending_count = "", None
                else:
                    # 前半不完整（珠海模式）→ 暂存人数等补全段
                    pending_count = ctext
            i += 1

    # 文档末尾结算残留（不完整名+count 或 完整名）
    if pending_name and pending_count is not None:
        records.append([pending_name, pending_count])

    # 名称变体归并
    canonical = {
        "广州市番禺区象贤中": "广州市番禺区象贤中学",
        "广州市番禺区实验中": "广州市番禺区实验中学",
        "广州市番禺区洛溪新": "广州市番禺区洛溪新城中学",
        "广州市海珠外国语实": "广州市海珠外国语实验中学",
        "广东外语外贸大学实": "广东外语外贸大学实验中学",
        "北京师范大学广州实": "北京师范大学广州实验学校",
        "广东第二师范学院番": "广东第二师范学院番禺附属中学",
        "广州市西关外国语学": "广州市西关外国语学校",
        "广州市天河外国语学": "广州市天河外国语学校",
        "广州白云中学": "广州市白云中学",
        "广州白云中学": "广州市白云中学",
        "广州市白云区广州空港实验中学": "广州市白云区广州空港实验中学",
    }
    merged = {}
    for name, cnt in records:
        key = canonical.get(name, name)
        merged[key] = merged.get(key, 0) + cnt

    final_list = sorted(merged.items(), key=lambda x: -x[1])
    gz_list = [(n, c) for n, c in final_list if "广州" in n]

    out = {"all": final_list, "guangzhou": gz_list}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")

    total = sum(c for _, c in final_list)
    print(f"记录数: {len(records)} | 合并后学校数: {len(final_list)} | 总人数: {total}（声明 10191，偏差 {total-10191:+d}）")
    print(f"广州学校数: {len(gz_list)}")
    known = {  # 已验证的广州 43 所区属示范正确值
        "广东仲元中学": 83, "广东番禺中学": 40, "广州市番禺区象贤中学": 28,
        "广州市真光中学": 57, "广州市玉岩中学": 48, "广州市天河中学": 46,
        "广州市第五中学": 44, "广州中学": 42, "广州市第十六中学": 40,
        "广州市培正中学": 38, "广州市南武中学": 34, "广州市第八十九中学": 32,
        "广州市第一中学": 31, "广州市第七中学": 30, "广东实验中学越秀学校": 9,
        "广州市西关外国语学校": 20, "广州市第一一三中学": 19, "广州市第六十五中学": 17,
        "广州市第三中学": 16, "广州大同中学": 16, "广州市番禺区实验中学": 15,
        "广州市海珠外国语实验中学": 14, "广东第二师范学院番禺附属中学": 14,
        "广州市第九十七中学": 14, "广州市第四中学": 12, "广州奥林匹克中学": 11,
        "广州科学城中学": 10, "广州市禺山高级中学": 10, "广州市第七十五中学": 8,
        "广州市南海中学": 6, "广东外语外贸大学实验中学": 6, "广州市第四十一中学": 5,
        "广州市番禺区大龙中学": 5, "北京师范大学广州实验学校": 4,
        "广州市白云中学": 2, "广州市白云区广州空港实验中学": 2,
        "广州市番禺区洛溪新城中学": 2, "广州彭加木纪念中学": 1,
        "广州市天河外国语学校": 9, "广州市培英中学": 23, "广州市第八十六中学": 23,
        "广州市育才中学": 18, "广州市第十七中学": 6,
    }
    bad = []
    for name, expect in known.items():
        got = merged.get(name)
        if got != expect:
            bad.append(f"{name}: 期望 {expect} 实得 {got}")
    print("43 所校验:", "全部通过" if not bad else "\n  " + "\n  ".join(bad))
    print(f"已写出: {OUT}")


if __name__ == "__main__":
    parse()
