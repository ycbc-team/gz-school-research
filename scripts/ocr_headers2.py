"""标题+表头分块 OCR v2"""
import pymupdf, cv2, subprocess, json
import numpy as np

PDF = 'data/linkage/raw/quota_detail.pdf'
OUT = 'data/linkage/raw/headers/header_ocr_all2.json'

def ocr(img, tag):
    p = f'/tmp/qgrid2/h_{tag}.png'
    cv2.imwrite(p, img)
    out = subprocess.run(['swift', '/tmp/ocr_row.swift', p], capture_output=True, text=True).stdout
    res = []
    for line in out.strip().split('\n'):
        parts = line.split('|')
        if len(parts) >= 5:
            try:
                x = float(parts[0]); y = float(parts[1])
                res.append((x, y, '|'.join(parts[4:]).strip()))
            except Exception:
                pass
    return res

doc = pymupdf.open(PDF)
all_pages = {}
for pno in range(len(doc)):
    pix = doc[pno].get_pixmap(dpi=300)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    H, W = gray.shape[:2]
    # 标题区 100-210
    title = cv2.resize(gray[100:210, :], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    tr = [(x + 0, y, t) for x, y, t in ocr(title, f't{pno}')]
    # 表头 226-470 分 4 块
    hr = []
    for bi in range(4):
        x0 = bi * 880
        x1 = min((bi+1) * 880, W)
        blk = cv2.resize(gray[226:470, x0:x1], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        for x, y, t in ocr(blk, f'h{pno}_{bi}'):
            hr.append((x0/1000 + x*880/1000, y, t))
    all_pages[str(pno)] = {'title': tr, 'header': hr}
    ttxt = ' '.join(t for _, _, t in tr)
    print(f'页{pno}: 标题={ttxt[:45]!r} 表头{len(hr)}', flush=True)
json.dump(all_pages, open(OUT, 'w'), ensure_ascii=False)
print('保存', OUT)
