#!/usr/bin/env python3
"""
综合落盘脚本：为 57 项需补实体添加 POI + 实体 + nature='民办' + MINBAN_IDS。

策略：
- 对可复用同校其他学段坐标的项，查找现有 POI 复用 lng/lat，POI 名与现有 POI 一致（同名同 school_id）
- 对高德查询到坐标的新校，使用查询到的坐标
- 对无法定位的，标记为 SKIP，不写入
- entities.json 保持手工最小补丁：按 school_id+stage 添加实体行
- MINBAN_IDS 同步更新
"""
import json
import hashlib
import re
import os
import copy

ROOT = "/Users/bytedance/Developer/gz_school_research"

# 统一匹配库：norm 本体收敛至 school_match.normName（NFKC/繁简/去广州市/删括号/去空白）
sys.path.insert(0, os.path.join(ROOT, "scripts/registry"))
from school_match import normName as norm_name

def id_key(adcode, poi_name):
    norm = norm_name(poi_name)
    h = hashlib.sha1(f'{adcode}|{norm}'.encode()).hexdigest()[:8]
    return f'gz-{adcode}-{h}'

# 加载所有 POI
poi_data = {}
poi_by_name_stage = {}  # (norm_name, stage) -> poi
for stage in ['primary', 'middle', 'high']:
    path = os.path.join(ROOT, f'data/poi/dist/{stage}_poi.json')
    with open(path) as f:
        d = json.load(f)
    poi_data[stage] = d
    for s in d.get('schools', []):
        key = (norm_name(s['name']), stage)
        poi_by_name_stage[key] = s

# 加载实体
with open(os.path.join(ROOT, 'data/registry/entities.json')) as f:
    entities_data = json.load(f)
entities = entities_data['entities']
ent_by_id_stage = {}  # (school_id, stage) -> entity
for e in entities:
    ent_by_id_stage[(e['school_id'], e['stage'])] = e

def find_existing_poi(adcode, lookup_name, target_stage):
    """在其他学段查找同校 POI，返回 (poi, matched_stage)。"""
    norm_lookup = norm_name(lookup_name)
    # 去掉学段后缀后匹配
    base = re.sub(r'(小学部|初中部|高中部|中学部)$', '', norm_lookup)
    for stage in ['primary', 'middle', 'high']:
        if stage == target_stage:
            continue
        for (nname, st), poi in poi_by_name_stage.items():
            if st != stage or poi.get('adcode') != adcode:
                continue
            if nname == norm_lookup or (base and base in nname) or (nname and nname in base):
                return poi, stage
    return None, None

# ============================================================
# 定义全部待补项
# 每项: {lookup_name, target_stage, adcode, poi_name_override, lng, lat, source, note}
# lookup_name: 用于查找现有 POI 的名称
# poi_name_override: 如指定，覆盖 POI 名（用于新校）
# lng/lat: 如指定，使用硬编码坐标（高德查询结果）；否则从现有 POI 复用
# ============================================================

PENDING = [
    # === 荔湾 12 项 ===
    {"lookup_name": "芳华中学", "target_stage": "primary", "adcode": "440103", "poi_name_override": "芳华小学", "source": "独立民办小学，与芳华初中同址但办学许可独立"},
    {"lookup_name": "博雅实验学校", "target_stage": "primary", "adcode": "440103", "poi_name_override": "广州市荔湾区博雅实验学校", "lng": 113.195313, "lat": 23.080770, "source": "高德：海北博雅实验学校，裕海路234号（注意：官方地址裕海路157号，候选为裕海路234号，待确认）"},
    {"lookup_name": "海龙博雅中英文学校", "target_stage": "primary", "adcode": "440103", "poi_name_override": "海龙博雅中英文学校", "lng": 113.181584, "lat": 23.064363, "source": "高德精确匹配：海龙路303号"},
    {"lookup_name": "君诚博雅实验学校", "target_stage": "primary", "adcode": "440103", "poi_name_override": "君诚博雅实验学校(滘口校区)", "source": "滘口校区，五眼桥滘口村377号，2026未招生但仍在册"},
    {"lookup_name": "爱莎文华", "target_stage": "high", "adcode": "440103", "poi_name_override": "广州荔湾爱莎文华学校", "lng": 113.191334, "lat": 23.059218, "source": "高德：爱莎国际学校，海龙路238号（爱莎文华=爱莎国际同一办学主体）"},
    {"lookup_name": "新晖学校", "target_stage": "primary", "adcode": "440103", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "广豪学校", "target_stage": "primary", "adcode": "440103", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "荔广实验学校", "target_stage": "primary", "adcode": "440103", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "东沙博雅实验学校", "target_stage": "primary", "adcode": "440103", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "博雅中英文学校", "target_stage": "primary", "adcode": "440103", "source": "九年制，复用初中部坐标（海中校区=海龙路）"},
    {"lookup_name": "君诚博雅实验学校", "target_stage": "primary", "adcode": "440103", "poi_name_override": "君诚博雅实验学校", "source": "山村校区，九年制，复用初中部坐标"},
    {"lookup_name": "爱莎文华", "target_stage": "primary", "adcode": "440103", "poi_name_override": "广州荔湾爱莎国际学校", "source": "爱莎文华小学部，复用初中部坐标（爱莎国际学校）"},

    # === 越秀 1 项 ===
    {"lookup_name": "雄鹰学校", "target_stage": "primary", "adcode": "440104", "poi_name_override": "雄鹰学校(小学部)", "source": "九年制，复用初中部坐标，云泉路163号大院"},

    # === 海珠 8 项 ===
    {"lookup_name": "为明学校", "target_stage": "primary", "adcode": "440105", "poi_name_override": "广州市为明学校(光大校区)", "lng": 113.257384, "lat": 23.083256, "source": "高德：为明学校光大校区，沙渡路131号（小初部，与罗马校区高中部不同址）"},
    {"lookup_name": "为明学校", "target_stage": "middle", "adcode": "440105", "poi_name_override": "广州市为明学校(光大校区)", "lng": 113.257384, "lat": 23.083256, "source": "同上，光大校区初中部"},
    {"lookup_name": "华洲实验学校", "target_stage": "primary", "adcode": "440105", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "育华学校", "target_stage": "primary", "adcode": "440105", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "华海双语学校", "target_stage": "primary", "adcode": "440105", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "华立学校", "target_stage": "middle", "adcode": "440105", "poi_name_override": "华立学校", "lng": 113.358600, "lat": 23.091206, "source": "高德精确匹配：赤沙村汾阳北大街三号之一（与华立小学南州路不同址，赤沙校区为中学部）"},
    {"lookup_name": "春晖小学", "target_stage": "primary", "adcode": "440105", "poi_name_override": "春晖学校", "lng": 113.290144, "lat": 23.086162, "source": "高德：春晖学校，凤岗路10号（2024年检名春晖学校，2026派位名春晖小学）"},
    {"lookup_name": "贝赛思学校", "target_stage": "primary", "adcode": "440105", "poi_name_override": "广州贝赛思学校(琶洲)", "lng": 113.387334, "lat": 23.096277, "source": "高德：新港东路1716号，2026新增民办小学"},

    # === 天河 18 项 ===
    {"lookup_name": "华美英语实验学校", "target_stage": "primary", "adcode": "440106", "source": "十二年制，复用初中部坐标"},
    {"lookup_name": "思源学校", "target_stage": "middle", "adcode": "440106", "source": "十二年制，复用高中部坐标"},
    {"lookup_name": "东风学校", "target_stage": "primary", "adcode": "440106", "poi_name_override": "东风学校", "lng": 113.321440, "lat": 23.166043, "source": "高德精确匹配：银利街35号（注意与东风实验小学不同校）"},
    {"lookup_name": "东风学校", "target_stage": "middle", "adcode": "440106", "poi_name_override": "东风学校", "lng": 113.321440, "lat": 23.166043, "source": "同上，九年制初中部"},
    {"lookup_name": "同仁学校", "target_stage": "primary", "adcode": "440106", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "同仁天兴学校", "target_stage": "primary", "adcode": "440106", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "成龙中学", "target_stage": "primary", "adcode": "440106", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "棠福学校", "target_stage": "primary", "adcode": "440106", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "东泰学校", "target_stage": "primary", "adcode": "440106", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "天泽中学", "target_stage": "primary", "adcode": "440106", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "培智学校", "target_stage": "middle", "adcode": "440106", "source": "九年制，复用小学部坐标"},
    {"lookup_name": "凤凰中学", "target_stage": "primary", "adcode": "440106", "poi_name_override": "凤凰中学", "lng": 113.393438, "lat": 23.199613, "source": "高德精确匹配：柯木塱大坪街19号（凤凰中学已有middle POI，同名同school_id，注意不是广州中学凤凰校区）"},
    {"lookup_name": "科韵路学校", "target_stage": "primary", "adcode": "440106", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "明珠中英文学校", "target_stage": "primary", "adcode": "440106", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "龙圣学校", "target_stage": "primary", "adcode": "440106", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "兴华培智学校", "target_stage": "primary", "adcode": "440106", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "黄村中英文学校", "target_stage": "primary", "adcode": "440106", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "天骄中英文学校", "target_stage": "primary", "adcode": "440106", "source": "九年制，复用初中部坐标"},

    # === 白云 8 项 ===
    {"lookup_name": "春蕾小学", "target_stage": "primary", "adcode": "440111", "poi_name_override": "春蕾小学", "lng": 113.265090, "lat": 23.186764, "source": "高德：萧岗礼堂南街，无现有POI"},
    {"lookup_name": "白云实验学校", "target_stage": "primary", "adcode": "440111", "poi_name_override": "省实白云实验学校", "source": "即省实白云实验学校，复用初中部坐标（夏茅沙园坊十字大街58号）"},
    {"lookup_name": "广云外国语学校", "target_stage": "primary", "adcode": "440111", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "嘉禾新都学校", "target_stage": "primary", "adcode": "440111", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "源雅学校", "target_stage": "primary", "adcode": "440111", "source": "完全中学，复用初高中部坐标"},
    {"lookup_name": "龙涛外国语实验学校", "target_stage": "primary", "adcode": "440111", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "实验外语学校", "target_stage": "primary", "adcode": "440111", "source": "十二年制，复用高中部坐标（广花一路599号）"},
    {"lookup_name": "颐和第二实验小学", "target_stage": "primary", "adcode": "440111", "SKIP": True, "source": "高德无结果，疑似已停办或名称变更，暂不补"},

    # === 黄埔 8 项 ===
    {"lookup_name": "天健学校", "target_stage": "middle", "adcode": "440112", "poi_name_override": "广州市天健学校", "lng": 113.496570, "lat": 23.209317, "source": "高德精确匹配：长贤路103号，2025年升格完全中学"},
    {"lookup_name": "天健学校", "target_stage": "high", "adcode": "440112", "poi_name_override": "广州市天健学校", "lng": 113.496570, "lat": 23.209317, "source": "同上，2025年新增高中部"},
    {"lookup_name": "新侨学校", "target_stage": "primary", "adcode": "440112", "source": "十二年制，复用初中部坐标（知识城慈济路2号）"},
    {"lookup_name": "新侨学校", "target_stage": "high", "adcode": "440112", "source": "十二年制，复用初中部坐标"},
    {"lookup_name": "中黄外国语实验学校", "target_stage": "primary", "adcode": "440112", "source": "九年制，复用初中部坐标（保金路36号，注意实体名含丰巢快递柜误植）"},
    {"lookup_name": "东晖学校", "target_stage": "primary", "adcode": "440112", "source": "九年制，复用初中部坐标"},
    {"lookup_name": "华外同文外国语学校", "target_stage": "primary", "adcode": "440112", "source": "九年制，复用初中部坐标（科学大道2号）"},
    {"lookup_name": "南方中英文学校", "target_stage": "primary", "adcode": "440112", "source": "九年制，复用初中部坐标（长岭路83号）"},

    # === 番禺 2 项 ===
    {"lookup_name": "博萃德学校", "target_stage": "high", "adcode": "440113", "source": "九年制→2025新增高中，复用小学部坐标"},
    {"lookup_name": "加拿达外国语学校", "target_stage": "primary", "adcode": "440113", "poi_name_override": "加拿达外国语学校(剑桥郡校区)", "source": "九年制，复用初中部坐标（南村镇剑桥郡花园内）"},
]

# ============================================================
# 执行落盘
# ============================================================
added_poi = []
added_entity = []
skipped = []
already_exists = []

for item in PENDING:
    if item.get('SKIP'):
        skipped.append(item)
        continue

    target_stage = item['target_stage']
    adcode = item['adcode']
    lookup_name = item['lookup_name']

    # 确定 POI 名
    poi_name = item.get('poi_name_override')
    if not poi_name:
        # 查找现有 POI 以获取名称
        existing_poi, existing_stage = find_existing_poi(adcode, lookup_name, target_stage)
        if existing_poi:
            poi_name = existing_poi['name']
        else:
            poi_name = lookup_name

    # 确定坐标
    lng = item.get('lng')
    lat = item.get('lat')
    coord_source = item.get('source', '')
    if lng is None or lat is None:
        existing_poi, existing_stage = find_existing_poi(adcode, lookup_name, target_stage)
        if existing_poi:
            lng = existing_poi['lng']
            lat = existing_poi['lat']
            coord_source += f"（复用{existing_stage} POI坐标）"
        else:
            skipped.append({**item, 'reason': '无法确定坐标'})
            continue

    # 生成 school_id
    school_id = id_key(adcode, poi_name)

    # 检查 POI 是否已存在
    poi_key = (norm_name(poi_name), target_stage)
    if poi_key in poi_by_name_stage:
        already_exists.append({'poi_name': poi_name, 'stage': target_stage, 'school_id': school_id})
    else:
        # 添加 POI
        new_poi = {
            'name': poi_name,
            'lng': lng,
            'lat': lat,
            'adcode': adcode,
            'school_id': school_id,
        }
        poi_data[target_stage]['schools'].append(new_poi)
        poi_by_name_stage[poi_key] = new_poi
        added_poi.append({'poi_name': poi_name, 'stage': target_stage, 'school_id': school_id, 'lng': lng, 'lat': lat, 'source': coord_source})

    # 检查实体是否已存在
    ent_key = (school_id, target_stage)
    if ent_key in ent_by_id_stage:
        ent = ent_by_id_stage[ent_key]
        if ent.get('nature') != '民办':
            ent['nature'] = '民办'
        already_exists.append({'entity_name': ent['name'], 'stage': target_stage, 'school_id': school_id})
    else:
        # 添加实体
        aliases = []
        # 生成别名：只加区名变体（带区名前缀/去区名）；自身 norm 不入 aliases
        # （索引侧 name 已覆盖，与 build_entities poiNameAliases 口径一致）
        dist_names = {'440103': '荔湾区', '440104': '越秀区', '440105': '海珠区',
                      '440106': '天河区', '440111': '白云区', '440112': '黄埔区', '440113': '番禺区'}
        base_alias = norm_name(poi_name)
        aliases = []
        dist = dist_names.get(adcode, '')
        if dist and not base_alias.startswith(dist):
            aliases.append(dist + base_alias)

        new_ent = {
            'school_id': school_id,
            'name': poi_name,
            'stage': target_stage,
            'aliases': sorted(set(aliases), key=len, reverse=True),
            'nature': '民办',
        }
        entities.append(new_ent)
        ent_by_id_stage[ent_key] = new_ent
        added_entity.append({'name': poi_name, 'stage': target_stage, 'school_id': school_id})

# ============================================================
# 写入文件
# ============================================================
# 1. 写入 POI 数据
for stage in ['primary', 'middle', 'high']:
    path = os.path.join(ROOT, f'data/poi/dist/{stage}_poi.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(poi_data[stage], f, ensure_ascii=False, indent=2)

# 2. 写入 entities.json（保持排序）
entities.sort(key=lambda e: (e['stage'] + e['name']).encode('utf-8'))
with open(os.path.join(ROOT, 'data/registry/entities.json'), 'w', encoding='utf-8') as f:
    json.dump(entities_data, f, ensure_ascii=False, indent=2)

# 3. 更新 MINBAN_IDS
build_path = os.path.join(ROOT, 'scripts/registry/build_entities.mjs')
with open(build_path) as f:
    build_content = f.read()

all_priv_ids = sorted(set(e['school_id'] for e in entities if e.get('nature') == '民办'))
pattern = r'(const MINBAN_IDS = new Set\(\[)(.*?)(\]\);)'
m = re.search(pattern, build_content, re.DOTALL)
if m:
    lines = []
    for i in range(0, len(all_priv_ids), 5):
        batch = all_priv_ids[i:i+5]
        line = '  ' + ', '.join(f"'{sid}'" for sid in batch)
        if i + 5 < len(all_priv_ids):
            line += ','
        lines.append(line)
    new_ids_block = '\n' + '\n'.join(lines) + '\n'
    build_content = build_content[:m.start()] + m.group(1) + new_ids_block + m.group(3) + build_content[m.end():]
    with open(build_path, 'w', encoding='utf-8') as f:
        f.write(build_content)

# ============================================================
# 输出统计
# ============================================================
print(f'=== 落盘结果 ===')
print(f'新增 POI: {len(added_poi)}')
for p in added_poi:
    print(f'  + [{p["stage"]}] {p["school_id"]} {p["poi_name"]} ({p["lng"]},{p["lat"]})')
print(f'\n新增实体: {len(added_entity)}')
for e in added_entity:
    print(f'  + [{e["stage"]}] {e["school_id"]} {e["name"]}')
print(f'\n已存在（跳过）: {len(already_exists)}')
print(f'SKIP/无法定位: {len(skipped)}')
for s in skipped:
    print(f'  - {s.get("lookup_name", "")} ({s.get("target_stage", "")}): {s.get("reason", s.get("source", ""))}')

# 最终统计
final_priv = [e for e in entities if e.get('nature') == '民办']
final_priv_ids = set(e['school_id'] for e in final_priv)
print(f'\n=== 最终统计 ===')
print(f'民办实体行: {len(final_priv)}')
print(f'民办 unique school_id: {len(final_priv_ids)}')
print(f'MINBAN_IDS 数量: {len(all_priv_ids)}')
print(f'一致性: {"PASS" if final_priv_ids == set(all_priv_ids) else "FAIL"}')
