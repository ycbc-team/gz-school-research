#!/usr/bin/env python3
"""机器 OCR 原文落盘（parsed/_ocr/）：海珠初中问答/计划表图片、天河/黄埔 PDF 附件页 → Vision OCR 行文本。

目的：为「Read 多模态直读」转录提供可复现的机器原文底稿——转录内容可在 OCR 原文中交叉校验
（见 audit_transcripts.py，量化命中率，未命中项进入人工复核清单），使 A 层转录可审计。

输入（共享 raw）:
  海珠 data/enrollment/raw/haizhu_2026_juniors_faq_01..13.jpg + haizhu_2026_juniors_plan.png
  天河 data/enrollment/raw/tianhe_2026_official.pdf  附件6/7/8 页 43-48（公办初中/企事业/民办初中）
  黄埔 data/enrollment/raw/huangpu_2026_official.pdf 附件5 页 27-29（小升初派位及对口直升分组表）

输出: data/middle/enrollment/parsed/_ocr/<区>_juniors_ocr.json
  {"district", "year", "pages": [{"file", "lines": [{text, x, y, w, h}, ...]}], "text": "全文拼接"}

依赖: pyobjc-framework-Vision（同小学侧 parse_haizhu_diduan.py）；poppler pdftoppm（PDF→PNG）
用法: python3 data/middle/enrollment/scripts/build_juniors_ocr.py
"""
import glob
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
RAW = os.path.join(ROOT, "data", "enrollment", "raw")
OCR_OUT = os.path.join(ROOT, "data", "middle", "enrollment", "parsed", "_ocr")
OCR_TOOL = os.path.join(ROOT, "data", "primary", "enrollment", "scripts", "ocr", "vision_ocr.py")

HAIZHU_FAQ = sorted(glob.glob(os.path.join(RAW, "haizhu_2026_juniors_faq_*.jpg")))
HAIZHU_PLAN = os.path.join(RAW, "haizhu_2026_juniors_plan.png")
PDF_PAGES = {
    "tianhe": (os.path.join(RAW, "tianhe_2026_official.pdf"), 43, 48, "附件6 公办初中划片及计划 + 附件7 企事业 + 附件8 民办"),
    "huangpu": (os.path.join(RAW, "huangpu_2026_official.pdf"), 27, 29, "附件5 小升初电脑随机派位及对口直升分组表"),
}


def ocr_image(img, json_path):
    subprocess.run(["python3", OCR_TOOL, img, "--json", json_path], check=True)
    return json.load(open(json_path, encoding="utf-8"))


def pdf_pages_to_png(pdf, first, last, tmp):
    out_prefix = os.path.join(tmp, "page")
    subprocess.run(["pdftoppm", "-png", "-r", "150", "-f", str(first), "-l", str(last), pdf, out_prefix], check=True)
    return sorted(glob.glob(out_prefix + "*.png"))


def main():
    os.makedirs(OCR_OUT, exist_ok=True)
    # 海珠：13 问答页 + 计划表
    pages = []
    for img in HAIZHU_FAQ:
        n = os.path.basename(img).split("_")[-1].split(".")[0]
        pages.append({"file": os.path.basename(img), "page": f"问答{n}",
                      "lines": ocr_image(img, os.path.join(tempfile.gettempdir(), "hz_ocr.json"))})
    pages.append({"file": os.path.basename(HAIZHU_PLAN), "page": "计划表",
                  "lines": ocr_image(HAIZHU_PLAN, os.path.join(tempfile.gettempdir(), "hz_plan_ocr.json"))})
    _write("haizhu", pages, "2026 初中招生问答（13 页图）+ 公办初中招生计划表")
    # 天河/黄埔：PDF 附件页
    for dk, (pdf, first, last, note) in PDF_PAGES.items():
        tmp = tempfile.mkdtemp()
        pngs = pdf_pages_to_png(pdf, first, last, tmp)
        pages = []
        for i, png in enumerate(pngs):
            pg = first + i
            pages.append({"file": os.path.basename(pdf), "page": f"p{pg}",
                          "lines": ocr_image(png, os.path.join(tmp, f"p{pg}.json"))})
        _write(dk, pages, note)
    print(f"✓ OCR 原文已落盘 {OCR_OUT}")


def _write(dk, pages, note):
    text = "\n".join(l["text"] for p in pages for l in p["lines"])
    out = {"district": dk, "year": 2026, "note": note,
           "pages": pages, "text": text,
           "line_count": sum(len(p["lines"]) for p in pages)}
    with open(os.path.join(OCR_OUT, f"{dk}_juniors_ocr.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"  {dk}: {len(pages)} 页, {out['line_count']} 行, 原文 {len(text)} 字")


if __name__ == "__main__":
    sys.exit(main())
