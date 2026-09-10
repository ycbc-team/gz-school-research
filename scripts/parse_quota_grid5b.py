"""quota_detail.pdf 全量解析 v5：行段 OCR + box 分列"""
import pymupdf, cv2, subprocess, json, os
import numpy as np

PDF = 'data/linkage/raw/quota_detail.pdf'
OUT = 'data/linkage/raw/quota_grid5b.json'
TMP = '/tmp/qgrid5'
SEG_W = 900  # 每段像素宽（含 ~13 列）

def detect(gray, H, W):
    _, bw = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    cols = []
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
    rows = []
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
        # 去重：差 < 10 合并
        dedup = []
        for r in rows:
            if dedup and r - dedup[-1] < 10:
                dedup[-1] = (dedup[-1] + r) // 2
            else:
                dedup.append(r)
        rows = dedup
        if len(rows) >= 3:
            break
    return cols, rows

def ocr_crop(crop, fx, fy):
    big = cv2.resize(crop, None, fx=fx, fy=fy, interpolation=cv2.INTER_CUBIC)
    p = f'{TMP}/s.png'
    cv2.imwrite(p, big)
    out = subprocess.run(['swift', '/tmp/ocr_row.swift', p], capture_output=True, text=True).stdout
    res = []
    for line in out.strip().split('\n'):
        parts = line.split('|')
        if len(parts) >= 5:
            try:
                res.append((float(parts[0]), float(parts[1]), float(parts[2]), '|'.join(parts[4:]).strip()))
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
        data_rows = []
        for i in range(len(rows)-1):
            h = rows[i+1] - rows[i]
            if 50 <= h <= 110 and rows[i] > 350:
                data_rows.append((rows[i], rows[i+1]))
        if len(data_rows) < 1 or len(cols) < 10:
            pages[str(pno)] = {'cols': cols, 'rows': rows, 'data': {}, 'note': 'no_table'}
            print(f'页{pno}: 无表(列{len(cols)}行{len(rows)})', flush=True)
            continue
        # 数据列区域：从名额考生列（第4列）起
        data_x0 = cols[3]
        # 每行分 3 段（每段约 900px 覆盖数据区）
        page_data = {str(c): {} for c in range(len(cols)-3)}
        nseg = max(1, (int(W) - data_x0) // SEG_W + 1)
        for ri, (r0, r1) in enumerate(data_rows):
            yc = (r0 + r1) // 2
            for si in range(nseg):
                sx = data_x0 + si * SEG_W
                ex = min(sx + SEG_W, W)
                if sx >= W - 5: break
                crop = gray[max(r0, 350):r1, sx:ex]
                # fx: 段宽 -> 3 倍
                res = ocr_crop(crop, 3, 3)
                for x_n, y_n, w_n, txt in res:
                    if not txt: continue
                    px = sx + (x_n + w_n/2) * (ex - sx)
                    py = max(r0, 350) + y_n * (r1 - max(r0, 350))
                    if abs(py - yc) > 40: continue
                    # 列归属：找最近列界
                    best = None; bd = 1e9
                    for ci in range(3, len(cols)-1):
                        cx = (cols[ci] + cols[ci+1]) / 2
                        d = abs(px - cx)
                        if d < bd: bd = d; best = ci - 3
                    if best is not None and bd < 80:
                        k = str(best)
                        if k not in page_data:
                            page_data[k] = {}
                        if str(ri) not in page_data[k]:
                            page_data[k][str(ri)] = []
                        page_data[k][str(ri)].append((px, txt))
        # 同格多 box 拼接
        for k in page_data:
            for rk in page_data[k]:
                page_data[k][rk].sort()
                page_data[k][rk] = ''.join(t for _, t in page_data[k][rk])
        pages[str(pno)] = {'cols': cols[3:], 'rows': [r for r0, r1 in data_rows for r in (r0, r1)],
                           'data': page_data}
        print(f'页{pno}: 列{len(page_data)} 行{len(data_rows)} 完成', flush=True)
    json.dump(pages, open(OUT, 'w'), ensure_ascii=False)
    print('保存', OUT)

if __name__ == '__main__':
    main()
