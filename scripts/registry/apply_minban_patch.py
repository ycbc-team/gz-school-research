#!/usr/bin/env python3
"""
汇总 7 区民办学校采集结果，提取"第一节（实体已存在、补标 nature=民办）"的 school_id，
最小补丁写入 entities.json，并同步更新 build_entities.mjs 的 MINBAN_IDS。

用法: python3 scripts/registry/apply_minban_patch.py [--dry-run]
"""
import json
import re
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENTITIES_PATH = os.path.join(REPO, 'data/registry/entities.json')
BUILD_SCRIPT = os.path.join(REPO, 'scripts/registry/build_entities.mjs')
MINBAN_DIR = os.path.join(REPO, 'scripts/registry')

DISTRICTS = {
    '440103': '荔湾', '440104': '越秀', '440105': '海珠',
    '440106': '天河', '440111': '白云', '440112': '黄埔', '440113': '番禺',
}

SCHOOL_ID_RE = re.compile(r'gz-\d{6}-[0-9a-f]{8}')

def extract_section1_ids(filepath):
    """从 minban_*.md 的"第一节"提取 school_id。"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    # 找到"## 一、"到"## 二、"之间的内容
    m = re.search(r'## 一[、.].*?(?=\n## 二[、.])', content, re.DOTALL)
    if not m:
        print(f'  [WARN] 未找到第一节: {filepath}')
        return set()
    section = m.group(0)
    ids = set(SCHOOL_ID_RE.findall(section))
    return ids

def main():
    dry_run = '--dry-run' in sys.argv

    # 1. 收集所有区的新增 school_id
    all_new_ids = set()
    per_district = {}
    for adcode, name in DISTRICTS.items():
        filepath = os.path.join(MINBAN_DIR, f'minban_{name.lower() if name != "越秀" else "yuexiu"}.md')
        # 实际文件名是拼音
        pinyin_map = {'荔湾': 'liwan', '越秀': 'yuexiu', '海珠': 'haizhu',
                      '天河': 'tianhe', '白云': 'baiyun', '黄埔': 'huangpu', '番禺': 'panyu'}
        filepath = os.path.join(MINBAN_DIR, f'minban_{pinyin_map[name]}.md')
        if not os.path.exists(filepath):
            print(f'  [SKIP] 文件不存在: {filepath}')
            continue
        ids = extract_section1_ids(filepath)
        per_district[adcode] = ids
        all_new_ids.update(ids)
        print(f'  {name}({adcode}): 第一节提取 {len(ids)} 个 school_id')

    print(f'\n总计新增 school_id: {len(all_new_ids)}')

    # 2. 读取 entities.json
    with open(ENTITIES_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    entities = data['entities']

    # 当前已标民办
    existing_priv = set(e['school_id'] for e in entities if e.get('nature') == '民办')
    print(f'当前已标民办 unique school_id: {len(existing_priv)}')

    # 3. 应用补丁
    newly_marked = set()
    already_marked = set()
    not_found = set()
    for sid in all_new_ids:
        found = False
        for e in entities:
            if e['school_id'] == sid:
                found = True
                if e.get('nature') == '民办':
                    already_marked.add(sid)
                else:
                    e['nature'] = '民办'
                    newly_marked.add(sid)
                break
        if not found:
            not_found.add(sid)

    print(f'\n补丁结果:')
    print(f'  新标记 nature=民办: {len(newly_marked)} 个 unique school_id')
    print(f'  已标民办(重复): {len(already_marked)} 个')
    print(f'  实体表未找到: {len(not_found)} 个')
    if not_found:
        for sid in sorted(not_found):
            print(f'    NOT_FOUND: {sid}')

    # 统计新增标记的行数（一个 school_id 可能跨多个 stage 行）
    newly_marked_rows = [e for e in entities if e['school_id'] in newly_marked and e.get('nature') == '民办']
    print(f'  新标记涉及实体行数: {len(newly_marked_rows)}')

    # 最终民办统计
    final_priv_rows = [e for e in entities if e.get('nature') == '民办']
    final_priv_ids = set(e['school_id'] for e in final_priv_rows)
    print(f'\n最终民办: {len(final_priv_rows)} 行 / {len(final_priv_ids)} 个 unique school_id')

    # 按区统计
    from collections import Counter
    dist_count = Counter(e['school_id'].split('-')[1] for e in final_priv_rows)
    dist_ids = {}
    for e in final_priv_rows:
        d = e['school_id'].split('-')[1]
        dist_ids.setdefault(d, set()).add(e['school_id'])
    print('\n最终民办分布（行 / unique_id）:')
    for d in sorted(dist_count):
        name = DISTRICTS.get(d, d)
        print(f'  {name}({d}): {dist_count[d]} 行 / {len(dist_ids.get(d, set()))} unique')

    if dry_run:
        print('\n[DRY-RUN] 未写入文件。')
        return

    # 4. 写入 entities.json
    with open(ENTITIES_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'\n已写入 {ENTITIES_PATH}')

    # 5. 更新 MINBAN_IDS in build_entities.mjs
    with open(BUILD_SCRIPT, 'r', encoding='utf-8') as f:
        script_content = f.read()

    # 找到 MINBAN_IDS = new Set([...]) 块
    pattern = r'(const MINBAN_IDS = new Set\(\[)(.*?)(\]\);)'
    m = re.search(pattern, script_content, re.DOTALL)
    if not m:
        print('[ERROR] 未找到 MINBAN_IDS 块')
        sys.exit(1)

    # 生成新的 ID 列表（按 adcode + hex 排序）
    all_ids = sorted(final_priv_ids)
    # 格式化为多行，每行 4-5 个
    lines = []
    for i in range(0, len(all_ids), 5):
        batch = all_ids[i:i+5]
        line = '  ' + ', '.join(f"'{sid}'" for sid in batch)
        if i + 5 < len(all_ids):
            line += ','
        lines.append(line)
    new_ids_block = '\n' + '\n'.join(lines) + '\n'

    new_script = script_content[:m.start()] + m.group(1) + new_ids_block + m.group(3) + script_content[m.end():]

    with open(BUILD_SCRIPT, 'w', encoding='utf-8') as f:
        f.write(new_script)
    print(f'已更新 {BUILD_SCRIPT} MINBAN_IDS ({len(all_ids)} 个 ID)')

    # 6. 验证一致性
    with open(BUILD_SCRIPT, 'r', encoding='utf-8') as f:
        verify_content = f.read()
    minban_in_script = set(SCHOOL_ID_RE.findall(
        re.search(r'const MINBAN_IDS = new Set\(\[.*?\]\);', verify_content, re.DOTALL).group(0)
    ))
    entities_priv = set(e['school_id'] for e in entities if e.get('nature') == '民办')
    if minban_in_script == entities_priv:
        print(f'\n[PASS] MINBAN_IDS 与 entities.json 民办标记完全一致 ({len(entities_priv)} 个)')
    else:
        only_script = minban_in_script - entities_priv
        only_entities = entities_priv - minban_in_script
        print(f'\n[FAIL] 不一致!')
        if only_script:
            print(f'  仅在 MINBAN_IDS: {only_script}')
        if only_entities:
            print(f'  仅在 entities.json: {only_entities}')

if __name__ == '__main__':
    main()
