#!/usr/bin/env python3
"""从 7 区 minban_*.md 提取第二节(需补实体)和第三节(待核实)完整清单，输出 JSON。"""
import json
import re
import os

REPO = "/Users/bytedance/Developer/gz_school_research"
# minban_*.md（民办采集）已随三业务拆分迁至 data/registry/private/src/（2026-09-21）
MINBAN_DIR = os.path.join(REPO, "data", "registry", "private", "src")

DISTRICTS = [
    ("440103", "荔湾", "liwan"),
    ("440104", "越秀", "yuexiu"),
    ("440105", "海珠", "haizhu"),
    ("440106", "天河", "tianhe"),
    ("440111", "白云", "baiyun"),
    ("440112", "黄埔", "huangpu"),
    ("440113", "番禺", "panyu"),
]

SCHOOL_ID_RE = re.compile(r'gz-\d{6}-[0-9a-f]{8}')

def extract_section(content, section_num):
    """提取第 N 节内容（## N、到下一个 ## 为止）。"""
    # 匹配 "## 二、" 或 "## 二." 等
    pattern = rf'## {section_num}[、.．].*?(?=\n## [一二三四五六七八九十]+[、.．])'
    m = re.search(pattern, content, re.DOTALL)
    if m:
        return m.group(0)
    # fallback: 到文件末尾
    pattern = rf'## {section_num}[、.．].*'
    m = re.search(pattern, content, re.DOTALL)
    return m.group(0) if m else ""

def parse_table_rows(section):
    """解析 markdown 表格行，返回 dict 列表。"""
    rows = []
    lines = section.split('\n')
    headers = None
    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if not cells:
            continue
        # 跳过分隔行
        if all(re.match(r'^[-:]+$', c) for c in cells):
            continue
        if headers is None:
            headers = cells
            continue
        row = dict(zip(headers, cells))
        rows.append(row)
    return rows

def main():
    all_need_entity = []  # 需补实体
    all_need_verify = []  # 待核实

    for adcode, name, pinyin in DISTRICTS:
        filepath = os.path.join(MINBAN_DIR, f'minban_{pinyin}.md')
        if not os.path.exists(filepath):
            print(f'[SKIP] {filepath}')
            continue
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 第二节：需补实体
        sec2 = extract_section(content, '二')
        rows2 = parse_table_rows(sec2)
        for r in rows2:
            r['_district'] = name
            r['_adcode'] = adcode
            all_need_entity.append(r)

        # 第三节：待核实
        sec3 = extract_section(content, '三')
        rows3 = parse_table_rows(sec3)
        for r in rows3:
            r['_district'] = name
            r['_adcode'] = adcode
            all_need_verify.append(r)

        print(f'{name}({adcode}): 需补实体={len(rows2)}, 待核实={len(rows3)}')

    print(f'\n总计：需补实体={len(all_need_entity)}, 待核实={len(all_need_verify)}')

    # 输出 JSON
    out = {
        'need_entity': all_need_entity,
        'need_verify': all_need_verify,
    }
    outpath = os.path.join(REPO, 'data', 'registry', 'entity', 'parsed', 'pending_items.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'\n已写入 {outpath}')

    # 打印需补实体的校名清单（用于高德查询）
    print('\n=== 需补实体校名清单 ===')
    for i, r in enumerate(all_need_entity):
        # 尝试提取校名和学段
        school_name = r.get('官方校名', r.get('校名', r.get('name', '')))
        stage = r.get('学段', r.get('stage', ''))
        print(f'  {i+1}. [{r["_district"]}] {school_name} | {stage}')

if __name__ == '__main__':
    main()
