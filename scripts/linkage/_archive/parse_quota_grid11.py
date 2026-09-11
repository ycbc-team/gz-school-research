"""quota_detail.pdf v11：tesseract 全量重读（21 省市属列 + col1，并行）"""
import pymupdf, cv2, subprocess, json, os
import numpy as np
from concurrent.futures import ProcessPoolExecutor

PDF = 'data/linkage/raw/quota_detail.pdf'
OUT = 'data/linkage/raw/quota_grid11.json'
TMP = 'scripts/tmp_ocr'
SZ = 21

def ts_one(args):
    pno, r, ci = args
    p = f'{TMP}/{pno}_{r}_{ci}.png'
    out = subprocess.run(['tesseract', p, 'stdout', '--psm', '10', '-c', 'tessedit_char_whitelist=0123456789'],
                         capture_output=True)
    return out.stdout.decode('utf-8', 'ignore').strip()

def prepare():
    os.makedirs(TMP, exist_ok=True)
    doc = pymupdf.open(PDF)
    tasks = []
    pages = {}
    for pno in range(len(doc)):
        pix = doc[pno].get_pixmap(dpi=300)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        # 复用 v10 的网格结构（列界/行界）
        pages[str(pno)] = gray
    g10 = json.load(open('data/linkage/raw/quota_grid10.json'))
    job = []
    for pno in sorted(g10, key=int):
        pg = g10[pno]
        if 'data' not in pg or not pg['data']:
            continue
        gray = pages[pno]
        rows = pg['rows']
        nrows = len(rows) // 2
        cols = pg['cols']
        for r in range(1, nrows):
            for ci in [1] + list(range(3, 3 + SZ)):
                if ci + 1 >= len(cols):
                    continue
                y0, y1 = rows[r*2], rows[r*2+1]
                x0, x1 = cols[ci] + 5, cols[ci+1] - 5
                if x1 - x0 < 20:
                    continue
                crop = gray[y0+5:y1-5, x0:x1]
                if crop.size == 0:
                    continue
                big = cv2.resize(crop, None, fx=10, fy=10, interpolation=cv2.INTER_CUBIC)
                _, bw = cv2.threshold(big, 150, 255, cv2.THRESH_BINARY)
                cv2.imwrite(f'{TMP}/{pno}_{r}_{ci}.png', bw)
                job.append((pno, r, ci))
    json.dump({'job': job}, open(f'{TMP}/job.json', 'w'))
    print('准备完成，任务数', len(job), flush=True)

def main():
    prepare()
    job = json.load(open(f'{TMP}/job.json'))['job']
    results = {}
    with ProcessPoolExecutor(max_workers=6) as ex:
        for (pno, r, ci), txt in zip(job, ex.map(ts_one, job)):
            results[f'{pno}_{r}_{ci}'] = txt
    g10 = json.load(open('data/linkage/raw/quota_grid10.json'))
    filled = 0
    for k, txt in results.items():
        if txt:
            pno, r, ci = k.split('_')
            g10[pno]['data'].setdefault(ci, {})[r] = txt
            filled += 1
    json.dump(g10, open(OUT, 'w'), ensure_ascii=False)
    print(f'保存 {OUT} (有效填充 {filled}/{len(job)})')

if __name__ == '__main__':
    main()
