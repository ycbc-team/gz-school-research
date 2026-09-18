#!/usr/bin/env python3
"""
汇总 7 区民办学校采集结果（scripts/registry/minban_*.md），把"第一节（实体已存在、
补标 nature=民办）"的 school_id 追加进民办名单权威表 data/registry/minban_schools.json。

注意：本脚本只更新民办名单权威表（源表），不直接写 entities.json——
entities.json 是 build_entities.mjs 的产物，改表后必须重跑生产脚本生成。

用法:
  python3 scripts/registry/apply_minban_patch.py [--dry-run]
  # dry-run 通过后：
  python3 scripts/registry/apply_minban_patch.py
  node scripts/registry/build_entities.mjs        # 重跑产物（nature 由表联表生产）
  python3 scripts/data_quality_test.py            # 民办名单快照变化需 UPDATE_SNAPSHOT=1 显式更新
"""
import json
import re
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENTITIES_PATH = os.path.join(REPO, 'data/registry/entities.json')
MINBAN_TABLE = os.path.join(REPO, 'data/registry/minban_schools.json')
MINBAN_DIR = os.path.join(REPO, 'scripts/registry')

DISTRICTS = {
    '440103': '荔湾', '440104': '越秀', '440105': '海珠',
    '440106': '天河', '440111': '白云', '440112': '黄埔', '440113': '番禺',
}
PINYIN = {'荔湾': 'liwan', '越秀': 'yuexiu', '海珠': 'haizhu', '天河': 'tianhe',
          '白云': 'baiyun', '黄埔': 'huangpu', '番禺': 'panyu'}

SCHOOL_ID_RE = re.compile(r'gz-\d{6}-[0-9a-f]{8}')
URL_RE = re.compile(r'https?://\S+')


def extract_section1(filepath):
    """从 minban_*.md 的"第一节"提取 school_id + 表格行来源 URL。"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    m = re.search(r'## 一[、.].*?(?=\n## 二[、.])', content, re.DOTALL)
    if not m:
        return {}, {}
    section = m.group(0)
    id_url = {}
    id_line = {}
    for sm in SCHOOL_ID_RE.finditer(section):
        sid = sm.group(0)
        line = section[max(0, section.rfind('\n', 0, sm.start())):section.find('\n', sm.end())]
        # 排除段（重点排除/勿混淆/非同一所/公办）里的 id 不是民办，不得提取——
        # 如 minban_panyu.md "重点排除"里的 番禺区剑桥郡小学(gz-440113-611fa8ce) 是公办。
        if any(w in line for w in ('公办', '勿混淆', '非同一所', '排除', '转公')):
            continue
        urls = URL_RE.findall(line)
        id_url.setdefault(sid, []).extend(urls)
        id_line[sid] = line.strip('| ')
    return id_url, id_line


def main():
    dry_run = '--dry-run' in sys.argv

    # 1. 收集所有区 md 第一节的 school_id
    all_new = {}
    for adcode, name in DISTRICTS.items():
        filepath = os.path.join(MINBAN_DIR, f'minban_{PINYIN[name]}.md')
        if not os.path.exists(filepath):
            print(f'  [SKIP] 文件不存在: {filepath}')
            continue
        id_url, id_line = extract_section1(filepath)
        for sid, urls in id_url.items():
            if sid not in all_new:
                all_new[sid] = {'urls': [], 'line': id_line.get(sid, '')}
            all_new[sid]['urls'].extend(urls)
        print(f'  {name}({adcode}): 第一节提取 {len(id_url)} 个 school_id')
    print(f'\nmd 第一节合计 school_id: {len(all_new)}')

    # 2. 读实体表（取 name 补全）与民办名单权威表
    entities = json.load(open(ENTITIES_PATH, encoding='utf-8'))['entities']
    name_by_id = {}
    for e in entities:
        name_by_id.setdefault(e['school_id'], e['name'])
    table = json.load(open(MINBAN_TABLE, encoding='utf-8'))
    existing = {s['school_id'] for s in table['schools']}

    # 3. 计算追加/已存在/未找到
    to_add = []
    already = []
    not_found = []
    panyu_blocked = []
    for sid in sorted(all_new):
        if sid in existing:
            already.append(sid)
        elif sid.startswith('gz-440113'):
            # 番禺有官方文件（2026 义务教育民办 sheet + 中考批次民办高中名单），
            # 民办名单必须由 build_minban_official.py 自动解析，禁止手工追加。
            panyu_blocked.append(sid)
        elif sid in name_by_id:
            to_add.append(sid)
        else:
            not_found.append(sid)

    print(f'\n补丁结果:')
    print(f'  已在权威表: {len(already)} 个')
    print(f'  待追加: {len(to_add)} 个')
    print(f'  番禺 md 提取但被拒（番禺只能官方源）: {len(panyu_blocked)} 个')
    if panyu_blocked:
        for sid in sorted(panyu_blocked):
            print(f'    BLOCKED_PANYU: {sid}  {all_new[sid]["line"][:80]}')
    print(f'  实体表未找到（需先补实体）: {len(not_found)} 个')
    if not_found:
        for sid in sorted(not_found):
            print(f'    NOT_FOUND: {sid}  {all_new[sid]["line"][:80]}')

    if dry_run or not to_add:
        print('\n[DRY-RUN 或无需追加] 未写文件。')
        return

    # 4. 追加进权威表（手工互补区 → source_type=manual）
    for sid in to_add:
        table['schools'].append({
            'school_id': sid,
            'name': name_by_id[sid],
            'stage': '',
            'source_type': 'manual',
            'source_urls': sorted(set(all_new[sid]['urls'])),
        })
    table['school_count'] = len(table['schools'])
    table['updated'] = '2026-09-18'
    json.dump(table, open(MINBAN_TABLE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n已写入 {MINBAN_TABLE}：追加 {len(to_add)} 所 → 共 {table["school_count"]} 所')

    print('\n后续（铁律：产物由生产脚本生成，禁止手改 entities.json）:')
    print('  node scripts/registry/build_entities.mjs        # 重跑产物（nature 由表联表生产）')
    print('  python3 scripts/data_quality_test.py            # 民办名单快照变化需 UPDATE_SNAPSHOT=1 显式更新')


if __name__ == '__main__':
    main()
