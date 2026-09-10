"""quota_detail.pdf v8：单格 OCR（v6 列界 + 对不一致行重读 col1 与 21 省市属列）"""
import pymupdf, cv2, subprocess, json, os, re
import numpy as np

PDF = 'data/linkage/raw/quota_detail.pdf'
G6 = 'data/linkage/raw/quota_grid6.json'
OUT = 'data/linkage/raw/quota_grid8.json'
TMP = '/tmp/qgrid8'
SZ = 21

def clean(s):
    if not s: return None
    s2 = re.sub(r'[^\dOSIl]', '', str(s)).replace('O','0').replace('o','0').replace('I','1').replace('l','1')
    try: return int(s2) if s2 else None
    except: return None

def ocr_crop(crop):
    big = cv2.resize(crop, None, fx=6, fy=4, interpolation=cv2.INTER_CUBIC)
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
    tot_cells = 0
    for pno in sorted(g6, key=int):
        pg = g6[pno]
        if 'data' not in pg or not pg['data']:
            continue
        pix = doc[int(pno)].get_pixmap(dpi=300)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        rows = pg['rows']
        nrows = len(rows) // 2
        cols = pg['cols']   # 列左界，idx0=名额考生
        need = 0
        for r in range(1, nrows):
            sheng = clean(pg['data'].get('1', {}).get(str(r), ''))
            szsum = sum(clean(pg['data'].get(str(i+3), {}).get(str(r), '')) or 0 for i in range(SZ))
            if sheng is not None and szsum == sheng:
                continue
            y0, y1 = rows[r*2], rows[r*2+1]
            # 重读 col1（省市属，cols idx1）与 21 省市属列（cols idx 3..23）
            for ci in list(range(1, 2)) + list(range(3, 3 + SZ)):
                if ci + 1 >= len(cols):
                    continue
                x0 = cols[ci] + 4
                x1 = cols[ci+1] - 4
                if x1 - x0 < 20:
                    continue
                crop = gray[y0+4:y1-4, x0:x1]
                if crop.size == 0:
                    continue
                txt = ocr_crop(crop)
                if txt:
                    pg['data'].setdefault(str(ci-3), {})[str(r)] = txt
                need += 1
                tot_cells += 1
        print(f'页{pno}: 单格重读 {need}', flush=True)
    json.dump(g6, open(OUT, 'w'), ensure_ascii=False)
    print(f'保存 {OUT} (总格 {tot_cells})')

if __name__ == '__main__':
    main()
