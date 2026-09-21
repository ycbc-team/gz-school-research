# -*- coding: utf-8 -*-
"""xiaoshengchu 名字→school_id 匹配解析（数据层）。

从 upgrade_xiaoshengchu.mjs 迁移的 Python 版：小升初记录的小学 school_id / 对口初中
feed_school_ids / 直升 direct_feed_school_id 全部在数据层（Python）解析，upgrade 只做
去重与分组维表组装，不再做名字匹配——运行时（xiaoshengchu_2026.json）只依赖 school_id。

规则与迁移前 upgrade_xiaoshengchu.mjs 完全一致（norm/法人 core 聚合/区过滤/RESOLVE_OVERRIDE），
迁移后 xiaoshengchu_2026.json 产物逐条不变（产物确定性靠 check 比对保证）。
"""
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AD = {'440103': '荔湾区', '440104': '越秀区', '440105': '海珠区', '440106': '天河区',
      '440111': '白云区', '440112': '黄埔区', '440113': '番禺区'}

# 点位合并覆盖（实体删除/合并后旧 POI 名须归并到保留实体）：与 upgrade RESOLVE_OVERRIDE 一致
RESOLVE_OVERRIDE = {
    '景泰小学柯子岭校区43号A座': ['gz-440111-9e34191e'],
    # 跨区同名：白云「龙溪小学」(民办, fd1c0f9d) 与 荔湾「西关实验小学龙溪学校」(公办, 53fbb2c8)
    # 别名都含「龙溪小学」；no_feed 记录 group 无区名 → district_of_group 为 None，宁缺，
    # 显式归位白云实体。
    '龙溪小学': ['gz-440111-fd1c0f9d'],
}


def norm_xs(s):
    """与 upgrade_xiaoshengchu.mjs normName 逐字符一致：全角括号→半角 → 去开头「广州市」
    → 删半角括号 → 删全部空白。"""
    if not s:
        return ''
    s = str(s).replace('（', '(').replace('）', ')')
    s = re.sub(r'^广州市', '', s)
    s = re.sub(r'[()]', '', s)
    s = re.sub(r'\s+', '', s)
    return s


def core_of_name(raw):
    """法人名归一：去括号校区/学部后缀 + 去「广州市」前缀；保留「X区」区名前缀。"""
    s = str(raw or '').replace('（', '(').replace('）', ')')
    s = re.sub(r'\([^()]*\)', '', s)
    s = re.sub(r'^广州市', '', s)
    s = re.sub(r'\s+', '', s)
    return s


def district_of_group(g):
    if not g:
        return None
    m = re.search(r'(荔湾|越秀|海珠|天河|白云|黄埔|番禺)区', g)
    return m.group(1) + '区' if m else None


class XsResolver:
    def __init__(self):
        self.entities = json.load(open(os.path.join(ROOT, 'data/registry/entity/dist/entities.json'),
                                       encoding='utf-8'))['entities']
        # stage + norm(name/alias) -> [entity]
        self.alias_idx = defaultdict(list)
        for e in self.entities:
            for a in set([e['name']] + (e.get('aliases') or [])):
                k = norm_xs(a)
                if k:
                    self.alias_idx[(e['stage'], k)].append(e)
        # school_id -> 区名（POI join，与 upgrade entDistrict 一致）
        self.ent_district = {}
        for stage, file in [('primary', 'data/poi/dist/primary_poi.json'),
                            ('middle', 'data/poi/dist/middle_poi.json'),
                            ('high', 'data/poi/dist/high_poi.json')]:
            try:
                poi = json.load(open(os.path.join(ROOT, file), encoding='utf-8'))
            except FileNotFoundError:
                continue
            for p in poi.get('schools') or []:
                if p.get('school_id'):
                    self.ent_district[p['school_id']] = AD.get(str(p.get('adcode')), '')
        # 校区 → 升学归属区（quota_matrix 权威）：法人行 school_ids 共同标注
        self.campus_dist = {}
        try:
            qm = json.load(open(os.path.join(ROOT, 'data/linkage/quota_matrix.json'),
                                encoding='utf-8'))
        except FileNotFoundError:
            qm = {'schools': []}
        for s in qm.get('schools') or []:
            if not s.get('district'):
                continue
            if s.get('school_id'):
                self.campus_dist[s['school_id']] = s['district']
            for sid in s.get('school_ids') or []:
                self.campus_dist[sid] = s['district']

    def resolve_one(self, name, district, stage):
        """小学/直升记录定位：跨区同名按 district 取唯一实体（宁缺不兜底 list[0]）。"""
        ov = RESOLVE_OVERRIDE.get(norm_xs(name))
        if ov:
            return ov[0]
        lst = self.alias_idx.get((stage, norm_xs(name)))
        if not lst:
            return None
        if len(lst) == 1:
            return lst[0]['school_id']
        # 多命中且无区名限定（no_feed 记录 group 无区名）：不兜底——白云「金星小学」与
        # 番禺「金星学校」别名撞车时曾跨区错配，宁可缺失。
        if not district:
            return None
        hit = next((e for e in lst if self.ent_district.get(e['school_id']) == district), None)
        return (hit or lst[0])['school_id']

    def resolve_many(self, name, district, stage):
        """feed 初中解析。

        官方整体名（无校区后缀）：政府源不标校区即按整体列（南武中学一校三区、南二实南北、
        新滘双校区同型）→ 同法人同学段校区全收 = core 聚合 ∪ alias 精确（合并去重）；
        区过滤优先 POI 物理区，POI 区不符但官方明确列出时用升学归属区兜底，均无则宁缺。
        官方带校区名（括号）：alias 精确匹配（按 POI 区过滤），未命中宁缺——不聚合其他校区。
        跨区同名等无法由通用规则覆盖的用 RESOLVE_OVERRIDE 显式名单。"""
        ov = RESOLVE_OVERRIDE.get(norm_xs(name))
        if ov:
            return list(ov)
        has_campus = bool(re.search(r'[（(]', name))
        if not has_campus:
            # 官方整体名（无校区后缀）：政府源不标校区即按整体列（南武一校三区、南二实南北、
            # 新滘双校区同型）→ 同法人同学段校区全收 = core 聚合 ∪ alias 精确（合并去重，
            # 不能二选一：黄埔实验初中部实体 core 带「初中部」后缀、仅 alias 含整体名）。
            core = core_of_name(name)
            core_hits = [e for e in self.entities if e['stage'] == stage and core_of_name(e['name']) == core]
            alias_hits = list(self.alias_idx.get((stage, norm_xs(name))) or [])
            cand = core_hits + [e for e in alias_hits if e not in core_hits]
            if cand:
                if district:
                    # 官方名单在某区 → POI 物理区 + 升学归属区合并（去重）：
                    # - POI 物理区命中（常规校区）
                    # - POI 区不符但升学归属区在名单区（跨区办学特例：七中桂花 POI 白云、
                    #   quota_matrix 升学归属越秀——官方「广州市第七中学」整体名含桂花；
                    #   四中丰宁 POI 越秀、官方荔湾名单明确）
                    by_poi = [e for e in cand if self.ent_district.get(e['school_id']) == district]
                    by_campus = [e for e in cand if self.campus_dist.get(e['school_id']) == district]
                    hit = by_poi + [e for e in by_campus if e not in by_poi]
                    if hit:
                        return list(dict.fromkeys(e['school_id'] for e in hit))
                    # 本区无同法人实体：宁缺不兜底
                    return []
                return list(dict.fromkeys(e['school_id'] for e in cand))
        picked = list(self.alias_idx.get((stage, norm_xs(name))) or [])
        if district:
            f = [e for e in picked if self.ent_district.get(e['school_id']) == district]
            picked = f if f else []
        if picked:
            return list(dict.fromkeys(e['school_id'] for e in picked))
        return []

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
            'feed_school_ids': feed_ids,  # 单条内不去重：与 upgrade 去重段契约一致（跨记录合并时才 Set）
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
    # 自检：解析结果与当前 xiaoshengchu_2026.json 比对（迁移一致性验证）
    recs = json.load(open(os.path.join(ROOT, 'data/primary/xiaoshengchu_all.json'),
                          encoding='utf-8'))['records']
    resolved = resolve_records(recs)
    cur = json.load(open(os.path.join(ROOT, 'data/primary/xiaoshengchu_2026.json'),
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
