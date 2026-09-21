#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""特色校数据审计：数量断言 / 字段完整性 / URL 域名与签发机构 / PDF 源一致性 / dist 一致性。

用法：python3 data/specialty_schools/scripts/audit_specialty.py
任一断言失败即退出码 1 并输出明细；全部通过输出 PASS 汇总。
"""
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

SPECIALTY = Path(__file__).resolve().parent.parent
PARSED = SPECIALTY / "parsed"
DIST = SPECIALTY / "dist"

FAILS = []


def check(cond, msg):
    if cond:
        print(f"  PASS  {msg}")
    else:
        FAILS.append(msg)
        print(f"  FAIL  {msg}")


def batch_counts():
    """每批次记录数断言（期望值以官方源核实为准：见各解析脚本与 raw/ 源文件）。"""
    expect = {
        "gd_arts_tradition": {
            ("美育/艺术教育", "首批"): 10,      # p1_art_first.pdf 附件
            ("中华优秀传统文化传承", "首批"): 6,  # 省厅 2020 网页公告
            ("中华优秀传统文化传承", "第二批"): 22,  # p3_trad2_art4.pdf 附件1（OCR）
            ("美育/艺术教育", "第四批"): 26,     # p3_trad2_art4.pdf 附件2（OCR）
            ("中华优秀传统文化传承", "第三批"): 12,  # p2_trad_art5.pdf 附件1
            ("美育/艺术教育", "第五批"): 9,      # p2_trad_art5.pdf 附件2
            ("美育/艺术教育", "第三批"): 20,     # 省厅 2020 网页公告
        },
        "sports": {
            ("体育-校园足球", "第一批"): 39,      # moe_2015_football_schools.xls
            ("体育-篮球", "第一批"): 26,          # moe_2017_basketball_batch1.docx
            ("体育-校园足球", "2023年"): 45,      # moe_2023_football.xlsx
            ("体育-校园足球", "2024年度"): 47,    # moe_2024_football.txt
            ("体育-校园足球", "2025年"): 45,      # moe_2025_football.txt
            ("体育-冰雪体育", "首批"): 49,        # jyj.gz.gov.cn 9357006.pdf
        },
        "gz_mental_health": {
            ("心理健康教育", "第五批"): 13, ("心理健康教育", "第六批"): 41, ("心理健康教育", "第七批"): 43,
        },
        "gz_meiyu_pilot": {("美育/艺术教育", "首批"): 30},
        "science_tech": {("科技创新/科学教育", "首批"): 49},
        "gd_science_high": {("科学高中", "首批"): 6},
    }
    print("== 批次数量断言（期望值来源：官方名单/附件，见各 parse 脚本注释）==")
    total_ok = True
    for fname, wants in expect.items():
        doc = json.loads((PARSED / f"{fname}.json").read_text("utf-8"))
        c = Counter((r.get("category"), r.get("batch")) for r in doc["records"])
        for key, want in wants.items():
            got = c.get(key, 0)
            ok = got == want
            total_ok = total_ok and ok
            check(ok, f"{fname} {key}: {got}（期望 {want}）")
    return total_ok


def fields_complete():
    print("== 字段完整性（school/category/level/batch/year/project/issuer/url 非空）==")
    ok = True
    for f in PARSED.glob("*.json"):
        doc = json.loads(f.read_text("utf-8"))
        for i, r in enumerate(doc.get("records", [])):
            for k in ("school", "category", "level", "batch", "year", "project", "issuer", "url"):
                if not r.get(k):
                    FAILS.append(f"{f.name}[{i}] 缺字段 {k}")
                    ok = False
                    print(f"  FAIL  {f.name}[{i}] 缺字段 {k}（school={r.get('school')}）")
    check(ok, "全部记录必填字段完整")
    return ok


def url_issuer_match():
    print("== URL 域名与签发机构匹配（媒体转载源记 WARN，见 README 缺口）==")
    official = ("moe.gov.cn", "edu.gd.gov.cn", "jyj.gz.gov.cn", "cnts.gov.cn", "yuexiu.gov.cn")
    media = ("southcn.com", "nfapp.southcn.com", "chinanews.com", "dayoo.com", "hsfz.net.cn")
    domains = {
        "教育部": "moe.gov.cn", "广东省教育厅": "edu.gd.gov.cn", "广州市教育局": "jyj.gz.gov.cn",
    }
    ok, warns = True, 0
    for f in PARSED.glob("*.json"):
        doc = json.loads(f.read_text("utf-8"))
        seen = {}
        for r in doc["records"]:
            key = (r["issuer"], r["url"])
            if key in seen:
                continue
            seen[key] = True
            dom = domains.get(r["issuer"])
            if dom and dom not in r["url"]:
                if any(m in r["url"] for m in official):
                    print(f"  WARN  {f.name}: {r['issuer']} 官方域名变体（官网转载/历史域名）→ {r['url'][:70]}")
                    warns += 1
                elif any(m in r["url"] for m in media):
                    print(f"  WARN  {f.name}: {r['issuer']} 媒体转载源（非一手官网）→ {r['url'][:70]}")
                    warns += 1
                else:
                    FAILS.append(f"{f.name}: issuer={r['issuer']} 但 url={r['url']}")
                    ok = False
                    print(f"  FAIL  {f.name}: {r['issuer']} → {r['url'][:70]}")
    check(ok, f"URL 无不可识别来源（媒体转载/官网转载 {warns} 项记 WARN）")
    return ok


def pdf_source_consistency():
    """PDF 解析 5 批次 vs parsed：真差异为 0（名字规范差异走白名单）。"""
    print("== PDF 源一致性（parse_gd_edu_pdf 5 批次 vs parsed）==")
    sys.path.insert(0, str(Path(__file__).parent))
    import parse_gd_edu_pdf as P
    results = []
    text1 = P.pdftotext(P.RAW / "p1_art_first.pdf")
    results.append({"batch": P.ATTACHMENTS["首批艺术"]["batch"], "category": "美育/艺术教育", "records": P.parse_p1(text1)})
    text2 = P.pdftotext(P.RAW / "p2_trad_art5.pdf")
    seg3 = text2.split("附件1")[1].split("附件2")[0] if "附件2" in text2 else text2
    seg5 = text2.split("附件2")[1] if "附件2" in text2 else ""
    results.append({"batch": P.ATTACHMENTS["第三批传承"]["batch"], "category": "中华优秀传统文化传承", "records": P.parse_rowwise(seg3)})
    results.append({"batch": P.ATTACHMENTS["第五批艺术"]["batch"], "category": "美育/艺术教育", "records": P.parse_rowwise(seg5)})
    doc = json.loads((PARSED / "gd_arts_tradition.json").read_text("utf-8"))
    exist = {}
    for r in doc["records"]:
        exist.setdefault((r["category"], r["batch"]), []).append(r["school"])
    ok = True
    for b in results:
        names = list(dict.fromkeys(re.sub(r"^广州市", "", P.norm(r["raw_name"])) for r in b["records"]))
        es = [re.sub(r"^广州市", "", P.norm(x)) for x in exist.get((b["category"], b["batch"]), [])]
        ps, es_s = set(names), set(es)
        for n in sorted(ps - es_s):  # OCR 错字或真差异：用 fuzzy 校正
            cand, kind = P.fuzzy_fix(n, list(es_s))
            if not cand:
                ok = False
                FAILS.append(f"PDF {b['batch']} 解析独有未校正: {n}")
                print(f"  FAIL  PDF {b['batch']} 解析独有（非OCR错字）: {n}")
        for n in sorted(es_s - ps):  # 现有独有侧：能在解析名中找到相似（名字规范差异/OCR错字）则算解释
            cand, kind = P.fuzzy_fix(n, list(ps))
            if not cand:
                ok = False
                FAILS.append(f"PDF {b['batch']} 现有独有: {n}")
                print(f"  FAIL  PDF {b['batch']} 现有独有（名单中未见）: {n}")
    # 第二批/第四批 OCR 批次
    text3 = P.ocr_pdf(P.RAW / "p3_trad2_art4.pdf")
    seg2, seg4 = P.split_ocr_attachments(text3)
    for b in ({"batch": P.ATTACHMENTS["第二批传承"]["batch"], "category": "中华优秀传统文化传承", "records": P.parse_ocr_gz_rows(seg2)},
              {"batch": P.ATTACHMENTS["第四批艺术"]["batch"], "category": "美育/艺术教育", "records": P.parse_ocr_gz_rows(seg4)}):
        names = list(dict.fromkeys(re.sub(r"^广州市", "", P.norm(r["raw_name"])) for r in b["records"]))
        es = [re.sub(r"^广州市", "", P.norm(x)) for x in exist.get((b["category"], b["batch"]), [])]
        ps, es_s = set(names), set(es)
        for n in sorted(ps - es_s):
            cand, kind = P.fuzzy_fix(n, list(es_s))
            if not cand:
                ok = False
                FAILS.append(f"PDF {b['batch']} 解析独有未校正: {n}")
                print(f"  FAIL  PDF {b['batch']} 解析独有（非OCR错字）: {n}")
        for n in sorted(es_s - ps):
            # OCR 漏抓：现有名能在解析名中找到相似（OCR错字）则算已解释，否则为真实漏抓
            cand, kind = P.fuzzy_fix(n, list(ps))
            if cand:
                print(f"  OK    PDF {b['batch']} 现有名 {n} ← OCR错字 {cand} ({kind})")
            else:
                print(f"  WARN  PDF {b['batch']} OCR 未检出: {n}（人工核验，见 README）")
    check(ok, "PDF 解析与 parsed 5 批次无未解释差异（第二批/第四批 OCR 漏抓项另行人工核验）")
    return ok


def dist_consistency():
    print("== dist 一致性（dist.schools[].school 覆盖 parsed 全部学校名）==")
    ok = True
    dist = json.loads((DIST / "specialty_schools.json").read_text("utf-8"))
    pool = {s.get("school") for s in dist.get("schools", [])}
    for f in PARSED.glob("*.json"):
        doc = json.loads(f.read_text("utf-8"))
        for r in doc["records"]:
            if r["school"] not in pool:
                ok = False
                FAILS.append(f"dist 未覆盖 {f.name}: {r['school']}")
                print(f"  FAIL  dist 未覆盖 {f.name}: {r['school']}")
    check(ok, "dist schools 池覆盖全部 parsed 学校名")
    return ok


def main():
    print("=" * 60)
    print("特色校数据审计")
    print("=" * 60)
    r1 = batch_counts()
    r2 = fields_complete()
    r3 = url_issuer_match()
    r4 = pdf_source_consistency()
    r5 = dist_consistency()
    print("=" * 60)
    if FAILS:
        print(f"审计未通过：{len(FAILS)} 项失败")
        sys.exit(1)
    print("全部断言通过")


if __name__ == "__main__":
    main()
