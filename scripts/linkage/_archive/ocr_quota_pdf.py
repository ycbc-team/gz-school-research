# -*- coding: utf-8 -*-
"""渲染名额分配结果 PDF 并 OCR，输出每页文字+坐标到 JSON"""
import pymupdf, json, os, sys
from rapidocr_onnxruntime import RapidOCR

PDF = 'data/linkage/raw/quota_detail.pdf'
OUT_DIR = 'data/linkage/raw/ocr_pages'
os.makedirs(OUT_DIR, exist_ok=True)

ocr = RapidOCR()
doc = pymupdf.open(PDF)
print('总页数:', len(doc))

for i, page in enumerate(doc):
    out = f'{OUT_DIR}/page_{i+1:02d}.json'
    if os.path.exists(out):
        continue
    mat = pymupdf.Matrix(300/72, 300/72)
    pix = page.get_pixmap(matrix=mat)
    png = f'{OUT_DIR}/tmp_{i}.png'
    pix.save(png)
    result, _ = ocr(png)
    items = []
    for item in (result or []):
        box, text, conf = item
        xs = [float(p[0]) for p in box]; ys = [float(p[1]) for p in box]
        items.append({'x0': min(xs), 'x1': max(xs), 'y0': min(ys), 'y1': max(ys),
                      'text': str(text), 'conf': float(conf)})
    json.dump(items, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    os.remove(png)
    print(f'page {i+1}: {len(items)} items')
print('done')
