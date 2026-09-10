"""quota_detail.pdf 全量解析：渲染→行列线检测→按列Vision OCR→矩阵"""
import pymupdf, cv2, subprocess, re, json, os, sys
import numpy as np

PDF = 'data/linkage/raw/quota_detail.pdf'
OUT = 'data/linkage/raw/quota_grid.json'
TMP = '/tmp/qgrid'

def detect_lines(img):
    H, W = img.shape[:2]
    _, bw = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY_INV)
    # 竖线
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
    vlines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, vk)
    colsum = vlines.sum(axis=0) // 255
    xs = [i for i in range(W) if colsum[i] > H * 0.25]
    cols = []
    if xs:
        start = prev = xs[0]
        for x in xs[1:]:
            if x - prev > 4:
                cols.append((start + prev) // 2)
                start = x
            prev = x
        cols.append((start + prev) // 2)
    # 水平线
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
    hlines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, hk)
    rowsum = hlines.sum(axis=1) // 255
    ys = [i for i in range(H) if rowsum[i] > W * 0.25]
    rows = []
    if ys:
        start = prev = ys[0]
        for y in ys[1:]:
            if y - prev > 4:
                rows.append((start + prev) // 2)
                start = y
            prev = y
        rows.append((start + prev) // 2)
    return cols, rows

def ocr_col(crop, scale=4):
    """整列竖带 OCR，返回 [(归一化y, text)]"""
    h, w = crop.shape[:2]
    if w < 10:
        crop = cv2.copyMakeBorder(crop, 0, 0, 8, 8, cv2.BORDER_CONSTANT, value=255)
        w = crop.shape[1]
    big = cv2.resize(crop, None, fx=scale, fy=2, interpolation=cv2.INTER_CUBIC)
    p = f'{TMP}/col.png'
    cv2.imwrite(p, big)
    out = subprocess.run(['swift', '/tmp/ocr_row.swift', p], capture_output=True, text=True).stdout
    res = []
    for line in out.strip().split('\n'):
        parts = line.split('|')
        if len(parts) >= 5:
            try:
                y = float(parts[1])
                txt = '|'.join(parts[4:]).strip()
                if txt:
                    res.append((y, txt))
            except Exception:
                pass
    return res

def main():
    os.makedirs(TMP, exist_ok=True)
    doc = pymupdf.open(PDF)
    pages = {}
    for pno in range(len(doc)):
        pix = doc[pno].get_pixmap(dpi=200)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        cols, rows = detect_lines(gray)
        # 数据区：表头行（第1行）之下
        if len(rows) < 2:
            continue
        top = rows[1]  # 第一条数据行顶线
        bottom = rows[-1]  # 表格底线
        # 数据列：从名额考生列开始（跳过序号/代码/校名 3 列）
        data_cols = cols[3:]
        page_data = {}
        for ci, x1 in enumerate(data_cols):
            xi = cols.index(x1)
            x2 = cols[xi+1] if xi+1 < len(cols) else gray.shape[1]
            crop = gray[top:bottom, x1:x2]
            res = ocr_col(crop)
            # 转行号：行界 rows[1:-1]，每行 75px 左右
            cells = {}
            for y_norm, txt in res:
                py = top + (1 - y_norm) * (bottom - top)
                # 找最近行
                best = None; bd = 1e9
                for ri in range(1, len(rows)-1):
                    d = abs(py - (rows[ri]+rows[ri+1])/2)
                    if d < bd: bd = d; best = ri
                if best is not None:
                    cells.setdefault(best, []).append((py, txt))
            colvals = {}
            for ri, lst in cells.items():
                lst.sort()
                colvals[ri] = ''.join(t for _, t in lst)
            page_data[ci] = colvals
        pages[pno] = {'cols': data_cols, 'rows': rows, 'data': page_data}
        print(f'页{pno}: 列{len(data_cols)} 行{len(rows)} 完成', flush=True)
    json.dump(pages, open(OUT, 'w'), ensure_ascii=False)
    print('保存', OUT)

if __name__ == '__main__':
    main()
