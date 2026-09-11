"""quota_detail.pdf v7：单格 OCR（对 v6 校验不一致的行重读 22 格：col1 + 21 省市属）"""
import pymupdf, cv2, subprocess, json, os, re
import numpy as np

PDF = 'data/linkage/raw/quota_detail.pdf'
G6 = 'data/linkage/raw/quota_grid6.json'
OUT = 'data/linkage/raw/quota_grid7.json'
TMP = '/tmp/qgrid7'
SZ = 21

def clean(s):
    if not s: return None
    s2 = re.sub(r'[^\dOSIl]', '', str(s)).replace('O','0').replace('o','0').replace('I','1').replace('l','1')
    try: return int(s2) if s2 else None
    except: return None

def ocr_crop(crop, fx=6, fy=4):
    big = cv2.resize(crop, None, fx=fx, fy=fy, interpolation=cv2.INTER_CUBIC)
    p = f'{TMP}/c.png'
    cv2.imwrite(p, big)
    out = subprocess.run(['swift', '/tmp/ocr_row.swift', p], capture_output=True, text=True).stdout
    txts = []
    for line in out.strip().split('\n'):
        parts = line.split('|')
        if len(parts) >= 5:
            txts.append('|'.join(parts[4:]).strip())
    return ''.join(txts)

def main():
    os.makedirs(TMP, exist_ok=True)
    g6 = json.load(open(G6))
    doc = pymupdf.open(PDF)
    for pno in g6:
        pg = g6[pno]
        if 'data' not in pg or not pg['data']:
            continue
        pix = doc[int(pno)].get_pixmap(dpi=300)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        rows = pg['rows']
        nrows = len(rows) // 2
        cols_all = [172] + [0] * (len(pg['cols']) + 3)
        # cols_all[3:] = pg['cols']（列左界），cols_all[i] 与 cols_all[i+1] 为界
        cols = pg['cols']
        # 重建完整列界：col 0-2 需要前 3 列的界（不在 cols 中，用检测）
        # 直接用 v6 存储的 cols（从 col3 起）→ 需要 col0-2 的界：从灰度重新检测不可靠
        # 方案：cols 是"第 3 列起的左界"，第 2 列的右界 = cols[0]
        # 但 col1/col2 的左右界未知 → 用近似：col2 左界 = cols[0] - 90（区属列宽~90-110）
        # 更稳：直接重新检测列线
        _, bw = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
        vlines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, vk)
        colsum = vlines.sum(axis=0) // 255
        H, W = gray.shape[:2]
        xs = [i for i in range(W) if colsum[i] > H * 0.15]
        lins = []
        if xs:
            start = prev = xs[0]
            for x in xs[1:]:
                if x - prev > 4:
                    lins.append((start + prev) // 2)
                    start = x
                prev = x
            lins.append((start + prev) // 2)
        # lins 应 ≈ len(cols)+3 条列线
        # 逐行逐列：只处理 col1 和 col3..col3+SZ-1
        need = 0
        for r in range(1, nrows):
            sheng = clean(pg['data'].get('1', {}).get(str(r), ''))
            szsum = sum(clean(pg['data'].get(str(i+3), {}).get(str(r), '')) or 0 for i in range(SZ))
            if sheng is not None and szsum == sheng:
                continue
            y0, y1 = rows[r*2], rows[r*2+1]
            for ci in range(3, 3 + SZ + 1):  # col1 与 21 省市属列
                if ci >= len(lins) - 1:
                    continue
                x0 = lins[ci] + 5
                x1 = lins[ci+1] - 5
                if x1 - x0 < 20:
                    continue
                crop = gray[y0+4:y1-4, x0:x1]
                if crop.size == 0:
                    continue
                txt = ocr_crop(crop)
                if txt:
                    pg['data'].setdefault(str(ci-3), {})[str(r)] = txt
                need += 1
        print(f'页{pno}: 单格重读 {need}', flush=True)
    json.dump(g6, open(OUT, 'w'), ensure_ascii=False)
    print('保存', OUT)

if __name__ == '__main__':
    main()
