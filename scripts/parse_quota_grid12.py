"""quota_detail.pdf v12：区头行 tesseract 重读 + 不一致行三票投票"""
import pymupdf, cv2, subprocess, json, os, re
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from collections import Counter

PDF = 'data/linkage/raw/quota_detail.pdf'
G11 = 'data/linkage/raw/quota_grid11.json'
OUT = 'data/linkage/raw/quota_grid12.json'
TMP = 'scripts/tmp_ocr'
SZ = 21

def clean(s):
    if not s: return None
    s2 = re.sub(r'[^\dOSIl]', '', str(s)).replace('O','0').replace('o','0').replace('I','1').replace('l','1')
    try: return int(s2) if s2 else None
    except: return None

def ts_one(args):
    key = args
    p = f'{TMP}/{key}.png'
    outs = []
    for _ in range(3):
        out = subprocess.run(['tesseract', p, 'stdout', '--psm', '10', '-c', 'tessedit_char_whitelist=0123456789'],
                             capture_output=True)
        outs.append(out.stdout.decode('utf-8', 'ignore').strip())
    # 众数
    c = Counter(outs)
    best, n = c.most_common(1)[0]
    return key, best if n >= 2 else ''

def main():
    os.makedirs(TMP, exist_ok=True)
    g11 = json.load(open(G11))
    doc = pymupdf.open(PDF)
    # 找出不一致行 + 区头行
    todo = set()
    for pno in sorted(g11, key=int):
        pg = g11[pno]
        if 'data' not in pg or not pg['data']: continue
        nr = len(pg['rows']) // 2
        todo.add((pno, 0))  # 区头行
        for r in range(1, nr):
            sheng = clean(pg['data'].get('1', {}).get(str(r), ''))
            sz = sum(clean(pg['data'].get(str(i+3), {}).get(str(r), '')) or 0 for i in range(SZ))
            if sheng is None or sz != sheng:
                todo.add((pno, r))
    # 准备图
    job = []
    for pno, r in sorted(todo):
        pg = g11[pno]
        rows = pg['rows']
        cols = pg['cols']
        pix = doc[int(pno)].get_pixmap(dpi=300)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        for ci in [1] + list(range(3, 3 + SZ)):
            if ci + 1 >= len(cols): continue
            y0, y1 = rows[r*2], rows[r*2+1]
            x0, x1 = cols[ci] + 5, cols[ci+1] - 5
            if x1 - x0 < 20: continue
            crop = gray[y0+5:y1-5, x0:x1]
            if crop.size == 0: continue
            big = cv2.resize(crop, None, fx=10, fy=10, interpolation=cv2.INTER_CUBIC)
            _, bw = cv2.threshold(big, 150, 255, cv2.THRESH_BINARY)
            key = f'{pno}_{r}_{ci}'
            cv2.imwrite(f'{TMP}/{key}.png', bw)
            job.append(key)
    print('重读格数', len(job), flush=True)
    results = {}
    with ProcessPoolExecutor(max_workers=6) as ex:
        for key, txt in ex.map(ts_one, job):
            results[key] = txt
    filled = 0
    for k, txt in results.items():
        if txt:
            pno, r, ci = k.split('_')
            g11[pno]['data'].setdefault(ci, {})[r] = txt
            filled += 1
    json.dump(g11, open(OUT, 'w'), ensure_ascii=False)
    print(f'保存 {OUT} (有效 {filled}/{len(job)})')

if __name__ == '__main__':
    main()
