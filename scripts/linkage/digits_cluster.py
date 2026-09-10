# -*- coding: utf-8 -*-
"""提取全量数字连通域 → KMeans 聚类成 10 类 → 输出类代表 cell 供确认"""
import cv2, numpy as np, os, json

PNG_DIR = 'data/linkage/raw/vision_pages'
OUT_DIR = 'data/linkage/raw/digit_clusters'
os.makedirs(OUT_DIR, exist_ok=True)

def extract_row_digits(img, y0, y1, x_min=1000):
    """去表格线，提取 y0-y1 行内 x>x_min 的数字连通域"""
    _, bw = cv2.threshold(img, 160, 255, cv2.THRESH_BINARY_INV)
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (80, 1))
    horiz = cv2.morphologyEx(bw, cv2.MORPH_OPEN, hk)
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    vert = cv2.morphologyEx(bw, cv2.MORPH_OPEN, vk)
    clean = cv2.subtract(bw, horiz)
    clean = cv2.subtract(clean, vert)
    row = clean[y0:y1, :]
    n, labels, stats, cent = cv2.connectedComponentsWithStats(row)
    out = []
    for s in stats[1:]:
        if s[4] > 10 and s[3] > 12 and s[2] > 3 and s[0] >= x_min:
            x, y, w, h = s[0], s[1], s[2], s[3]
            crop = row[y:y+h, x:x+w]
            c28 = cv2.resize(crop, (28, 28), interpolation=cv2.INTER_AREA)
            out.append({'x': x, 'y': y0 + y, 'w': w, 'h': h,
                        'feat': (c28 > 0).astype(float).flatten(), 'src': img})
    return out

def kmeans(X, k, iters=30, seed=0, retry=8):
    best = None
    for s in range(retry):
        rng = np.random.RandomState(seed + s)
        centers = X[rng.choice(len(X), k, replace=False)]
        for _ in range(iters):
            d = np.linalg.norm(X[:, None] - centers[None], axis=2)
            labels = d.argmin(1)
            newc = np.array([X[labels == i].mean(0) if (labels == i).any() else centers[i] for i in range(k)])
            if np.allclose(newc, centers): break
            centers = newc
        # 评估：类大小均衡度
        sizes = np.bincount(labels, minlength=k)
        score = sizes.min()
        if best is None or score > best[0]:
            best = (score, labels, centers)
    return best[1], best[2]

# 行结构：每页用水平线检测
def get_row_lines(img):
    _, bw = cv2.threshold(img, 160, 255, cv2.THRESH_BINARY_INV)
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (80, 1))
    horiz = cv2.morphologyEx(bw, cv2.MORPH_OPEN, hk)
    vals = np.where(horiz.sum(axis=1) > 1500)[0]
    lines = []
    for v in vals:
        if lines and v - lines[-1] <= 8: lines[-1] = v
        else: lines.append(v)
    return lines

all_digits = []
for p in sorted(os.listdir(PNG_DIR)):
    if not p.endswith('.png'): continue
    img = cv2.imread(os.path.join(PNG_DIR, p), cv2.IMREAD_GRAYSCALE)
    lines = get_row_lines(img)
    # 数据行：跳过表头（前 3 条线内），行对 (line[i], line[i+1])
    for i in range(1, len(lines) - 1):
        y0, y1 = lines[i] + 2, lines[i+1] - 2
        if y1 - y0 < 50: continue
        for d in extract_row_digits(img, y0, y1):
            d['page'] = p
            all_digits.append(d)
print('总数字连通域:', len(all_digits))
X = np.array([d['feat'] for d in all_digits])
labels, centers = kmeans(X, 10)
for i, d in enumerate(all_digits):
    d['cluster'] = int(labels[i])
# 每类选代表（离质心最近），保存 cell
os.makedirs(f'{OUT_DIR}/reps', exist_ok=True)
for c in range(10):
    idx = [i for i, l in enumerate(labels) if l == c]
    if not idx: continue
    dist = np.linalg.norm(X[idx] - centers[c], axis=1)
    rep = idx[dist.argmin()]
    d = all_digits[rep]
    img = cv2.imread(os.path.join(PNG_DIR, d['page']), cv2.IMREAD_GRAYSCALE)
    pad = 8
    cell = img[d['y']-pad:d['y']+d['h']+pad, d['x']-pad:d['x']+d['w']+pad]
    cell4 = cv2.resize(cell, None, fx=8, fy=8, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(f'{OUT_DIR}/reps/cls{c}_n{len(idx)}.png', cell4)
    print(f'类{c}: {len(idx)} 个, 代表已存')
clean_d = []
for d in all_digits:
    r = {}
    for k, v in d.items():
        if k in ('feat', 'src'): continue
        if isinstance(v, (np.integer,)): v = int(v)
        elif isinstance(v, (np.floating,)): v = float(v)
        r[k] = v
    clean_d.append(r)
json.dump(clean_d, open(f'{OUT_DIR}/digits_all.json', 'w', encoding='utf-8'), ensure_ascii=False)
np.save(f'{OUT_DIR}/digits_labels.npy', labels)
print('done')
