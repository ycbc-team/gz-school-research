"""OCR 名额分配 PDF 表头列名（竖排）→ 每页每列的高中名。

落盘版：不依赖 /tmp 临时脚本。按 grid 的列分隔线 x 坐标 crop 每列表头，
逐列用 tesseract chi_sim 竖排识别。输出 data/linkage/raw/_ocr/col_headers.json。
"""
import pymupdf, cv2, subprocess, json, os, sys
import numpy as np

PDF = 'data/linkage/raw/quota_detail.pdf'
GRID = 'data/linkage/raw/quota_grid_final.json'
OUTDIR = 'data/linkage/raw/_ocr'
os.makedirs(OUTDIR, exist_ok=True)

def ocr_col(img):
    p = f'{OUTDIR}/_col.png'
    cv2.imwrite(p, img)
    out = subprocess.run(['tesseract', p, 'stdout', '-l', 'chi_sim', '--psm', '5'],
                         capture_output=True, text=True).stdout
    return ''.join(out.split())

doc = pymupdf.open(PDF)
g = json.load(open(GRID))
result = {}
for pno in sorted(g, key=int):
    cols = g[pno]['cols']  # 列分隔线 x（像素，300dpi）
    ncols = len(cols) - 1
    # 表头区 y：数据第一行之前。先整页渲染，表头约在 y<1000（300dpi）
    pix = doc[int(pno)].get_pixmap(dpi=300)
    im = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    gray = cv2.cvtColor(im, cv2.COLOR_RGB2GRAY) if im.shape[2] == 3 else im
    # 表头竖排文字从页面顶部一直延伸，取 40~1400
    y0, y1 = 40, 1400
    names = {}
    for i in range(ncols):
        cx0, cx1 = cols[i], cols[i+1]
        crop = gray[y0:y1, cx0:cx1]
        if crop.shape[1] < 10: continue
        txt = ocr_col(crop)
        if txt:
            names[i] = txt
    result[pno] = names
    print(f'页{pno}: {len(names)}列  例:{ {k: names[k] for k in list(names)[:6]} }', flush=True)

json.dump(result, open(f'{OUTDIR}/col_headers.json', 'w'), ensure_ascii=False, indent=1)
print('保存', f'{OUTDIR}/col_headers.json')
