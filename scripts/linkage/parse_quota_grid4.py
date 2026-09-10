"""quota_detail.pdf 全量解析 v3：300dpi、每页动态列界+行界、按列 Vision OCR"""
import pymupdf, cv2, subprocess, json, os
import numpy as np

PDF = 'data/linkage/raw/quota_detail.pdf'
OUT = "data/linkage/raw/quota_grid4.json"
TMP = '/tmp/qgrid3'

def detect(gray, H, W):
    _, bw = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    # 列线：动态阈值（先试 0.25，失败降 0.12）
    for thr in (0.25, 0.15, 0.10):
        vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
        vlines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, vk)
        colsum = vlines.sum(axis=0) // 255
        xs = [i for i in range(W) if colsum[i] > H * thr]
        cols = []
        if xs:
            start = prev = xs[0]
            for x in xs[1:]:
                if x - prev > 4:
                    cols.append((start + prev) // 2)
                    start = x
                prev = x
            cols.append((start + prev) // 2)
        if len(cols) >= 20:
            break
    # 行线
    for thr2 in (0.25, 0.15, 0.10):
        hk = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
        hlines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, hk)
        rowsum = hlines.sum(axis=1) // 255
        ys = [i for i in range(H) if rowsum[i] > W * thr2]
        rows = []
        if ys:
            start = prev = ys[0]
            for y in ys[1:]:
                if y - prev > 5:
                    rows.append((start + prev) // 2)
                    start = y
                prev = y
            rows.append((start + prev) // 2)
        if len(rows) >= 3:
            break
    return cols, rows

def ocr_crop(crop):
    if crop.shape[1] < 12:
        crop = cv2.copyMakeBorder(crop, 0, 0, 6, 6, cv2.BORDER_CONSTANT, value=255)
    big = cv2.resize(crop, None, fx=4, fy=2, interpolation=cv2.INTER_CUBIC)
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
        cols, rows = detect(gray, H, W)
        # 数据行：行高 50-110、表格区内
        data_rows = []
        for i in range(len(rows)-1):
            h = rows[i+1] - rows[i]
            if 50 <= h <= 110 and rows[i] > 350:
                data_rows.append((rows[i], rows[i+1]))
        if len(data_rows) < 1 or len(cols) < 8:
            pages[str(pno)] = {'cols': cols, 'rows': rows, 'data': {}, 'note': 'no_table'}
            print(f'页{pno}: 无表(列{len(cols)}行{len(rows)})', flush=True)
            continue
        top = data_rows[0][0]
        bottom = data_rows[-1][1]
        page_data = {}
        # 数据列：跳过前 3 列（序号/代码/校名）——但有的页序号列窄，先检测前3列是否合理
        for ci in range(3, len(cols)):
            x1 = cols[ci]
            x2 = cols[ci+1] if ci+1 < len(cols) else W; x1p = x1 + 10; x2p = max(x1p + 30, x2 - 10)
            if x1 >= W - 10:
                break
            crop = gray[top:bottom, x1p:x2p]
            res = ocr_crop(crop)
            cells = {}
            for y_norm, txt in res:
                py = top + (1 - y_norm) * (bottom - top)
                best = None; bd = 1e9
                for ri, (r0, r1) in enumerate(data_rows):
                    d = abs(py - (r0+r1)/2)
                    if d < bd: bd = d; best = ri
                if best is not None and bd < 45:
                    cells.setdefault(best, []).append((py, txt))
            colvals = {}
            for ri, lst in cells.items():
                lst.sort()
                colvals[str(ri)] = ''.join(t for _, t in lst)
            page_data[str(ci-3)] = colvals
        pages[str(pno)] = {'cols': cols[3:], 'rows': [r for r0, r1 in data_rows for r in (r0, r1)],
                           'data': page_data}
        print(f'页{pno}: 列{len(page_data)} 行{len(data_rows)} 完成', flush=True)
    json.dump(pages, open(OUT, 'w'), ensure_ascii=False)
    print('保存', OUT)

if __name__ == '__main__':
    main()
