#!/usr/bin/env python3
"""复现解析：越秀区小学升初中电脑派位分组（yuexiu_2026_juniors.json）——完全程序化，无人工写死转录。

输入（共享 raw，2026-09-23 补录）:
  data/enrollment/raw/yuexiu_2026_juniors_groups.html   2022 官方分组表（11 组×10 中学，表格结构）
  data/enrollment/raw/yuexiu_2026_official_juniors.html 2026 义务教育招生细则（第九条直升/派位口径）

流程:
  1. HTML 表格程序化读取 → 11 组 ×（组号, 对口小学列表, 10 个中学简称）  ← 机器提取，可审计
  2. 简称 → 官方全称 ALIAS 展开（人工规范表，每条带来源注释，全部经现有转录/实体表核对）
  3. 细则正文正则提取直升（"XX中学面向XX小学/学校" + 九年一贯制 5 校）→ direct_feed
输出: data/middle/enrollment/parsed/_transcripts/yuexiu_2026_juniors.json

用法: python3 data/middle/enrollment/scripts/parse_yuexiu_juniors.py [--out PATH]
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
RAW = os.path.join(ROOT, "data", "enrollment", "raw")
OUT = os.path.join(ROOT, "data", "middle", "enrollment", "parsed", "_transcripts", "yuexiu_2026_juniors.json")

META = {
    "year": 2026,
    "district": "越秀区",
    "source": "2022年越秀区小学升初中电脑派位生分组表（官网 post_8301356）+ 2026 义务教育招生细则（post_10790590，确认分组稳定、直升口径）",
    "source_url": "http://www.yuexiu.gov.cn/gzjg/qzf/qjyj/jyzl/gk/zswd/content/post_8301356.html",
    "source_url_rules": "https://www.yuexiu.gov.cn/gzjg/qzf/qjyj/jyzl/gk/jyjwj/content/post_10790590.html",
    "note": "分组表为 2022 年官方表（2026 细则第九条确认组别稳定，志愿填报学校数 12→10 所）；无班数/范围（官方分组表仅组结构）",
    "mechanism": "group_paidui",
}

# 官网简称 → 官方全称（B 层人工规范表，2026-09-23 经现有转录+实体表逐条核对）
# 执信水荫：2022 表格写作"执信水荫"，2026 派位按执信路校区计（水荫校区 2026 无初一招生，
# 见 src/middle_enroll_notes.json「执信水荫：仅初三就读」）；矿泉中学 2026 改名培正矿泉学校。
ALIAS = {
    "广州7中": "广州市第七中学",
    "广州16中": "广州市第十六中学",
    "省越天胜": "广东实验中学越秀学校（天胜校区）",
    "育才中学": "广州市育才中学",
    "十六实验": "广州市第十六中学实验学校",
    "八一实验": "广州市八一实验学校",
    "东风实验": "广州市东风实验学校",
    "七中东山": "广州市第七中学东山学校",
    "广大附中": "广州大学附属中学",
    "执信水荫": "广州市执信中学（执信路校区）",  # 见 META.note 口径说明
    "执信本部": "广州市执信中学（执信路校区）",
    "广州17中": "广州市第十七中学",
    "华侨外语": "广州市华侨外国语学校",
    "广州13中": "广州市第十三中学",
    "广州2中": "广州市第二中学",
    "广州3中": "广州市第三中学",
    "三中实验": "广州市第三中学实验学校",
    "广东侨中": "广东华侨中学",
    "十六东华": "广州市第十六中学东华实验学校",
    "培正中学": "广州市培正中学",
    "省实中学": "广东实验中学",
    "铁一中学": "广州市铁一中学",
    "广州10中": "广州市第十中学",
    "知用学校": "广州市知用学校",
    "真光学校": "广州市真光学校",
    "七中实验": "广州市第七中学实验学校",
    "矿泉中学": "广州市培正矿泉学校",
}

# 直升小学名规范化：细则原文名（"广州市铁一小学"等）→ 转录 key（实体表别名口径）
DIRECT_FEED_ALIAS = {
    "广州市铁一小学": "铁一小学",
    "广州市培正小学": "东山培正小学",
    "广州市育才学校": "育才学校",
}


def _cell_texts(row):
    return [re.sub(r"<[^>]+>", "", c).strip()
            for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]


def parse_groups(html):
    """程序化读官方分组表表格 → [{group, primaries, juniors(全称)}]。"""
    tables = re.findall(r"<table[^>]*>.*?</table>", html, re.S)
    assert len(tables) == 1, f"期望 1 个表格，实际 {len(tables)}"
    rows = re.findall(r"<tr[^>]*>.*?</tr>", tables[0], re.S)
    groups = []
    for row in rows[4:15]:  # row0 标题 / row1 日期 / row2-3 表头 / row4-14 数据 / row15 备注
        cells = _cell_texts(row)
        assert cells[0], f"组号缺失: {cells}"
        primaries = [s.strip() for s in cells[1].split("、") if s.strip()]
        assert len(cells[2:12]) == 10, f"组 {cells[0]} 中学列数异常: {len(cells)-2}"
        juniors = [ALIAS[a] for a in cells[2:12]]
        groups.append({"group": cells[0], "primaries": primaries, "juniors": juniors})
    assert len(groups) == 11
    return groups


def parse_direct_feed(rules_html):
    """细则正文正则提取直升：'XX中学面向XX小学/学校'（3 条）+ 九年一贯制 5 校（本校小学部直升）。"""
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", rules_html, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|\u3000|\s+", "", text)
    feed = {}
    # 1) "广州市铁一中学面向广州市铁一小学" 模式
    for m in re.finditer(r"广州市([\u4e00-\u9fff（）]+?学校|[\u4e00-\u9fff（）]+?中学)面向广州市([\u4e00-\u9fff（）]+?小学|[\u4e00-\u9fff（）]+?学校)", text):
        junior, primary = m.group(1), m.group(2)
        key = DIRECT_FEED_ALIAS.get("广州市" + primary, "广州市" + primary)
        feed[key] = "广州市" + junior
    # 2) 九年一贯制 5 校（细则第九条括号名单）——本校小学部 → 本校初中部
    #    key 用小学部习惯名（去"广州市"前缀，与既有转录/实体匹配口径一致）
    m = re.search(r"九年一贯制学校（([^）]+?)）", text)
    assert m, "细则未找到九年一贯制学校名单"
    for name in re.split(r"[、和]", m.group(1)):
        name = name.strip()
        if not name:
            continue
        key = re.sub(r"^广州市", "", name) + "（小学部）"
        feed[key] = f"广州市{name}" if not name.startswith("广州市") else name
    return feed


def extract():
    groups_html = open(os.path.join(RAW, "yuexiu_2026_juniors_groups.html"), encoding="utf-8").read()
    rules_html = open(os.path.join(RAW, "yuexiu_2026_official_juniors.html"), encoding="utf-8").read()
    return {**META, "groups": parse_groups(groups_html), "direct_feed": parse_direct_feed(rules_html)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    data = extract()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # 完整性校验
    assert len(data["groups"]) == 11 and all(len(g["juniors"]) == 10 for g in data["groups"])
    assert len(data["direct_feed"]) == 8, f"直升应 8 条，实际 {len(data['direct_feed'])}"
    print(f"✓ {args.out}")
    print(f"  {len(data['groups'])} 组 × 10 初中（程序化提取） + {len(data['direct_feed'])} 条直升（细则正则）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
