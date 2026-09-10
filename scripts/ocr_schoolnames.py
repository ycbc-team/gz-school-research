"""OCR 每页校名列（col2 初中学校）→ 校名序列"""
import pymupdf, cv2, subprocess, json
import numpy as np

PDF = 'data/linkage/raw/quota_detail.pdf'
OUT = 'data/linkage/raw/schoolnames.json'

def ocr_crop(crop):
    if crop.shape[1] < 20:
        crop = cv2.copyMakeBorder(crop, 0, 0, 10, 10, cv2.BORDER_CONSTANT, value=255)
    big = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    p = '/tmp/qgrid2/sn.png'
    cv2.imwrite(p, big)
    out = subprocess.run(['swift', '/tmp/ocr_row.swift', p], capture_output=True, text=True).stdout
    res = []
    for line in out.strip().split('\n'):
        parts = line.split('|')
        if len(parts) >= 5:
            try:
                res.append((float(parts[1]), '|'.join(parts[4:]).strip()))
            except Exception:
                pass
    return res

def detect_rows(gray, H, W):
    _, bw = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
    hlines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, hk)
    rowsum = hlines.sum(axis=1) // 255
    ys = [i for i in range(H) if rowsum[i] > W * 0.15]
    rows = []
    if ys:
        start = prev = ys[0]
        for y in ys[1:]:
            if y - prev > 5:
                rows.append((start + prev) // 2)
                start = y
            prev = y
        rows.append((start + prev) // 2)
    return rows

doc = pymupdf.open(PDF)
out = {}
for pno in range(len(doc)):
    pix = doc[pno].get_pixmap(dpi=300)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    H, W = gray.shape[:2]
    rows = detect_rows(gray, H, W)
    data_rows = [(rows[i], rows[i+1]) for i in range(len(rows)-1)
                 if 50 <= rows[i+1]-rows[i] <= 110 and rows[i] > 350]
    if not data_rows:
        out[str(pno)] = []
        continue
    top = data_rows[0][0]; bottom = data_rows[-1][1]
    # 校名列 = 从左侧第3列起（172-1044 区域，取 391-1044）
    crop = gray[top:bottom, 391:1044]
    res = ocr_crop(crop)
    # 行归属
    names = {}
    for y_norm, txt in res:
        py = top + (1 - y_norm) * (bottom - top)
        best = None; bd = 1e9
        for ri, (r0, r1) in enumerate(data_rows):
            d = abs(py - (r0+r1)/2)
            if d < bd: bd = d; best = ri
        if best is not None and bd < 45:
            if best not in names:
                names[best] = txt
    out[str(pno)] = [names.get(r, '') for r in range(len(data_rows))]
    print(f'页{pno}: {len(data_rows)}校 例:{out[str(pno)][:2]}', flush=True)
json.dump(out, open(OUT, 'w'), ensure_ascii=False)
print('保存', OUT)
