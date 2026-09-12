#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
升学通道四表回填 school_id（官方名单名 → 实体表主键）。

背景：quota_matrix / special_matrix / batch2_scores / district_quota 的键是官方名单原文校名
（PDF 视觉提取），与 POI 名存在「学部后缀 / 校区叫法 / 括号全半角」差异，且从未走实体桥接——
历史遗留的「用名字识别」链路。本脚本按实体表（data/registry/entities.json 的 name+aliases）
回填 school_id：
- quota_matrix.schools[].school_id（初中）
- special_matrix / batch2_scores / district_quota 顶层 middle_school_ids（初中名 → school_id）

匹配规则：
1) norm：全角括号→半角 → 去「广州市」前缀 → 去半角括号 → 去空白（与 shared normName 一致）
2) loose：norm 后再去掉尾部「初中部/高中部/小学部/校区/分校/学校/部」后缀（容错 POI 学部后缀）
   先精确 norm，未命中再用 loose；两者均为全等匹配，不会误配。

未命中（7 区外无实体 / 7 区内需人工桥接）落盘 data/linkage/_school_id_unmatched.json，
原文保留、不伪造 id；7 区内清单待人工确认后补进 build_entities.mjs 的 OFFICIAL_ALIASES 或实体 aliases。

运行：python3 scripts/linkage/backfill_school_ids.py
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CITY7 = {'荔湾区', '越秀区', '海珠区', '天河区', '白云区', '黄埔区', '番禺区'}


def norm(s: str) -> str:
    t = (s or '').replace('（', '(').replace('）', ')').replace('广州市', '')
    return re.sub(r'\s+', '', re.sub(r'[()]', '', t))


def loose(s: str) -> str:
    return re.sub(r'(初中部|高中部|小学部|校区|分校|学校|部)$', '', norm(s))


def main() -> int:
    entities = json.loads((ROOT / 'data/registry/entities.json').read_text('utf-8'))
    idx_norm = defaultdict(list)
    idx_loose = defaultdict(list)
    for e in entities['entities']:
        for k in [e['name']] + (e.get('aliases') or []):
            idx_norm[norm(k)].append(e)
            idx_loose[loose(k)].append(e)

    def resolve(name: str):
        """官方名 → 实体（norm 精确优先，loose 容错次之）；多实体取第一个（实体构建顺序=官方表顺序）"""
        hit = idx_norm.get(norm(name)) or idx_loose.get(loose(name))
        return hit[0] if hit else None

    unmatched = []  # (表, 官方名, 区, 是否7区内)
    files = {
        'quota_matrix': (ROOT / 'data/linkage/quota_matrix.json', 2),
        'special_matrix': (ROOT / 'data/linkage/special_matrix.json', 1),
        'batch2_scores': (ROOT / 'data/linkage/batch2_scores.json', 1),
        'district_quota': (ROOT / 'data/linkage/district_quota.json', 1),
    }
    for tag, (path, indent) in files.items():
        d = json.loads(path.read_text('utf-8'))
        if tag == 'quota_matrix':
            for s in d['schools']:
                ent = resolve(s['school'])
                if ent:
                    s['school_id'] = ent['school_id']
                else:
                    s.pop('school_id', None)
                    unmatched.append((tag, s['school'], s.get('district'), s.get('district') in CITY7))
        else:
            if tag == 'special_matrix':
                keys = list(d['matrix'].keys())
            elif tag == 'batch2_scores':
                keys = sorted({k for v in d['data'].values() for k in v.keys()})
            else:  # district_quota
                keys = list(d['data'].keys())
            ids = {}
            for k in keys:
                ent = resolve(k)
                if ent:
                    ids[k] = ent['school_id']
                else:
                    unmatched.append((tag, k, None, None))
            d['middle_school_ids'] = ids
        path.write_text(json.dumps(d, ensure_ascii=False, indent=indent) + '\n', 'utf-8')
        print(f'[{tag}] 回填完成')

    # 未命中清单：7 区内（需人工桥接）与 7 区外/未知（无实体，链接不可点属正确行为）分列
    inside = sorted({n for _, n, dist, is7 in unmatched if is7 is True})
    outside = sorted({n for _, n, dist, is7 in unmatched if is7 is not True})
    (ROOT / 'data/linkage/_school_id_unmatched.json').write_text(
        json.dumps({
            'note': '升学通道官方名未命中实体表：7 区内需人工桥接（补进 build_entities.mjs 别名）；7 区外无 POI 实体，链接不可点属正确行为，原文保留展示。',
            'updated': '2026-09-12',
            'inside7_unmatched': inside,
            'outside7_or_unknown': outside,
        }, ensure_ascii=False, indent=1) + '\n', 'utf-8')
    print(f'\n7 区内未命中 {len(inside)} 个（待人工桥接）:')
    for n in inside[:30]:
        print('   ', n)
    print(f'\n7 区外/未知未命中 {len(outside)} 个（无实体，正常不可点）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
