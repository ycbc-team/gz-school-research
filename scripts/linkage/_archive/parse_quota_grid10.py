"""quota_detail.pdf v10：tesseract 单格补漏（空格 + >10 可疑值重读）"""
import pymupdf, cv2, subprocess, json, os, re
import numpy as np

PDF = 'data/linkage/raw/quota_detail.pdf'
G9 = 'data/linkage/raw/quota_grid9.json'
OUT = 'data/linkage/raw/quota_grid10.json'
TMP = 'scripts/tmp_ocr'
SZ = 21

def clean(s):
    if not s: return None
    s2 = re.sub(r'[^\dOSIl]', '', str(s)).replace('O','0').replace('o','0').replace('I','1').replace('l','1')
    try: return int(s2) if s2 else None
    except: return None

def ts_crop(crop):
    big = cv2.resize(crop, None, fx=8, fy=8, interpolation=cv2.INTER_CUBIC)
    _, bw = cv2.threshold(big, 150, 255, cv2.THRESH_BINARY)
    p = f'{TMP}/t.png'
    cv2.imwrite(p, bw)
    out = subprocess.run(['tesseract', p, 'stdout', '--psm', '10', '-c', 'tessedit_char_whitelist=0123456789'],
                         capture_output=True)
    return out.stdout.decode('utf-8', 'ignore').strip()

def main():
    os.makedirs(TMP, exist_ok=True)
    g9 = json.load(open(G9))
    doc = pymupdf.open(PDF)
    tot = 0
    for pno in sorted(g9, key=int):
        pg = g9[pno]
        if 'data' not in pg or not pg['data']:
            continue
        pix = doc[int(pno)].get_pixmap(dpi=300)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        rows = pg['rows']
        nrows = len(rows) // 2
        cols = pg['cols']
        n = 0
        for r in range(1, nrows):
            for ci in [1] + list(range(3, 3 + SZ)):
                if ci + 1 >= len(cols):
                    continue
                key = str(ci)
                v = clean(pg['data'].get(key, {}).get(str(r), ''))
                if v is not None and v <= 10:
                    continue  # 非空且合理，跳过
                y0, y1 = rows[r*2], rows[r*2+1]
                x0, x1 = cols[ci] + 5, cols[ci+1] - 5
                if x1 - x0 < 20:
                    continue
                crop = gray[y0+5:y1-5, x0:x1]
                if crop.size == 0:
                    continue
                txt = ts_crop(crop)
                if txt:
                    pg['data'].setdefault(key, {})[str(r)] = txt
                n += 1
                tot += 1
        print(f'页{pno}: tesseract 重读 {n}', flush=True)
    json.dump(g9, open(OUT, 'w'), ensure_ascii=False)
    print(f'保存 {OUT} (总格 {tot})')

if __name__ == '__main__':
    main()
