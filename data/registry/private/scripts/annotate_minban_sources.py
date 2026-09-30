#!/usr/bin/env python3
"""
民办名单来源标注：把 minban_*.json（手工互补区）与历史遗留分开标注。

- manual：data/registry/private/src/minban_*.json 中出现的 school_id
  （mark_nature / already_marked / need_entity / need_verify 节；excluded 节是
  公办/转公/误植等"非民办"行，不参与 manual 标注——JSON 结构化表达替代了旧 md
  的"行内关键词排除"启发式）。
- legacy：既不在官方源（official_*）也不在 JSON 的历史已标条目（2026-09-14 前
  POI/tier1/levels 等历史来源，来源待逐条追溯）。

用法：python3 data/registry/private/scripts/annotate_minban_sources.py [--dry-run]
"""
import json
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
TABLE = os.path.join(ROOT, 'data/registry/private/dist/minban_schools.json')
SRC_DIR = os.path.join(ROOT, 'data/registry/private/src')

# 这些节表示"人工核实确认为民办/需补实体/待核实的民办候选"，视为 manual 来源；
# excluded 节（公办/转公/误植）不参与。
MANUAL_SECTIONS = ('mark_nature', 'already_marked', 'need_entity', 'need_verify')


def collect_manual_ids():
    manual_ids = set()
    for f in sorted(glob.glob(os.path.join(SRC_DIR, 'minban_*.json'))):
        data = json.load(open(f, encoding='utf-8'))
        for sec in MANUAL_SECTIONS:
            for r in data.get('sections', {}).get(sec, []):
                if r.get('school_id'):
                    manual_ids.add(r['school_id'])
    return manual_ids


def main():
    dry_run = '--dry-run' in sys.argv

    table = json.load(open(TABLE, encoding='utf-8'))
    by_id = {s['school_id']: s for s in table['schools']}
    manual_ids = collect_manual_ids()

    n_manual = n_legacy = 0
    for sid, s in by_id.items():
        if s.get('source_type', '').startswith('official'):
            continue  # 官方源优先，不覆盖
        if sid in manual_ids:
            if s.get('source_type') != 'manual':
                s['source_type'] = 'manual'
                n_manual += 1
        else:
            if s.get('source_type') != 'legacy':
                s['source_type'] = 'legacy'
                n_legacy += 1

    from collections import Counter
    c = Counter(s.get('source_type', '(无)') for s in table['schools'])
    print(f'标注: manual +{n_manual} / legacy +{n_legacy}')
    print('分布:', dict(c))

    if dry_run:
        print('[DRY-RUN] 未写文件。')
        return
    json.dump(table, open(TABLE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'已写入 {TABLE}')


if __name__ == '__main__':
    main()
