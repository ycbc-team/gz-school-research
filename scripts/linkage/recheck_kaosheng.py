#!/usr/bin/env python3
"""定向 OCR 精校 kaosheng：对 quota_matrix 中 kaosheng 为 None/0/存疑的学校，
从官方 PDF 重新渲染对应行的名额单元格，用 Vision OCR 精读数字。

输出: data/linkage/raw/_ocr/kaosheng_recheck.json
"""
import json, pymupdf, cv2, subprocess, os, re
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / 'data/linkage/raw/quota_detail.pdf'
GRID = ROOT / 'data/linkage/raw/quota_grid_final.json'
QUOTA = ROOT / 'data/linkage/quota_matrix.json'
OUTDIR = ROOT / 'data/linkage/raw/_ocr'
OCR_SWIFT = ROOT / 'scripts/linkage/ocr_vision.swift'
RESULT = OUTDIR / 'kaosheng_recheck.json'

OUTDIR.mkdir(parents=True, exist_ok=True)

grid = json.load(open(GRID))
quota = json.load(open(QUOTA))
doc = pymupdf.open(str(PDF))

def ocr_image(img_path, out_json):
    r = subprocess.run(['swift', str(OCR_SWIFT), str(img_path), str(out_json), '0.1'],
                       capture_output=True, text=True, timeout=30)
    if os.path.exists(out_json):
        return json.load(open(out_json))
    return []

def extract_number(text):
    """从 OCR 文本中提取纯数字"""
    digits = re.findall(r'\d+', text.replace('O','0').replace('o','0').replace('l','1').replace('I','1'))
    if digits:
        return int(digits[0])
    return None

def recheck_school(school, idx):
    page = school['page']
    row = school['row']
    old_kao = school['kaosheng']
    
    p = grid[str(page)]
    cols = p['cols']  # col0 = kaosheng
    rows = p['rows']  # [r0top,r0bot,...]
    
    y0 = rows[2*row]
    y1 = rows[2*row+1]
    x0 = cols[0]
    x1 = cols[1] if len(cols) > 1 else cols[0] + 200
    
    # 渲染页面
    pix = doc[page].get_pixmap(dpi=300)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    # 裁剪 kaosheng 单元格（加宽50%防止多位数截断，放大4倍）
    pad = 5
    extra = int((x1 - x0) * 0.5)
    k_crop = gray[max(0,y0-pad):min(gray.shape[0],y1+pad), 
                  max(0,x0-pad-extra):min(gray.shape[1],x1+pad+extra)]
    k_big = cv2.resize(k_crop, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    k_path = OUTDIR / f'k_{idx:03d}.png'
    cv2.imwrite(str(k_path), k_big)
    
    # 裁剪校名区域（用于验证行对应）
    name_x1 = x0
    name_x0 = max(0, x0 - 800)
    n_crop = gray[max(0,y0-pad):min(gray.shape[0],y1+pad), name_x0:name_x1]
    n_big = cv2.resize(n_crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    n_path = OUTDIR / f'n_{idx:03d}.png'
    cv2.imwrite(str(n_path), n_big)
    
    # OCR
    k_items = ocr_image(k_path, OUTDIR / f'k_{idx:03d}.json')
    n_items = ocr_image(n_path, OUTDIR / f'n_{idx:03d}.json')
    
    k_text = ' '.join(it['text'] for it in sorted(k_items, key=lambda x: x['x0']))
    n_text = ' '.join(it['text'] for it in sorted(n_items, key=lambda x: x['x0']))
    
    new_kao = extract_number(k_text)
    
    return {
        'idx': idx,
        'school': school['school'],
        'page': page,
        'row': row,
        'old_kaosheng': old_kao,
        'ocr_raw': k_text,
        'ocr_number': new_kao,
        'name_ocr': n_text[:60],
        'cell_img': str(k_path.relative_to(ROOT)),
        'changed': new_kao is not None and new_kao != old_kao,
    }

def main():
    schools = quota['schools']
    
    # 目标：None + 0 + 用户点名(祈福新邨=189) + 1-5中抽样
    targets = []
    for i, s in enumerate(schools):
        if s['kaosheng'] is None or s['kaosheng'] == 0:
            targets.append((i, s))
        elif '祈福新邨' in s['school']:
            targets.append((i, s))
    
    print(f'目标学校: {len(targets)}所')
    results = []
    for idx, s in targets:
        print(f'  [{idx}] 页{s["page"]}行{s["row"]} {s["school"]} (旧={s["kaosheng"]})...', flush=True)
        try:
            r = recheck_school(s, idx)
            results.append(r)
            status = f'→ OCR=[{r["ocr_raw"]}] 数字={r["ocr_number"]}'
            if r['changed']:
                status += ' ⚠️变更!'
            print(f'    {status}')
        except Exception as e:
            print(f'    失败: {e}')
            results.append({'idx': idx, 'school': s['school'], 'error': str(e)})
    
    json.dump(results, open(RESULT, 'w'), ensure_ascii=False, indent=2)
    print(f'\n结果保存: {RESULT}')
    
    changed = [r for r in results if r.get('changed')]
    confirmed = [r for r in results if r.get('ocr_number') is not None and not r.get('changed')]
    failed = [r for r in results if r.get('ocr_number') is None]
    print(f'变更: {len(changed)}所, 确认不变: {len(confirmed)}所, OCR未识别: {len(failed)}所')

if __name__ == '__main__':
    main()
