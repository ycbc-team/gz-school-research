#!/usr/bin/env python3
"""
民办名单来源标注：把 minban_*.md（手工互补区）与历史遗留分开标注。

- manual：scripts/registry/minban_*.md 中出现的 school_id（排除"公办/勿混淆/非同一所/排除/转公"段，
  如番禺剑桥郡小学为公办不得标 manual）。
- legacy：既不在官方源（official_*）也不在 md 的历史已标条目（2026-09-14 前 POI/tier1/levels
  等历史来源，来源待逐条追溯）。

用法：python3 scripts/registry/annotate_minban_sources.py [--dry-run]
"""
import json
import re
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TABLE = os.path.join(ROOT, 'data/registry/minban_schools.json')
MINBAN_DIR = os.path.join(ROOT, 'scripts/registry')
SID_RE = re.compile(r'gz-\d{6}-[0-9a-f]{8}')
EXCLUDE_WORDS = ('公办', '勿混淆', '非同一所', '排除', '转公')


def main():
    dry_run = '--dry-run' in sys.argv

    table = json.load(open(TABLE, encoding='utf-8'))
    by_id = {s['school_id']: s for s in table['schools']}

    # 1. 收集 md 里出现的 school_id（排除段除外）
    manual_ids = set()
    for f in sorted(os.listdir(MINBAN_DIR)):
        if not re.match(r'minban_[a-z]+\.md$', f):
            continue
        txt = open(os.path.join(MINBAN_DIR, f), encoding='utf-8').read()
        for sm in SID_RE.finditer(txt):
            line = txt[max(0, txt.rfind('\n', 0, sm.start())):txt.find('\n', sm.end())]
            if any(w in line for w in EXCLUDE_WORDS):
                continue
            manual_ids.add(sm.group(0))

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
