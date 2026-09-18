#!/usr/bin/env python3
"""
番禺区民办学校名单——官方源自动解析（不允许手工维护）。

来源：data/primary/enrollments/_raw/panyu_2026_official.json
  《2026年番禺区义务教育阶段学校招生计划、招生地段及条件》→ "民办招生计划" sheet（39 所）。

规则：
- 解析 sheet 学校名（学区合并单元格行 6 cell / 完整行 7 cell）。
- 匹配实体：先精确 norm（去 广州市/番禺区/番禺 前缀与括号）→ 未命中再按「区 440113 + 关键词唯一」匹配
  （金星→金星学校、同心→番禺同心小学、名智→番禺名智小学、华立→华立学校、加拿达→加拿达外国语学校剑桥郡校区）。
- 输出的 school_id 以 source_type="official_panyu_plan" 写入 minban_schools.json；
  官方源条目由本脚本生成，重跑覆盖，禁止手改（官方文件更新 → 重跑本脚本即可感知）。

用法：python3 scripts/registry/build_minban_official.py [--dry-run]
"""
import json
import re
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, 'data/primary/enrollments/_raw/panyu_2026_official.json')
HIGH_RAW = os.path.join(ROOT, 'data/registry/_raw/gzzk_2026_minban_high.json')
TABLE = os.path.join(ROOT, 'data/registry/minban_schools.json')
ENTITIES = os.path.join(ROOT, 'data/registry/entities.json')
DISTRICT = '440113'

# 官方名 → 关键词（区+关键词唯一才采用）的特殊匹配。
# 这些官方名与实体名存在街道/镇前缀、同校多实体（小学部/中学部/招生处）等差异，
# 精确 norm 匹配不到，须用「区+关键词唯一」匹配并带出同校全部实体。
def norm(s):
    return (re.sub(r'[（(].*?[)）]', '', s)
            .replace('广州市', '').replace('番禺区', '').replace('番禺', '')
            .replace('有限公司', '').strip())


def parse_plan_names():
    """解析民办招生计划 sheet → 学校名列表。"""
    raw = json.load(open(RAW, encoding='utf-8'))
    rows = raw['sheets']['民办招生计划']
    names = []
    for r in rows[5:]:
        cells = [str(x).strip() for x in r if str(x).strip()]
        if not cells or len(cells) < 2:
            continue
        name = cells[1] if len(cells) == 7 else cells[0]
        if name in ('学区', '学校名称', '班数', '人数') or '年番禺' in name:
            continue
        names.append(name)
    return names


def parse_high_names():
    """解析广州市中考批次民办高中名单（官方源）→ (学校名列表, source_url)。"""
    raw = json.load(open(HIGH_RAW, encoding='utf-8'))
    return raw['schools'], raw['source_url']


def main():
    dry_run = '--dry-run' in sys.argv

    # 1. 解析官方 sheet（义务教育民办招生计划）
    names = parse_plan_names()
    print(f'官方 sheet: {len(names)} 所')
    high_names, high_url = parse_high_names()
    print(f'官方民办高中名单: {len(high_names)} 所')

    # 2. 匹配实体（区 440113）
    entities = json.load(open(ENTITIES, encoding='utf-8'))['entities']
    district_ents = [e for e in entities if e['school_id'].startswith('gz-' + DISTRICT)]
    idx = {}
    for e in district_ents:
        for n in [e['name']] + e.get('aliases', []):
            idx.setdefault(norm(n), set()).add(e['school_id'])
    official = {}  # school_id -> set(source_urls)（可能多官方源）
    source_url = 'https://www.panyu.gov.cn/jgzy/qzfbm/fzqjyj/jyjgkml/qt/tzgg/content/post_10794082.html'
    unmatched = []
    for name in names:
        # 精确 norm 匹配实体表 name+aliases（官方名作为别名下沉在 build_entities 别名表，
        # 如「洛浦厦滘学校」「化龙镇大博学校」等带街道/镇前缀的官方名）：
        # 命中 school_id 即标民办；同名多 id = 同校多 stage/多校区实体，全部带出。
        ids = idx.get(norm(name), set())
        if ids:
            # 同名多 id = 同校多 stage（九年制小学部+初中部等），全部标民办
            for i in ids:
                official.setdefault(i, set()).add(source_url)
        else:
            unmatched.append((name, sorted(ids)))

    # 2b. 民办高中名单（番禺实体）→ 同样归入官方源
    for name in high_names:
        ids = idx.get(norm(name), set())
        if ids:
            for i in ids:
                official.setdefault(i, set()).add(high_url)
        else:
            unmatched.append((f'[高中] {name}', []))

    print(f'匹配实体: {len(official)} 所 | 未匹配/歧义: {len(unmatched)}')
    for n, ids in unmatched:
        print(f'  未匹配/歧义: {n} → {ids}')

    # 3. 读取权威表（--check 只读对比，不更新）
    table = json.load(open(TABLE, encoding='utf-8'))

    if '--check' in sys.argv:
        cur = {s['school_id']: set(s.get('source_urls', [])) for s in table['schools'] if s.get('source_type') == 'official_panyu_plan'}
        expected = dict(official)
        ok = True
        if set(cur) != set(expected):
            ok = False
            print(f'  ✗ official 源 id 集合不一致：表 {len(cur)} vs 重算 {len(expected)}')
            print(f'    表多出: {sorted(set(cur) - set(expected))}')
            print(f'    重算新增: {sorted(set(expected) - set(cur))}')
        for sid in sorted(set(cur) & set(expected)):
            if cur[sid] != expected[sid]:
                ok = False
                print(f'  ✗ {sid} source_urls 不一致：表 {sorted(cur[sid])} vs 官方 {sorted(expected[sid])}')
        if not ok:
            print('[CHECK FAIL] official 民办源被手改或官方文件变化未重跑 → 必须重跑 build_minban_official.py')
            sys.exit(1)
        print('[CHECK PASS] official 民办源与权威表一致（番禺官方招生计划自动解析，禁手改）')
        return

    existing = {s['school_id']: s for s in table['schools']}
    n_upd, n_new = 0, 0
    for sid in sorted(official):
        urls = official[sid]  # 该 id 的官方来源集合（义务教育 sheet / 民办高中名单）
        if sid in existing:
            s = existing[sid]
            if s.get('source_type') != 'official_panyu_plan' or set(s.get('source_urls', [])) != urls:
                s['source_type'] = 'official_panyu_plan'
                s['source_urls'] = sorted(urls)  # 替换而非追加，清除残留错误 URL
                n_upd += 1
        else:
            table['schools'].append({
                'school_id': sid,
                'name': next(e['name'] for e in entities if e['school_id'] == sid),
                'stage': '',
                'source_type': 'official_panyu_plan',
                'source_urls': sorted(urls),
            })
            n_new += 1

    # 4. 移除官方源里已不存在的 id（官方文件变化 → 从表移除，不允许手改残留）
    official_ids = set(official)
    removed = []
    for s in table['schools'][:]:
        if s.get('source_type') == 'official_panyu_plan' and s['school_id'] not in official_ids:
            table['schools'].remove(s)
            removed.append(s['school_id'])

    table['school_count'] = len(table['schools'])
    print(f'\n更新 {n_upd} / 新增 {n_new} / 官方源移除 {len(removed)}')
    if removed:
        print('  移除（官方文件不再列为民办）:', removed)

    if dry_run:
        print('\n[DRY-RUN] 未写文件。')
        return
    json.dump(table, open(TABLE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n已写入 {TABLE} → 共 {table["school_count"]} 所')
    print('后续：node scripts/registry/build_entities.mjs 重跑产物')


if __name__ == '__main__':
    main()
