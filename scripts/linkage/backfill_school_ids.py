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

# 统一匹配库：norm/loose 收敛至 school_match.normName/looseNorm（原本地定义已删，规则与 shared support.ts 一致）
sys.path.insert(0, str(ROOT / 'scripts' / 'registry'))
from school_match import normName as norm
from school_match import looseNorm as loose


def main() -> int:
    entities = json.loads((ROOT / 'data/registry/entities.json').read_text('utf-8'))
    idx_norm = defaultdict(list)
    idx_loose = defaultdict(list)
    for e in entities['entities']:
        for k in [e['name']] + (e.get('aliases') or []):
            idx_norm[norm(k)].append(e)
            idx_loose[loose(k)].append(e)

    # 法人聚合：官方升学文件按法人单位公布（不分校区），一个法人名对应同 stage 全部校区实体。
    # 由实体表 name 去括号校区后缀推导（如「广州市第一一三中学(乐学校区)」→ 法人「广州市第一一三中学」），
    # 脚本生成不手改；quota 法人行写入 school_ids 数组，前端升学信息按法人聚合展示、各校区分别跳转。
    def core_name(n: str) -> str:
        return re.sub(r'[（(][^）)]*[）)]', '', n or '').strip()

    by_core: dict[tuple, list] = defaultdict(list)
    for e in entities['entities']:
        by_core[(e['stage'], core_name(e['name']))].append(e['school_id'])
    for k in by_core:
        by_core[k] = sorted(set(by_core[k]))

    AD_MAP = {'荔湾区': '440103', '越秀区': '440104', '海珠区': '440105',
              '天河区': '440106', '白云区': '440111', '黄埔区': '440112', '番禺区': '440113'}

    # quota_matrix 人工修正硬映射（官方名 → school_id）：通用 norm/loose 规则无法复现的
    # 人工核对结果（同 stage 多校区歧义选错、跨学段裸名被 high 独占等），在数据层直接关联
    # school_id，不靠手改产物；来源：HEAD quota_matrix school_id（人工核对版）。
    # quota_matrix 人工修正硬映射（官方名 → school_id）：通用 norm/loose 规则无法复现的
    # 人工核对结果，在数据层直接关联 school_id，不靠手改产物。
    # 已收敛的条目：resolve 升级后可复现的冗余项、build_entities FORCED_MIDDLE_ALIAS
    # （官方裸名→初中部校区）治本项、rebuild_quota_matrix 校名规范化（OCR 错字）项——
    # 一律不再进覆盖表，保持覆盖表只承载「同区同 stage 真歧义 / 跨区同名 / 跨学段多候选」。
    MATCH_OVERRIDES = {
        "广州市为明学校": "gz-440105-baa048f9",  # 跨学段多候选（primary 光大 + high 罗马，无 middle 实体）
        "广州市天健学校": "gz-440112-e085f4fa",  # 跨区同名（黄埔 high vs 白云 middle），quota 区过滤锚黄埔
        "广州市香江中学": "gz-440118-322b6d28",  # 官方名（香江中学）vs 实体名（香江学校），7 区外但有实体
        "广州市天河区汇景实验学校": "gz-440106-0d1e149e",  # 旧名实体（四十七中汇景中学部）alias 持现名裸名，同区同 stage 双候选
        "广州市天河区同仁实验学校": "gz-440106-77787b4a",  # 官方名 norm 未命中（小学部实体持名）
        "广州市天河外国语学校": "gz-440106-b711d94a",  # 官方名带全角括号校区，实体无对应 alias
        "广州市新滘中学": "gz-440105-003f2037",  # 官方名（贵荣校区）norm 未命中
        "广州市真光中学": "gz-440103-042e23a5",  # 同区同 stage 双实体（本部/岭南均 middle），锚岭南（初中部）
        "广州市第八十六中学": "gz-440112-43108516",  # 完中本部 0cb5a402 自身含 middle 行，初中表双候选
        "广州市第十六中学": "gz-440104-8964385d",  # 完中本部 8a1a7b3d 自身含 middle 行，初中表双候选
        "广州市第四十一中学": "gz-440105-b210556b",  # 完中本部 40a80ebb 自身含 middle 行，初中表双候选
        "广州市西关外国语学校": "gz-440103-b41a3512",  # 完中本部（中学部）持官方名，同区同 stage 双候选
        "广州市实验外语学校": "gz-440106-540006ea",  # quota 标白云但实体在天河，跨区 loose 多候选
        "广州市番禺区丽江学校": "gz-440113-2264148c",  # 官方名（丽江学校）vs 实体名（丽江小学），loose 多候选
        "广州市第十三中学": "gz-440104-0a17f1eb",  # 文德校区=初中部校区；同校区双 POI 实体（文德/初中部），锚入库值
        "广州市黄埔区铁英中学": "gz-440112-c80ac6ac",  # 官方名（广铁一中铁英学校）与实体名差异
        "广州铁一中学（番禺校区）": "gz-440113-97e0acaa",  # 官方名带全角括号校区，实体无对应 alias
    }

    def resolve(name: str, stage: str, adcode: str = None):
        """官方名 → 实体。

        规则（按优先级）：
        0) QUOTA_OVERRIDES 硬映射（quota_matrix 人工修正，直接 school_id 关联）。
        1) norm 精确命中且含 preferred_stage → 取之（「广州市第一中学」norm 命中高中部
           裸名，但 quota_matrix 是初中配额表，必须回填初中部 2dc142ec——人工修正固化
           进脚本，不靠改数据）。
        2) loose 容错（去「初中部/校区」等学部后缀）命中且含 preferred_stage → 取之。
        3) norm/loose 命中但**候选唯一**（无 preferred_stage）→ 接受：该官方名对应的
           POI 唯一（完中/一贯制学校初中配额挂高中或小学实体），跨学段引用是唯一 POI 的
           正确行为。
        4) 多候选且无 preferred_stage → 宁缺失不跨学段错配。
        adcode（quota_matrix 带 district 字段）：跨区同名（如「培智学校」天河/白云）时按区
        过滤；本区无候选 → 回退全量唯一（如培英鹤洞实体在荔湾 440103、quota 表标白云区，
        跨区引用是唯一 POI）——宁缺失只用于「多候选且跨区无本区项」，不用唯一的跨区引用。
        同 stage 多实体（如一一三中金融城/元岗双校区）取实体构建顺序第一个。
        """
        # 设施类 POI（游泳馆/体育馆等非学校）不参与匹配——采集噪音，实体表应剔除（见 build_entities）
        FACILITY = ('游泳馆', '体育馆', '运动场', '田径场')
        # 实体 name 与 alias 可能同串重复入索引；先按 (school_id, stage) 去重
        def dedup(ents):
            out = {}
            for e in ents or []:
                if any(f in e['name'] for f in FACILITY):
                    continue
                out.setdefault((e['school_id'], e['stage']), e)
            return out

        # 区过滤：优先本区；本区无 → 回退全量（唯一跨区引用允许）
        def in_dist(e):
            return not adcode or e['school_id'].startswith(f'gz-{adcode}-')

        n = norm(name)
        dn = dedup(idx_norm.get(n))
        pn = {k: v for k, v in dn.items() if in_dist(v)} or dn
        same = [e for e in pn.values() if e['stage'] == stage]
        if same:
            return same[0]
        l = loose(name)
        dl = dedup(idx_loose.get(l))
        pl = {k: v for k, v in dl.items() if in_dist(v)} or dl
        lsame = [e for e in pl.values() if e['stage'] == stage]
        if lsame:
            return lsame[0]
        if len(pn) == 1:
            return next(iter(pn.values()))
        if len(pl) == 1:
            return next(iter(pl.values()))
        return None

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
                if s['school'] in MATCH_OVERRIDES:
                    s['school_id'] = MATCH_OVERRIDES[s['school']]
                else:
                    ent = resolve(s['school'], 'middle', AD_MAP.get(s.get('district')))
                    if ent:
                        s['school_id'] = ent['school_id']
                    else:
                        s.pop('school_id', None)
                        unmatched.append((tag, s['school'], s.get('district'), s.get('district') in CITY7))
                # 法人行（不带校区括号）：挂该法人同 stage 全部校区实体（school_ids 数组）。
                # 校区收敛（如脏 POI 实体剔除后 ids 变 1 或 0）必须清残留旧数组，否则引用断链。
                if s.get('school_id'):
                    c = core_name(s['school'])
                    if c == s['school']:
                        ids = by_core.get(('middle', c)) or []
                        if len(ids) > 1:
                            s['school_ids'] = ids
                        else:
                            s.pop('school_ids', None)
        else:
            if tag == 'special_matrix':
                keys = list(d['matrix'].keys())
            elif tag == 'batch2_scores':
                keys = sorted({k for v in d['data'].values() for k in v.keys()})
            else:  # district_quota
                keys = list(d['data'].keys())
            ids = {}
            for k in keys:
                if k in MATCH_OVERRIDES:
                    ids[k] = MATCH_OVERRIDES[k]
                    continue
                ent = resolve(k, 'middle')
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
