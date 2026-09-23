# -*- coding: utf-8 -*-
"""xiaoshengchu 名字→school_id 匹配解析（数据层）。

匹配统一收敛到 SchoolMatcher（data/registry/entity/scripts/school_match.py）：
  - resolve_one（小学记录/直升初中）→ SchoolMatcher.resolve（single：同区唯一→同区同阶段→主 POI→全局唯一→缺失）
  - resolve_many（feed 初中）→ SchoolMatcher.resolve_all：
      带校区名（官方含括号校区限定）→ 精准匹配，只返回命中的校区实体，宁缺毋滥；
      无校区名（官方只写法人名）→ 泛匹配，返回同一法人的全部校区实体（按 POI 物理区 + 政策区过滤）。
  - 跨区办学特例（政策区 ≠ POI 物理区，如七中桂花 POI 白云/政策越秀）由
    SchoolMatcher.POLICY_DISTRICT（quota_matrix 数据驱动白名单）承接；
    跨区同名/实体合并等显式锚定由 SchoolMatcher.RESOLVE_OVERRIDE 承接——
    业务不再各自适配特殊学校（原 RESOLVE_OVERRIDE 已迁入 SchoolMatcher）。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))), 'data', 'registry', 'entity', 'scripts'))
from school_match import SchoolMatcher  # noqa: E402  统一校名匹配（entity 域唯一真源）

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# district（「X区」）→ adcode（SchoolMatcher 收敛键）
DISTRICT_ADCODE = {'荔湾区': '440103', '越秀区': '440104', '海珠区': '440105', '天河区': '440106',
                   '白云区': '440111', '黄埔区': '440112', '番禺区': '440113'}
STAGE_CN = {'primary': '小学', 'middle': '初中', 'high': '高中'}


def district_of_group(g):
    if not g:
        return None
    m = re.search(r'(荔湾|越秀|海珠|天河|白云|黄埔|番禺)区', g)
    return m.group(1) + '区' if m else None


class XsResolver:
    def __init__(self):
        self.matcher = SchoolMatcher.load()

    def resolve_one(self, name, district, stage):
        """小学/直升记录定位：SchoolMatcher.resolve 单校区收敛（同区唯一，宁缺不跨区错配）。"""
        ad = DISTRICT_ADCODE.get(district) if district else None
        r = self.matcher.resolve(name, preferred_adcode=ad, preferred_stage=STAGE_CN.get(stage))
        return r.get('school_id') if r and r.get('school_id') else None

    def resolve_many(self, name, district, stage):
        """feed 初中解析：SchoolMatcher.resolve_all——带校区名精准宁缺、法人名全校区泛匹配+区过滤。"""
        ad = DISTRICT_ADCODE.get(district) if district else None
        rs = self.matcher.resolve_all(name, preferred_adcode=ad, preferred_stage=STAGE_CN.get(stage))
        return [e['school_id'] for e in rs if e.get('school_id')]

    def resolve_record(self, r):
        """对一条 xiaoshengchu 记录解析 school_id / feed_school_ids / direct_feed_school_id。"""
        district = district_of_group(r.get('group'))
        school_id = self.resolve_one(r.get('name'), district, 'primary')
        feed_ids, feed_unresolved = [], []
        for name in r.get('feed_junior_highs') or []:
            ids = self.resolve_many(name, district, 'middle')
            if ids:
                feed_ids.extend(ids)
            else:
                feed_unresolved.append(name)
        direct = None
        if r.get('direct_feed'):
            direct = self.resolve_one(r['direct_feed'], district, 'middle')
        return {
            'school_id': school_id,
            'group': r.get('group'),
            'feed_school_ids': list(dict.fromkeys(feed_ids)),  # 保序去重：法人名 resolve_all 全校区展开
            # 与校区名单独解析可能命中同一实体（如「XX中学」→本部+东校区，「XX中学东校区」→东校区，
            # 东校区 id 会重复出现）；upgrade 跨记录合并时另有 Set，但单条内重复无意义，直接去重。
            'feed_unresolved': feed_unresolved,
            'direct_feed_school_id': direct,
            'source_url': r.get('source_url'),
            'source_note': r.get('source_note'),
            'data_gaps': r.get('data_gaps'),
        }


def resolve_records(records):
    """批量解析（merge_all 调用）。"""
    res = XsResolver()
    return [res.resolve_record(r) for r in records]


if __name__ == '__main__':
    # 自检：解析结果与当前 xiaoshengchu_2026.json 比对（迁移一致性验证）。
    # 输入与 merge_all 一致（各区 per-district rec 结构，含 name）——all.json 是解析产物无 name，
    # 不能作自检输入。
    recs = []
    for key in ['yuexiu', 'liwan', 'baiyun', 'panyu', 'haizhu', 'tianhe', 'huangpu']:
        p = os.path.join(ROOT, 'data/primary/transition/dist', f'xiaoshengchu_{key}.json')
        if os.path.exists(p):
            recs.extend(json.load(open(p, encoding='utf-8'))['records'])
    resolved = resolve_records(recs)
    cur = json.load(open(os.path.join(ROOT, 'data/primary/transition/dist/xiaoshengchu_2026.json'),
                         encoding='utf-8'))
    groups = cur['groups']
    cur_recs = []
    for r in cur['records']:
        g = groups[r['group_id']]
        cur_recs.append({
            'school_id': r.get('school_id'), 'group': g.get('name'),
            'feed_school_ids': r.get('feed_school_ids'), 'feed_unresolved': r.get('feed_unresolved'),
            'direct_feed_school_id': r.get('direct_feed_school_id'),
            'source_url': (g.get('source_urls') or [None])[0],
            'source_note': r.get('source_note'), 'data_gaps': r.get('data_gaps'),
        })
    # 当前 2026 已按 (group, school_id) 去重合并 feed；py 结果先聚合再比对
    agg = {}
    for r in resolved:
        k = (r['school_id'], r['group'])
        if k not in agg:
            agg[k] = (set(r['feed_school_ids']), set(r['feed_unresolved']))
        else:
            agg[k][0].update(r['feed_school_ids'])
            agg[k][1].update(r['feed_unresolved'])
    cur_map = {}
    for c in cur_recs:
        k = (c['school_id'], c['group'])
        cur_map.setdefault(k, (set(), set()))
        cur_map[k][0].update(c['feed_school_ids'] or [])
        cur_map[k][1].update(c['feed_unresolved'] or [])
    diff = 0
    for k, (fs, fu) in sorted(agg.items(), key=lambda x: (str(x[0][0]), str(x[0][1]))):
        cfs, cfu = cur_map.get(k, (set(), set()))
        if fs == cfs and fu == cfu:
            continue
        diff += 1
        if diff <= 8:
            print('DIFF:', k[1], '|', k[0], '| feed py:', sorted(fs), 'cur:', sorted(cfs),
                  '| un py:', sorted(fu), 'cur:', sorted(cfu))
    only_cur = [k for k in cur_map if k not in agg]
    only_py = [k for k in agg if k not in cur_map]
    if only_cur:
        print('仅当前 2026 存在（py 未解析出）:', only_cur[:5], '... 共', len(only_cur))
    if only_py:
        print('仅 py 存在（当前 2026 没有）:', only_py[:5], '... 共', len(only_py))
    print(f'解析 {len(resolved)} 条（聚合 {len(agg)} 组）；与当前 2026 不一致 {diff} 组')
    sys.exit(1 if diff or only_cur or only_py else 0)
