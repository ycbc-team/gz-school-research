"""v15：43 个不一致行 col1+21列 三票 tesseract 重读"""
import json, re, subprocess, os
import pymupdf, cv2, numpy as np
from concurrent.futures import ProcessPoolExecutor
from collections import Counter

def clean(s):
    if not s: return None
    s2 = re.sub(r'[^\dOSIl]', '', str(s)).replace('O','0').replace('o','0').replace('I','1').replace('l','1')
    try: return int(s2) if s2 else None
    except: return None

def ts3(key):
    p = f'scripts/tmp_ocr/f2/{key}.png'
    outs = []
    for _ in range(3):
        o = subprocess.run(['tesseract', p, 'stdout', '--psm', '10', '-c', 'tessedit_char_whitelist=0123456789'], capture_output=True)
        outs.append(o.stdout.decode('utf-8', 'ignore').strip())
    c = Counter(outs)
    best, n = c.most_common(1)[0]
    return key, (best if n >= 2 else '')

def main():
    g = json.load(open('data/linkage/raw/quota_grid14.json'))
    bad = json.load(open('scripts/tmp_ocr/bad14.json'))
    doc = pymupdf.open('data/linkage/raw/quota_detail.pdf')
    os.makedirs('scripts/tmp_ocr/f2', exist_ok=True)
    job = []
    for pno, r, sheng, sz in bad:
        pg = g[pno]
        rows = pg['rows']; cols = pg['cols']
        pix = doc[int(pno)].get_pixmap(dpi=300)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        for ci in [1] + list(range(3, 24)):
            if ci + 1 >= len(cols): continue
            y0, y1 = rows[int(r)*2], rows[int(r)*2+1]
            x0, x1 = cols[ci]+5, cols[ci+1]-5
            if x1 - x0 < 20: continue
            crop = gray[y0+5:y1-5, x0:x1]
            if crop.size == 0: continue
            big = cv2.resize(crop, None, fx=10, fy=10, interpolation=cv2.INTER_CUBIC)
            _, bw = cv2.threshold(big, 150, 255, cv2.THRESH_BINARY)
            key = f'{pno}_{r}_{ci}'
            cv2.imwrite(f'scripts/tmp_ocr/f2/{key}.png', bw)
            job.append(key)
    print('格数', len(job), flush=True)
    results = {}
    with ProcessPoolExecutor(max_workers=6) as ex:
        for key, txt in ex.map(ts3, job):
            results[key] = txt
    filled = 0
    for k, txt in results.items():
        if txt:
            pno, r, ci = k.split('_')
            g[pno]['data'].setdefault(ci, {})[r] = txt
            filled += 1
    json.dump(g, open('data/linkage/raw/quota_grid15.json', 'w'), ensure_ascii=False)
    print(f'v15 saved (有效 {filled}/{len(job)})')

if __name__ == '__main__':
    main()
