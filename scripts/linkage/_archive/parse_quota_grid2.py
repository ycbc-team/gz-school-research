"""quota_detail.pdf 全量解析 v2：300dpi 渲染、固定列界、动态行界、按列 Vision OCR"""
import pymupdf, cv2, subprocess, json, os, sys
import numpy as np

PDF = 'data/linkage/raw/quota_detail.pdf'
OUT = 'data/linkage/raw/quota_grid.json'
TMP = '/tmp/qgrid2'
FIXED_COLS = [172, 241, 391, 1044, 1154, 1245, 1354, 1420, 1498, 1567, 1635, 1704,
              1773, 1845, 1917, 1979, 2051, 2123, 2195, 2258, 2320, 2383, 2452, 2520,
              2589, 2667, 2736, 2814, 2889, 2964, 3039, 3114, 3190, 3265, 3340]

def detect_rows(gray, W, H):
    _, bw = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 1))
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
    # 过滤：只保留表格区的连续行组（行高 60-100px）
    return rows

def ocr_crop(crop, fx=4, fy=2):
    if crop.shape[1] < 12:
        crop = cv2.copyMakeBorder(crop, 0, 0, 6, 6, cv2.BORDER_CONSTANT, value=255)
    big = cv2.resize(crop, None, fx=fx, fy=fy, interpolation=cv2.INTER_CUBIC)
    p = f'{TMP}/c.png'
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

def main():
    os.makedirs(TMP, exist_ok=True)
    doc = pymupdf.open(PDF)
    pages = {}
    for pno in range(len(doc)):
        pix = doc[pno].get_pixmap(dpi=300)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        H, W = gray.shape[:2]
        rows = detect_rows(gray, W, H)
        # 数据行 = 行高 60-100 的连续对（表头第一行 226-488 高 262 排除）
        data_rows = []
        for i in range(len(rows)-1):
            h = rows[i+1] - rows[i]
            if 55 <= h <= 105 and rows[i] > 400:
                data_rows.append((rows[i], rows[i+1]))
        if not data_rows:
            pages[str(pno)] = {'rows': rows, 'data': {}, 'note': 'no_table'}
            print(f'页{pno}: 无数据行', flush=True)
            continue
        top = data_rows[0][0]
        bottom = data_rows[-1][1]
        # 数据列：名额考生(1044) 到最后一列
        page_data = {}
        for ci in range(3, len(FIXED_COLS)):
            x1 = FIXED_COLS[ci]
            x2 = FIXED_COLS[ci+1] if ci+1 < len(FIXED_COLS) else W
            if x1 >= W - 20: break
            crop = gray[top:bottom, x1:x2]
            res = ocr_crop(crop)
            cells = {}
            for y_norm, txt in res:
                py = top + (1 - y_norm) * (bottom - top)
                best = None; bd = 1e9
                for ri, (r0, r1) in enumerate(data_rows):
                    d = abs(py - (r0+r1)/2)
                    if d < bd: bd = d; best = ri
                if best is not None and bd < 40:
                    cells.setdefault(best, []).append((py, txt))
            colvals = {}
            for ri, lst in cells.items():
                lst.sort()
                colvals[str(ri)] = ''.join(t for _, t in lst)
            page_data[str(ci-3)] = colvals
        pages[str(pno)] = {'rows': [r for r0, r1 in data_rows for r in (r0, r1)], 'data': page_data}
        print(f'页{pno}: 数据行{len(data_rows)} 列{len(page_data)} 完成', flush=True)
    json.dump(pages, open(OUT, 'w'), ensure_ascii=False)
    print('保存', OUT)

if __name__ == '__main__':
    main()
