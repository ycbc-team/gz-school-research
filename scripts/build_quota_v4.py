# -*- coding: utf-8 -*-
"""名额分配解析 V4：数据驱动列网格 + 全0列插值 + 顺序配对 + 列和校验"""
import json, numpy as np

CLS2DIGIT = {0:0, 1:5, 2:6, 3:3, 4:7, 5:1, 6:0, 7:4, 8:8, 9:2}
# 数字列顺序（去掉序号/代码/初中学校）
COLS = {
 'page_01': ['名额考生','省市名额','区属名额','华附石牌','华附知识城','省实荔湾','省实白云','广雅荔湾','广雅花都','执信越秀','执信天河','二中','六中海珠','六中从化','六中花都','侨中','协和','广附','铁一越秀','铁一番禺','铁一白云','广州外国语','清湾智谷','清湾智慧城','一中','四中','南海中学','西外','真光本部','真光汾水','真光广钢'],
 'page_03': ['名额考生','省市名额','区属名额','华附石牌','华附知识城','省实荔湾','省实白云','广雅荔湾','广雅花都','执信越秀','执信天河','二中','六中海珠','六中从化','六中花都','侨中','协和','广附','铁一越秀','铁一番禺','铁一白云','广州外国语','清湾智谷','清湾智慧城','三中','七中本部','七中麓湖','十三中','十六中本部','十六中水荫','十七中','省实越秀','培正','育才'],
 'page_05': ['名额考生','省市名额','区属名额','华附石牌','华附知识城','省实荔湾','省实白云','广雅荔湾','广雅花都','执信越秀','执信天河','二中','六中海珠','六中从化','六中花都','侨中','协和','广附','铁一越秀','铁一番禺','铁一白云','广州外国语','清湾智谷','清湾智慧城','五中本部','五中金碧','南武本部','南武岭南画派','九十七本部','九十七江南新苑','四十一中','海珠外国语本部','海珠外国语江海'],
 'page_07': ['名额考生','省市名额','区属名额','华附石牌','华附知识城','省实荔湾','省实白云','广雅荔湾','广雅花都','执信越秀','执信天河','二中','六中海珠','六中从化','六中花都','侨中','协和','广附','铁一越秀','铁一番禺','铁一白云','广州外国语','清湾智谷','清湾智慧城','广州中学','七十五中','一一三中金融城','一一三中元岗','八十九中','天河中学','奥林匹克','天外珠江新城','天外智慧城'],
 'page_10': ['名额考生','省市名额','区属名额','华附石牌','华附知识城','省实荔湾','省实白云','广雅荔湾','广雅花都','执信越秀','执信天河','二中','六中海珠','六中从化','六中花都','侨中','协和','广附','铁一越秀','铁一番禺','铁一白云','广州外国语','清湾智谷','清湾智慧城','培英云城','培英鹤洞','六十五中江高','六十五中同德','六十五中江府','大同','白云中学','彭加木','广外实验','空港实验'],
 'page_14': ['名额考生','省市名额','区属名额','华附石牌','华附知识城','省实荔湾','省实白云','广雅荔湾','广雅花都','执信越秀','执信天河','二中','六中海珠','六中从化','六中花都','侨中','协和','广附','铁一越秀','铁一番禺','铁一白云','广州外国语','清湾智谷','清湾智慧城','八十六中','玉岩','科中','石化中学','北师大广实','黄埔开元','广实','黄埔苏元'],
 'page_17': ['名额考生','省市名额','区属名额','华附石牌','华附知识城','省实荔湾','省实白云','广雅荔湾','广雅花都','执信越秀','执信天河','二中','六中海珠','六中从化','六中花都','侨中','协和','广附','铁一越秀','铁一番禺','铁一白云','广州外国语','清湾智谷','清湾智慧城','仲元','番中','番实','象贤','石碁','洛溪新城','禺山','石北','石楼','南村','大龙','二师番禺附中'],
}
DISTRICT = {'page_01':'荔湾区','page_03':'越秀区','page_05':'海珠区','page_07':'天河区','page_10':'白云区','page_14':'黄埔区','page_17':'番禺区'}

digits = json.load(open('data/linkage/raw/digit_clusters/digits_all.json', encoding='utf-8'))
bypage = {}
for d in digits:
    p = d['page'].replace('.png','')
    bypage.setdefault(p, []).append(d)

def cluster_1d(xs, gap):
    xs = sorted(xs)
    if not xs: return []
    groups = [[xs[0]]]
    for x in xs[1:]:
        if x - groups[-1][-1] <= gap: groups[-1].append(x)
        else: groups.append([x])
    return [int(np.mean(g)) for g in groups]

def interpolate_grid(grid, n_expected, colwidth=140):
    """把网格插值到期望列数：大间距处插入等距网格"""
    grid = sorted(grid)
    while len(grid) < n_expected:
        # 找最大间距（且 >= 1.6 倍列宽）
        best_i, best_gap = None, 0
        for i in range(len(grid) - 1):
            gap = grid[i+1] - grid[i]
            if gap > best_gap:
                best_gap = gap; best_i = i
        if best_i is None or best_gap < 1.5 * colwidth:
            break
        # 插入：间距内均分（ceil(gap/colwidth) 段）
        n_seg = max(2, int(round(best_gap / colwidth)))
        for k in range(1, n_seg):
            grid.insert(best_i + k, grid[best_i] + best_gap * k / n_seg)
    return [int(g) for g in grid][:n_expected]

out = {}
for p, cols in COLS.items():
    ds = bypage.get(p, [])
    num_ds = [d for d in ds if d['x'] > 1000]
    col_centers = cluster_1d([d['x'] for d in num_ds], 30)
    n_exp = len(cols)
    if len(col_centers) != n_exp:
        # 检查是否有多余（代码列混入：x<1350 的数字若形成独立列则删）
        if len(col_centers) > n_exp:
            print(f'{p}: 网格 {len(col_centers)} > 期望 {n_exp}，需剔除')
        col_centers = interpolate_grid(col_centers, n_exp)
        print(f'{p}: 网格 {len(col_centers)}（插值后）vs 期望 {n_exp}')
    ys = [d['y'] + d['h']//2 for d in num_ds]
    row_groups = cluster_1d(ys, 40)
    rows = []
    for ry in row_groups:
        row_ds = [d for d in num_ds if abs(d['y'] + d['h']//2 - ry) <= 35]
        cell = {}
        for c_i, cx in enumerate(col_centers):
            cds = [d for d in row_ds if abs(d['x'] - cx) <= 55]
            if not cds: continue
            cds.sort(key=lambda d: d['x'])
            s = ''.join(str(CLS2DIGIT[d['cluster']]) for d in cds)
            if s: cell[cols[c_i]] = s
        rows.append({'y': ry, 'cell': cell})
    out[p] = {'rows': rows, 'col_centers': col_centers}
    # 校验：名额考生列和
    s_q = sum(int(r['cell'].get('名额考生', 0)) for r in rows)
    print(f'{p} {DISTRICT[p]}: {len(rows)} 行, 名额考生列和={s_q}')

json.dump(out, open('data/linkage/raw/quota_v4.json', 'w', encoding='utf-8'), ensure_ascii=False)
