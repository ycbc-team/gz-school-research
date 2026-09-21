#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""省教育厅艺术/传承名单 PDF 解析（raw/gd_edu → 广州学校清单 + 与 gd_arts_tradition.json 对比）。

覆盖：
  - p1_art_first.pdf   首批广东省中小学艺术教育特色学校（文本型，序号锚定+跨行规整）
  - p2_trad_art5.pdf   附件1 第三批传承 + 附件2 第五批艺术（文本型，行式）
  - p3_trad2_art4.pdf  附件1 第二批传承 + 附件2 第四批艺术（扫描件 → pymupdf 渲染 + tesseract OCR）

输出 scripts/out/gd_edu_pdf_parsed.json + 对比报告。
用法：python3 data/specialty_schools/scripts/parse_gd_edu_pdf.py [--ocr]（--ocr 才跑 p3 OCR，较慢）
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPECIALTY = Path(__file__).resolve().parent.parent
RAW = SPECIALTY / "raw" / "gd_edu"
OUT_DIR = Path(__file__).resolve().parent / "out"

ISSUER_GD = "广东省教育厅"
GZ_DISTRICTS = ["越秀", "海珠", "荔湾", "天河", "白云", "黄埔", "番禺", "花都", "南沙", "从化", "增城"]
GZ_NAME_RE = re.compile(r"广州市|" + "|".join(GZ_DISTRICTS))
OTHER_CITY_RE = re.compile(r"东莞|佛山|中山|珠海|惠州|江门|肇庆|汕头|汕尾|湛江|茂名|揭阳|潮州|韶关|河源|梅州|清远|云浮|阳江|深圳|龙岗|宝安|南山|福田|罗湖|盐田|坪山|龙华|光明")
SCHOOL_TAIL = re.compile(r"(学校|中学|小学|幼儿园|学院|分校|学术)$")
NO = re.compile(r"^\s*(\d{1,4})\s+")

# 附件名 → (批次, 类别, 年份, 项目全称)
ATTACHMENTS = {
    "首批艺术": {"category": "美育/艺术教育", "batch": "首批", "year": "2018",
                 "project": "首批广东省中小学艺术教育特色学校"},
    "第二批传承": {"category": "中华优秀传统文化传承", "batch": "第二批", "year": "2021",
                   "project": "第二批广东省中小学中华优秀文化传承学校"},
    "第四批艺术": {"category": "美育/艺术教育", "batch": "第四批", "year": "2021",
                   "project": "第四批广东省中小学艺术教育特色学校"},
    "第三批传承": {"category": "中华优秀传统文化传承", "batch": "第三批", "year": "2022",
                   "project": "第三批广东省中小学中华优秀文化传承学校"},
    "第五批艺术": {"category": "美育/艺术教育", "batch": "第五批", "year": "2022",
                   "project": "第五批广东省中小学艺术教育特色学校"},
}


def pdftotext(path):
    return subprocess.run(["pdftotext", "-layout", str(path), "-"],
                          capture_output=True, text=True).stdout


def is_gz(name):
    if not name:
        return False
    if OTHER_CITY_RE.search(name):
        return False
    return bool(GZ_NAME_RE.search(name)) or name.startswith("广州")


def parse_p1(text):
    """首批艺术：序号锚定，县区/学校可能跨行。返回 [(name, line, district)]
    序号行可能无尾随空格（如"005"独占一行），否则会与前一行合并导致学校名覆盖。"""
    out = []
    cur = None
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^\s*(\d{1,4})(?:\s+|$)", line)
        if m:
            if cur:
                out.append(cur)
            cur = {"no": m.group(1), "tokens": line.split(), "line": i}
        elif cur:
            cur["tokens"] += line.split()
    if cur:
        out.append(cur)
    rows = []
    for r in out:
        toks = r["tokens"][1:]
        tail_toks = [t for t in toks
                     if SCHOOL_TAIL.search(t) and not re.fullmatch(r"(广州市|[^市]{1,4}区)", t)]
        if not tail_toks:
            continue
        name = tail_toks[-1]  # 学校名列在最后（县区/地市列居前）
        # 归穗：学校名含区名/广州市前缀，或行内地市/县区列本身是广州区名（如"广东广雅中学"）
        gz_col = any(t == "广州市" or (t.endswith("区") and t[:-1] in GZ_DISTRICTS) for t in toks)
        gz_col = gz_col and not any(OTHER_CITY_RE.search(t) for t in toks)
        if is_gz(name) or gz_col:
            rows.append({"raw_name": name, "line": r["line"], "no": r["no"]})
    return rows


def parse_rowwise(text):
    """行式名单（序号 地市 学校 [项目]）：地市=广州市。"""
    rows = []
    for i, line in enumerate(text.splitlines(), 1):
        parts = line.split()
        if len(parts) >= 3 and NO.match(line) and parts[1] == "广州市":
            name = parts[2]
            # 学校名列后可能紧跟项目名，学校名本身可能带空格（已由 split 拆开）
            # 用尾部词还原：从第 3 个 token 起向后拼，直到 SCHOOL_TAIL
            j, name = 2, ""
            for tok in parts[2:]:
                name += tok
                if SCHOOL_TAIL.search(name):
                    break
            rows.append({"raw_name": name, "line": i})
    return rows


def ocr_pdf(path, lang="chi_sim", dpi=300, psm="4"):
    """扫描件：pymupdf 渲染 + tesseract OCR。
    注意：渲染图必须写在工作区/项目目录内（外部二进制 tesseract 看不到沙箱 /tmp）。
    扫描表格用 psm=4（单列可变块）效果远好于 psm=6（表格线干扰）。"""
    import fitz
    doc = fitz.open(str(path))
    tmp = OUT_DIR / ".ocr_tmp"
    tmp.mkdir(exist_ok=True)
    parts = []
    for pno in range(doc.page_count):
        pix = doc[pno].get_pixmap(dpi=dpi)
        img = tmp / f"{Path(path).stem}_p{pno+1}.png"
        pix.save(str(img))
        txt = subprocess.run(["tesseract", str(img), "-", "-l", lang, "--psm", psm],
                             capture_output=True, text=True, errors="replace").stdout
        parts.append(f"===== PAGE {pno+1} =====\n{txt}")
    return "\n".join(parts)


# OCR 学校名提取：以"广州(市)"开头、以校名后缀结尾（错字地市列不影响，省直属行自动排除）
# 后缀含"学术"（tesseract 常见"学校"→"学术"错字）、"广州大学附属中学"等无"市"前缀也收
GZ_SCHOOL_RE = re.compile(r"广州(?:市)?[\u4e00-\u9fa5]+?(?:中学|小学|学校|学院|幼儿园|学术)")


def parse_ocr_gz_rows(text):
    rows = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in GZ_SCHOOL_RE.finditer(line):
            name = m.group(0)
            if SCHOOL_TAIL.search(name):
                rows.append({"raw_name": name, "line": i})
    return rows


def split_ocr_attachments(text):
    """按页面分段 OCR：PAGE1-2 发文正文；PAGE3 起附件1（第二批传承）；含"第四批+艺术+名单"标题的页起为附件2。
    标题可能跨行，故按"页内同时出现关键词"判定，而非单行匹配。"""
    pages = re.split(r"===== PAGE (\d+) =====", text)
    # pages: ['', '1', content1, '2', content2, ...]
    page_map = {}
    for i in range(1, len(pages), 2):
        page_map[int(pages[i])] = pages[i + 1]
    annex2_page = None
    for pno in sorted(page_map):
        if pno <= 2:  # PAGE1-2 为通知+发文页（含附件目录），不作为名单页锚
            continue
        c = page_map[pno]
        if "第四批" in c and "艺术" in c and "名单" in c:
            annex2_page = pno
            break
    seg2_lines, seg4_lines = [], []
    for pno in sorted(page_map):
        if pno <= 2:
            continue
        if annex2_page and pno >= annex2_page:
            seg4_lines.append(f"===== PAGE {pno} =====\n{page_map[pno]}")
        else:
            seg2_lines.append(f"===== PAGE {pno} =====\n{page_map[pno]}")
    return "\n".join(seg2_lines), "\n".join(seg4_lines)


def load_gz_entity_names():
    """entities.json 中广州学校名（去"广州市"前缀）集合，用于 p1 省属/无前缀校二次确认。"""
    try:
        ents = json.loads((ROOT / "data/registry/entity/dist/entities.json").read_text("utf-8"))["entities"]
    except Exception:
        return set()
    gz = set()
    for e in ents:
        if e.get("school_id", "").startswith("gz-4401"):
            n = re.sub(r"^广州市", "", norm(e.get("name", "")))
            gz.add(n)
            for a in e.get("aliases", []):
                gz.add(re.sub(r"^广州市", "", norm(a)))
    return gz


def norm(s):
    return re.sub(r"\s+", "", s or "").strip()


import difflib


def _strip_prefix(name):
    """剥离区名前缀，返回学校主体名。优先"X区"（含 OCR 错字区名如"自去区/秋遇区"），
    再剥已知广州区名（官方名单常省略"区"字，如"天河外国语学校"）。"""
    m = re.match(r"^(.{1,4}?区)", name)
    if m:
        return name[m.end():]
    for d in GZ_DISTRICTS:
        if name.startswith(d) and len(name) > len(d):
            return name[len(d):]
    return name


def fuzzy_fix(name, candidates):
    """OCR 错字校对。两级判定，避免把不同学校误配：
    1. 去区名后主体完全一致（覆盖 OCR 区名错字，如"番遇区"→"番禺区"）；
    2. 无区名或主体差 1 字（短名相似度≥0.75，覆盖校名 1 字错字，如"天荧"→"天荣"）。
    其余不校正（防"铁一小学"↔"朝天小学"这类不同学校误配）。
    返回 (校正名, 判定类型) 或 (None, None)。"""
    body = _strip_prefix(name)
    best, best_r = None, 0.0
    for c in candidates:
        cb = _strip_prefix(c)
        if cb == body:
            return c, "主体一致"
        r = difflib.SequenceMatcher(None, body, cb).ratio()
        if r > best_r:
            best, best_r = c, r
    # 1 字错字（短名，如"天荧中学"→"天荣中学"）
    if best_r >= 0.75 and min(len(body), len(_strip_prefix(best))) <= 10:
        return best, f"1字错字({best_r})"
    # 2 字错字：等长、后 3 字后缀一致（如"闻维爆纪念中学"→"邝维煜纪念中学"）；
    # 但"铁一小学"vs"朝天小学"后缀"一小学/天小学"不同，不误配
    for c in candidates:
        cb = _strip_prefix(c)
        if len(body) == len(cb) and len(body) >= 5 and body[-3:] == cb[-3:] \
                and sum(a != b for a, b in zip(body, cb)) <= 2:
            return c, "2字错字"
    return None, None


def main():
    OUT_DIR.mkdir(exist_ok=True)
    results = []

    # p1 首批艺术（省直属段如广东实验中学/华师附中在地市列留空，按口径不计入"广州市"段）
    text1 = pdftotext(RAW / "p1_art_first.pdf")
    rows1 = parse_p1(text1)
    results.append({"key": "p1_art_first", "batch": "首批艺术", "records": rows1,
                    **ATTACHMENTS["首批艺术"]})

    # p2 第三批传承 + 第五批艺术
    text2 = pdftotext(RAW / "p2_trad_art5.pdf")
    seg3 = text2.split("附件1")[1].split("附件2")[0] if "附件2" in text2 else text2
    seg5 = text2.split("附件2")[1] if "附件2" in text2 else ""
    results.append({"key": "p2_trad3", "batch": "第三批传承", "records": parse_rowwise(seg3),
                    **ATTACHMENTS["第三批传承"]})
    results.append({"key": "p2_art5", "batch": "第五批艺术", "records": parse_rowwise(seg5),
                    **ATTACHMENTS["第五批艺术"]})

    # p3 第二批传承 + 第四批艺术（扫描件 OCR，按附件标题分段）
    text3 = ocr_pdf(RAW / "p3_trad2_art4.pdf")
    seg2, seg4 = split_ocr_attachments(text3)
    results.append({"key": "p3_trad2", "batch": "第二批传承", "records": parse_ocr_gz_rows(seg2),
                    **ATTACHMENTS["第二批传承"]})
    results.append({"key": "p3_art4", "batch": "第四批艺术", "records": parse_ocr_gz_rows(seg4),
                    **ATTACHMENTS["第四批艺术"]})

    (OUT_DIR / "gd_edu_pdf_parsed.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 对比 gd_arts_tradition.json
    doc = json.loads((SPECIALTY / "parsed" / "gd_arts_tradition.json").read_text("utf-8"))
    exist = {}
    for r in doc.get("records", []):
        exist.setdefault((r.get("category"), r.get("batch")), []).append(r["school"])

    print(f"{'批次':<10}{'解析广州':<6}{'现有':<6}{'校正后独有':<8}{'现有独有'}")
    for b in results:
        # 归一化：去"广州市"前缀后再比较（官方名单常省略前缀，parsed 多已补全）
        names = list(dict.fromkeys(re.sub(r"^广州市", "", norm(r["raw_name"])) for r in b["records"]))
        es = [re.sub(r"^广州市", "", norm(x)) for x in exist.get((b["category"], b["batch"]), [])]
        ps, es_s = set(names), set(es)
        # OCR 错字校对：解析独有名与现有名做相似度匹配，命中则视为同一所
        fixed = {}
        real_only = []
        for n in sorted(ps - es_s):
            cand, kind = fuzzy_fix(n, list(es_s))
            if cand:
                fixed[n] = (cand, kind)
            else:
                real_only.append(n)
        print(f"{b['batch']:<10}{len(ps):<6}{len(es_s):<6}{len(real_only):<8}{len(es_s-ps)}")
        for n, (cand, kind) in fixed.items():
            print(f"    [OCR校正] {n} → {cand} ({kind})")
        for n in real_only:
            print(f"    [真差异·解析独有] {n}")
        for n in sorted(es_s - ps):
            print(f"    [现有独有] {n}")


if __name__ == "__main__":
    main()
