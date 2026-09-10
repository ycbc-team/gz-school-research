#!/usr/bin/env python3
"""P1 教育集团成员覆盖比对（v3 修正版）：
- 区检测：兼容带/不带"区"字（南沙/增城/花都/从化）
- 三种变体匹配：POI带校区后缀 / 集团带区名前缀 / 集团带校区后缀
- 远郊（花都/南沙/增城/从化）单独标注
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def norm_name(s: str) -> str:
    return (s.replace('广州市', '').replace('（', '(').replace('）', ')')
             .replace('(', '').replace(')', '')
             .replace(' ', '').replace('\t', '').replace('\u3000', ''))

def load_json(path):
    with open(os.path.join(ROOT, path), encoding='utf-8') as f:
        return json.load(f)

def load_poi(path):
    d = load_json(path)
    return {norm_name(s['name']): s for s in d.get('schools', [])}

middle = load_poi('data/middle/schools-gz.json')
primary = load_poi('data/primary/schools-gz.json')
high = load_poi('data/high/schools-gz.json')
all_poi = {'初中': middle, '小学': primary, '高中': high}

SEVEN = {'荔湾区', '越秀区', '海珠区', '天河区', '白云区', '黄埔区', '番禺区'}
OUTER = {'花都区', '南沙区', '增城区', '从化区'}
# 不带区字的别名
OUTER_ALIASES = {'花都': '花都区', '南沙': '南沙区', '增城': '增城区', '从化': '从化区'}

def detect_district(name):
    # 先匹配带"区"字
    for d in list(SEVEN) + list(OUTER):
        if d in name:
            return d
    # 再匹配不带"区"字（仅限远郊，避免"黄埔中学"误判）
    for alias, dist in OUTER_ALIASES.items():
        if alias in name:
            return dist
    # 核心校映射
    CORE_DIST = {
        '华南师范大学附属中学': '黄埔区', '广东广雅中学': '荔湾区',
        '广州市第二中学': '越秀区', '广州市第六中学': '海珠区',
        '广东华侨中学': '越秀区', '广州大学附属中学': '越秀区',
        '广州外国语学校': '南沙区', '广州市第一中学': '荔湾区',
        '广州市第四中学': '荔湾区', '广州市西关外国语学校': '荔湾区',
        '广州市真光中学': '荔湾区', '广州市第三中学': '越秀区',
        '广州市培正中学': '越秀区', '广州市第五中学': '海珠区',
        '广州市第九十七中学': '海珠区', '广州市第四十一中学': '海珠区',
        '广州中学': '天河区', '广州奥林匹克中学': '天河区',
        '广州市培英中学': '荔湾区', '广州市第六十五中学': '白云区',
        '广州大同中学': '白云区', '广州市白云中学': '白云区',
        '广东外语外贸大学实验中学': '白云区',
        '广州市第八十六中学': '黄埔区', '广州市玉岩中学': '黄埔区',
        '广州科学城中学': '黄埔区', '广东仲元中学': '番禺区',
        '广东番禺中学': '番禺区',
    }
    for core, dist in CORE_DIST.items():
        if core in name:
            return dist
    return None

CAMPUS_KEYWORDS = ['校区', '分校', '初中部', '高中部', '小学部', '本部',
                    '校本部', '中学部', '东校区', '西校区', '南校区', '北校区',
                    '首校区', '新校区', '实验学校', '学校', '校区)']

def is_campus_suffix(suffix):
    if not suffix or len(suffix) > 15:
        return False
    for kw in CAMPUS_KEYWORDS:
        if kw in suffix:
            return True
    return len(suffix) <= 8  # 短后缀视为校区/地名

def is_district_prefix(prefix):
    if not prefix:
        return False
    if re.search(r'(区|镇|街道|街)$', prefix):
        return True
    return False

def find_variants(name, poi_layer):
    """三种变体匹配"""
    nn = norm_name(name)
    matches = []
    for pnn, poi in poi_layer.items():
        if pnn == nn:
            continue
        # 1. POI 带校区后缀：POI 以集团名开头
        if pnn.startswith(nn) and is_campus_suffix(pnn[len(nn):]):
            matches.append(('POI带校区', poi['name']))
        # 2. 集团带区名前缀：集团名以 POI 名结尾
        elif nn.endswith(pnn) and len(pnn) >= 3 and is_district_prefix(nn[:-len(pnn)]):
            matches.append(('集团带区名', poi['name']))
        # 3. 集团带校区后缀：集团名以 POI 名开头
        elif nn.startswith(pnn) and is_campus_suffix(nn[len(pnn):]):
            matches.append(('集团带校区', poi['name']))
    return matches

def check_school(name):
    nn = norm_name(name)
    result = {'name': name, 'norm_name': nn, 'layers': {}, 'status': '缺失'}
    exact = False
    variant = False
    for layer_name, layer in all_poi.items():
        if nn in layer:
            result['layers'][layer_name] = {'match_type': '精确', 'poi_name': layer[nn]['name']}
            exact = True
        else:
            vs = find_variants(name, layer)
            if vs:
                result['layers'][layer_name] = {
                    'match_type': vs[0][0], 'poi_name': vs[0][1],
                    'all_variants': vs}
                variant = True
    if exact:
        result['status'] = '精确命中'
    elif variant:
        result['status'] = '变体命中'
    else:
        result['status'] = '未命中'
    return result

groups_data = load_json('data/registry/education_groups_2026.json')
results = []
stats = {'精确命中': 0, '变体命中': 0, '未命中': 0, '远郊不在范围': 0}
miss_seven = []
miss_outer = []

for g in groups_data['groups']:
    core = g['core']
    level = g['level']
    core_dist = detect_district(core)
    core_result = check_school(core)
    core_result['district'] = core_dist
    core_result['role'] = '核心校'
    if core_dist in OUTER and core_result['status'] == '未命中':
        core_result['status'] = '远郊不在POI范围'
        stats['远郊不在范围'] += 1
        miss_outer.append(core_result)
    else:
        stats[core_result['status']] += 1
        if core_result['status'] == '未命中':
            miss_seven.append(core_result)

    member_results = []
    for m in g['members']:
        m_dist = detect_district(m)
        mr = check_school(m)
        mr['district'] = m_dist
        mr['role'] = '成员校'
        if m_dist in OUTER and mr['status'] == '未命中':
            mr['status'] = '远郊不在POI范围'
            stats['远郊不在范围'] += 1
            miss_outer.append(mr)
        else:
            stats[mr['status']] += 1
            if mr['status'] == '未命中':
                miss_seven.append(mr)
        member_results.append(mr)
    results.append({'core': core_result, 'level': level, 'members': member_results})

total = sum(stats.values())
print(f'=== 覆盖统计（共 {total} 校）===')
for k, v in stats.items():
    print(f'  {k}: {v}')
print(f'\n=== 7 区内未命中（{len(miss_seven)} 所，需高德核实）===')
for s in miss_seven:
    print(f'  [{s["role"]}][{s["district"]}] {s["name"]}')
print(f'\n=== 远郊不在 POI 范围（{len(miss_outer)} 所）===')
for s in miss_outer:
    print(f'  [{s["role"]}][{s["district"]}] {s["name"]}')

out_path = os.path.join(ROOT, 'scripts/registry/coverage_result.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump({'summary': stats, 'groups': results,
               'miss_seven': miss_seven, 'miss_outer': miss_outer},
              f, ensure_ascii=False, indent=2)
print(f'\n结果已写入 {out_path}')
