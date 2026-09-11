"""每页标题+表头 OCR，输出 header_ocr 全量"""
import pymupdf, cv2, subprocess, json
import numpy as np

PDF = 'data/linkage/raw/quota_detail.pdf'
OUT = 'data/linkage/raw/headers/header_ocr_all.json'

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
    # 标题区（顶部 100px）放大
    title = cv2.resize(gray[40:140, :], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    tr = ocr(title, f't{pno}')
    # 表头区（226-488 数据第一行前）
    header = cv2.resize(gray[226:470, :], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    hr = ocr(header, f'h{pno}')
    all_pages[str(pno)] = {'title': tr, 'header': hr}
    ttxt = ' '.join(t[2] for t in tr)
    print(f'页{pno}: {ttxt[:40]}', flush=True)
json.dump(all_pages, open(OUT, 'w'), ensure_ascii=False)
print('保存', OUT)
