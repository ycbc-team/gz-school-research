#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""升学通道四表回填 school_id（C 层 SchoolMatcher：官方名单名 → 实体表主键）。

输入（B 层规范表，canonical）：data/linkage/parsed/canonical/ 下四表
  - quota_matrix.json     名额分配计划规范表（schools[].school 官方名单原文名）
  - special_matrix.json   升学通道矩阵规范表（高中名单原文 → high_school_ids 已在 B 层解析）
  - batch2_scores.json    第二批次分数规范表（data 键=初中名）
  - district_quota.json   区属名额规范表（data 键=初中名）

输出：
  1) canonical 写回（既有 id 又有 name 的规范表，快照测试唯一基线）：
     - quota_matrix.schools[].school_id / school_ids（初中实体）
     - batch2_scores / district_quota 顶层 middle_school_ids（初中名 → school_id）
  2) dist（运行时精简产物，键位 id 优先 + 原文兜底，school 名 / 调试字段全部删除）：
     - quota_matrix：schools 拆两个并行数组——ids（有 school_id 的行，只保留
       school_id/school_ids，前端 join 实体表展示名）+ schools（无 id 的行，保留原文名
       展示，链接不可点）。行内删 page/row/is_district_head/sz_sum，顶层删
       districts/note/source/title/updated（均无前端消费，canonical 保留）。
     - district_quota / batch2_scores：data 递归拆 ids/schools 并行映射（键=id 优先，
       无实体键保留原文）——外层初中/高中键、内层高中/初中键各自拆。顶层
       middle_school_ids 删除（键已 id 化）；note/source 等元数据删除。
     - special_matrix：删 high_entities/high_schools 死字段与 note/source 等元数据；
       high_school_ids / autonomy_plan 键保持官方名单原文（名单原文是外键表键，
       null 兜底需要原文）；special_plan 已 id 键，值内 name（=实体名）删除。

匹配规则（resolve）：
0) src/backfill_overrides.json 硬映射（人工核对，优先于一切通用规则）
1) norm：全角括号→半角 → 去「广州市」前缀 → 去半角括号 → 去空白（与 shared normName 一致）
2) loose：norm 后再去掉尾部「初中部/高中部/小学部/校区/分校/学校/部」后缀（容错 POI 学部后缀）
   先精确 norm，未命中再用 loose；两者均为全等匹配，不会误配。
3) matchNorm 剥区兜底（官方名带「X区」前缀、实体 name 无区名）：仅全局唯一候选可取，
   区一致性校验后按 stage 收敛。
未命中（7 区外无实体 / 7 区内需人工桥接）落盘 test/_school_id_unmatched.json（构建期审计
产物，非运行时数据），原文保留、不伪造 id；7 区内清单待人工确认后补进 build_entities.py 的
OFFICIAL_ALIASES 或实体 aliases。

运行：python3 data/linkage/scripts/backfill_school_ids.py
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LINK = ROOT / 'data' / 'linkage'
CANON = LINK / 'parsed' / 'canonical'
DIST = LINK / 'dist'
TEST = LINK / 'test'
CITY7 = {'荔湾区', '越秀区', '海珠区', '天河区', '白云区', '黄埔区', '番禺区'}

# 统一匹配库：norm/loose 收敛至 school_match.normName/looseNorm（与 shared support.ts 一致）
sys.path.insert(0, str(ROOT / 'data' / 'registry' / "entity" / 'scripts'))
from school_match import normName as norm
from school_match import looseNorm as loose
from school_match import matchNorm as mnorm


def main() -> int:
    entities = json.loads((ROOT / 'data/registry/entity/dist/entities.json').read_text('utf-8'))
    idx_norm = defaultdict(list)
    idx_loose = defaultdict(list)
    idx_mnorm = defaultdict(list)
    for e in entities['entities']:
        for k in [e['name']] + (e.get('aliases') or []):
            idx_norm[norm(k)].append(e)
            idx_loose[loose(k)].append(e)
            # 2026-09-21 别名瘦身兜底：matchNorm（剥区名）键 + 去括号变体——
            # 官方名带「X区」前缀、实体 name 无区名（如「广州市天河区科韵路学校」→ name「科韵路学校」）
            _mk = mnorm(k)
            if _mk:
                idx_mnorm[_mk].append(e)
                _flat = _mk.replace('(', '').replace(')', '')
                if _flat != _mk:
                    idx_mnorm[_flat].append(e)

    # 法人聚合：官方升学文件按法人单位公布（不分校区），一个法人名对应同 stage 全部校区实体。
    # 由实体表 name 去括号校区后缀推导（如「广州市第一一三中学(乐学校区)」→ 法人「广州市第一一三中学」），
    # 再统一去「广州市」前缀（保留「X区」区名隔离不同法人：从化区第七中学 ≠ 第七中学），
    # 使「育才中学(东校区)」（POI 无广州市前缀）与「广州市育才中学(西校区)」归同一法人聚合。
    # core_loose：再剥离尾部「校区/分校/初中部/高中部/小学部」后缀——POI 表存在不带括号的
    # 校区/学部名（如「广州市第十三中学文德校区」「广州市第十三中学初中部」），core_name 无法归一；
    # 剥离后与括号版（文德校区/禺山校区）同归「第十三中学」。区名前缀保留，跨区法人不混。
    # 脚本生成不手改；quota 法人行写入 school_ids 数组，前端升学信息按法人聚合展示、各校区分别跳转。
    def core_name(n: str) -> str:
        return re.sub(r'^广州市', '', re.sub(r'[（(][^）)]*[）)]', '', n or '').strip())

    def core_loose(n: str) -> str:
        return re.sub(r'(校区|分校|初中部|高中部|小学部)$', '', core_name(n))

    by_core: dict[tuple, list] = defaultdict(list)
    for e in entities['entities']:
        by_core[(e['stage'], core_loose(e['name']))].append(e['school_id'])
    for k in by_core:
        by_core[k] = sorted(set(by_core[k]))
    by_id = {e['school_id']: e['name'] for e in entities['entities']}

    AD_MAP = {'荔湾区': '440103', '越秀区': '440104', '海珠区': '440105',
              '天河区': '440106', '白云区': '440111', '黄埔区': '440112', '番禺区': '440113'}

    # 人工核对硬映射（官方名 → school_id）：通用 norm/loose 规则无法复现的人工核对结果
    # （同区同 stage 多校区歧义选错、跨学段裸名被 high 独占等），在数据层直接关联 school_id，
    # 不靠手改产物。来源：src/backfill_overrides.json（含逐条原因，可审计）。
    # 已收敛的条目：resolve 升级后可复现的冗余项、build_entities FORCED_MIDDLE_ALIAS
    # （官方裸名→初中部校区）治本项、rebuild_quota_matrix 校名规范化（OCR 错字）项——
    # 一律不再进覆盖表，保持覆盖表只承载「同区同 stage 真歧义 / 跨区同名 / 跨学段多候选」。
    MATCH_OVERRIDES = {
        k: v['school_id']
        for k, v in json.loads((LINK / 'src' / 'backfill_overrides.json').read_text('utf-8'))['overrides'].items()
    }

    def resolve(name: str, stage: str, adcode: str = None):
        """官方名 → 实体。

        规则（按优先级）：
        0) MATCH_OVERRIDES 硬映射（人工核对，直接 school_id 关联）。
        1) norm 精确命中且含 preferred_stage → 取之（「广州市第一中学」norm 命中高中部
           裸名，但 quota_matrix 是初中配额表，必须回填初中部 2dc142ec——人工修正固化
           进覆盖表，不靠改数据）。
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
        # 剥区兜底（2026-09-21）：norm/loose 未命中时 matchNorm 剥区名全等匹配；
        # 仅全局唯一候选可取（官方名「X区+裸名」→ 唯一裸名实体）；跨区同名多候选
        # （如「培智学校」天河/越秀/白云）宁缺——区消歧信息已丢，不能按 stage 收敛
        # （曾把天河培智错配白云 middle），仍走 _school_id_unmatched 人工桥接
        m = mnorm(name)
        dm = dedup(idx_mnorm.get(m) or idx_mnorm.get(m.replace('(', '').replace(')', '')))
        if dm:
            # 按 school_id 判唯一：一贯制学校同 id 双 stage 实体（小学部/初中部）是同一学校，
            # 不算多候选；跨区同名（如「培智学校」天河/越秀/白云）才宁缺
            _by_sid = {e['school_id']: e for e in dm.values()}
            if len(_by_sid) == 1:
                e = next(iter(_by_sid.values()))
                # 区一致性校验：官方名带区名且可解析时，候选实体 adcode 必须同区——
                # 防「广州市海珠区华立学校」剥区后误配番禺「华立学校」（HEAD 宁缺不配）
                _d = re.search(r'(荔湾|越秀|海珠|天河|白云|黄埔|番禺|花都|南沙|从化|增城)区', name)
                if _d and not e['school_id'].startswith(f"gz-{AD_MAP.get(_d.group(0), '')}-"):
                    return None
                if e['stage'] == stage:
                    return e
                return next((x for x in dm.values() if x['stage'] == stage), e)
        return None

    unmatched = []  # (表, 官方名, 区, 是否7区内)
    dist_out = {}

    # ================= quota_matrix：canonical 回填 + dist 行拆 ids/schools =================
    d = json.loads((CANON / 'quota_matrix.json').read_text('utf-8'))
    ids_rows = []
    school_rows = []
    # 官方名单原文名 → 法人行 school_id 的精确索引（前端查询用；法人聚合/主 id 归一的
    # 全部推断都在本 py 层完成，运行时只做 id 精准匹配，不做任何名称推断）
    # ---------- 21 省市属校区：sz 键原文 → high 实体 id（SchoolMatcher resolve，含 alias） ----------
    # 官方原文按校区公布（如「广州市铁一中学（越秀校区）」）；实体表缺口的校区
    # （广东广雅中学（花都校区）/广州市第六中学（从化校区）/广州市第六中学（花都校区））
    # id=None → 行内 sz_schools 原文保底（与 ids/schools 并行结构同构，前端显示名称不可点）。
    # school = 官方原文去括号的归属法人名（如「华南师范大学附属中学」），前端分组/聚合用。
    CAMPUS_ORDER = [
        '华南师范大学附属中学（石牌校区）', '华南师范大学附属中学（知识城校区）',
        '广东实验中学（荔湾校区）', '广东实验中学（白云校区）',
        '广东广雅中学（荔湾校区）', '广东广雅中学（花都校区）',
        '广州市执信中学（执信路校区）', '广州市执信中学（天河校区）',
        '广州市第二中学',
        '广州市第六中学（海珠校区）', '广州市第六中学（从化校区）', '广州市第六中学（花都校区）',
        '广东华侨中学', '广州协和学校', '广州大学附属中学',
        '广州市铁一中学（越秀校区）', '广州市铁一中学（番禺校区）', '广州市铁一中学（白云校区）',
        '广州外国语学校',
        '清华附中湾区学校（智谷校区）', '清华附中湾区学校（智慧城校区）',
    ]

    def campus_sid(name):
        e = resolve(name, 'high')
        return e['school_id'] if e else None

    def campus_school(name):
        return re.sub(r'[（(][^）)]*[）)]', '', name).strip()

    def conv_sz(sz):
        """canonical sz（原文 dict，全 21 key 含 0）→ dist id 键非零 + sz_schools 原文非零保底"""
        out_ids, out_schools = {}, {}
        for k, n in (sz or {}).items():
            if n > 0:
                sid = campus_map.get(k)
                if sid:
                    out_ids[sid] = n
                else:
                    out_schools[k] = n
        return out_ids, out_schools

    campuses_out = []
    campus_map = {}
    for name in CAMPUS_ORDER:
        sid = campus_sid(name)
        campus_map[name] = sid
        c = {'id': sid, 'name': name, 'school': campus_school(name)}
        campuses_out.append(c)
    print(f'[quota_matrix] 21 校区转 id：{sum(1 for c in campuses_out if c["id"])}/21 命中，'
          f'{sum(1 for c in campuses_out if not c["id"])} 个实体表缺口进 sz_schools 原文保底')
    name_index = {}
    for s in d['schools']:
        if s['school'] in MATCH_OVERRIDES:
            s['school_id'] = MATCH_OVERRIDES[s['school']]
        else:
            ent = resolve(s['school'], 'middle', AD_MAP.get(s.get('district')))
            if ent:
                s['school_id'] = ent['school_id']
            else:
                s.pop('school_id', None)
                unmatched.append(('quota_matrix', s['school'], s.get('district'), s.get('district') in CITY7))
        # 法人/校区行聚合 school_ids：官方升学文件按法人公布，一个法人名对应同 stage
        # 全部校区实体——school_ids 数组 = 同 core 现存 middle 校区全集（实体表现存即
        # 「办初中」：纯高中校区已由 build_entities NON_MIDDLE_CAMPUS/CAMPUS_STAGE_FIX
        # 删除或转 high，不再出现在 middle by_core，天然排除）。
        # 聚合 key 用「行 school_id 对应实体的 core_name」而非行原名：官方名单名带区前缀
        # 而实体名不带（如「广州市白云区龙归学校」vs 实体「龙归学校(初中部)」），
        # 原名 core 会失配（龙归 4c9a3eaa 曾因此无升学仍孤儿）；实体 core 反查天然对齐，
        # 且实体 core 保留区名（从化区第七中学 ≠ 第七中学）不受影响。
        # 主 id 归一仍只对法人行（原名无括号）做（用户口径：一个名字 + 弹窗选校区）；
        # 校区收敛（如脏 POI 实体剔除后 ids 变 1 或 0）必须清残留旧数组，否则引用断链。
        if s.get('school_id'):
            _core = core_loose(by_id.get(s['school_id'], ''))
            ids = by_core.get(('middle', _core)) or [] if _core else []
            if '(' in s['school'] or '（' in s['school']:
                # 校区级官方名单名（带括号，如「广州市铁一中学（越秀校区）」）：官方文件按校区
                # 独立公布名额（越秀/白云/番禺三行各自考生数），不是法人聚合——school_ids 只关联
                # 该校区本身。school_id 即 SchoolMatcher resolve 的结果（norm/mnorm 去括号后
                # 保留校区名，如「铁一中学越秀校区」，精确命中唯一校区实体），直接单校区收敛，
                # 不额外写字符串匹配逻辑；其余 id 走 by_core 法人聚合（原名无括号才聚合）。
                s['school_ids'] = [s['school_id']]
            elif len(ids) > 1:
                # 法人行（原名无括号）：school_ids = 同 core 全部校区（升学信息按法人聚合展示）
                s['school_ids'] = ids
                # 主 id 归一：多校区法人行主 school_id 必须指向「本部实体」——
                # school_ids 中「实体名无括号且去广州市后=法人名」者（如十六中→本部 8a1a7b3d，
                # 而非首匹配的东湖校区）；无本部实体（如七中仅麓湖/初中部/桂花校区）取 ids[0]。
                # 否则列表页点法人名跳到校区详情页。
                home = next((i for i in ids
                             if '(' not in by_id.get(i, '') and '（' not in by_id.get(i, '')
                             and core_loose(by_id.get(i, '')) == _core), None)
                s['school_id'] = home or ids[0]
            else:
                s.pop('school_ids', None)
        # dist 行：有 id 只留 school_id/school_ids（前端 join 实体表展示名），
        # 无 id 才留 school 原文名（无点击跳转）。调试字段 page/row/is_district_head/sz_sum 只进 canonical。
        row = {k: s[k] for k in ('district', 'kaosheng', 'sheng_quota', 'qu_quota') if k in s}
        _sz_ids, _sz_schools = conv_sz(s.get('sz'))
        if _sz_ids:
            row['sz'] = _sz_ids
        if _sz_schools:
            row['sz_schools'] = _sz_schools
        if s.get('school_id'):
            row['school_id'] = s['school_id']
            name_index[s['school']] = s['school_id']
            if s.get('school_ids'):
                row['school_ids'] = s['school_ids']
            ids_rows.append(row)
        else:
            row['school'] = s['school']
            school_rows.append(row)
    (CANON / 'quota_matrix.json').write_text(json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True) + '\n', 'utf-8')
    dist_out['quota_matrix'] = {'ids': ids_rows, 'schools': school_rows, 'name_index': name_index, 'campuses': campuses_out}
    print(f'[quota_matrix] 回填完成 → canonical 写回 + dist ids({len(ids_rows)})/schools({len(school_rows)}) 拆分')

    # ================= district_quota / batch2：canonical 回填 + dist 递归 ids/schools =================
    def conv_row(row, resolver):
        """值行拆 ids/schools：键=id 优先，无实体键保留原文。resolver 返回 school_id 或 None。

        行内冲突（两个官方键映射同一 school_id，如区属名单里两个校名挂同一实体）：
        后者保留原文键进 schools，不覆盖前者（id 键化禁止丢行数据），冲突待数据层
        （registry alias 修复）收敛——见 id_conflicts 告警。
        """
        out_ids = {}
        out_schools = {}
        seen = set()
        for k, v in row.items():
            sid = resolver(k)
            if sid and sid not in seen:
                seen.add(sid)
                out_ids[sid] = v
            else:
                out_schools[k] = v
                if sid:
                    id_conflicts.append((k, sid))
        return {'ids': out_ids, 'schools': out_schools}

    def high_sid(name: str):
        e = resolve(name, 'high')
        return e['school_id'] if e else None

    id_conflicts = []  # (官方键, school_id)：两名同 id 且行数据不同，保底原文兜底（数据层需修复 alias）
    for tag in ('district_quota', 'batch2_scores'):
        d = json.loads((CANON / f'{tag}.json').read_text('utf-8'))
        if tag == 'batch2_scores':
            mid_keys = sorted({k for v in d['data'].values() for k in v.keys()})
        else:  # district_quota
            mid_keys = list(d['data'].keys())
        ids = {}
        for k in mid_keys:
            if k in MATCH_OVERRIDES:
                ids[k] = MATCH_OVERRIDES[k]
                continue
            ent = resolve(k, 'middle')
            if ent:
                ids[k] = ent['school_id']
            else:
                unmatched.append((tag, k, None, None))
        d['middle_school_ids'] = ids
        (CANON / f'{tag}.json').write_text(json.dumps(d, ensure_ascii=False, indent=1) + '\n', 'utf-8')
        # dist：data 递归拆（外层键、内层键各自 ids/schools）；外层多名同 id 冲突保底 schools
        outer_ids = {}
        outer_schools = {}
        outer_seen = set()
        if tag == 'batch2_scores':
            for hk, rows in d['data'].items():
                hs = high_sid(hk)
                conv = conv_row(rows, lambda mk: ids.get(mk) or (resolve(mk, 'middle') or {}).get('school_id'))
                # dist 值精简：运行时只消费录取最低分。min_score 为空（admitted:false，
                # 有指标但未完成录取）与 admitted/rows/last_score 均只进 canonical（调试/
                # 业务字段，消费结果与"无记录"一致）；前端 UI 也只展示 min 一列。
                for m in list(conv['ids']):
                    v = conv['ids'].pop(m)
                    conv['ids'][m] = {'min_score': v.get('min_score')}
                for m in list(conv['schools']):
                    v = conv['schools'].pop(m)
                    conv['schools'][m] = {'min_score': v.get('min_score')}
                conv['ids'] = {k: v for k, v in conv['ids'].items() if v['min_score'] is not None}
                conv['schools'] = {k: v for k, v in conv['schools'].items() if v['min_score'] is not None}
                if hs and hs not in outer_seen:
                    outer_seen.add(hs)
                    outer_ids[hs] = conv
                else:
                    outer_schools[hk] = conv
                    if hs:
                        id_conflicts.append((hk, hs))
                    else:
                        # 审计：batch2 外层高中校区未命中实体表（多为 7 区外校区，
                        # 无实体不可点属正确行为；7 区内则需人工桥接）
                        is7 = not any(x in hk for x in ('增城', '南沙', '花都', '从化'))
                        unmatched.append(('batch2-outer', hk, None, is7))
        else:  # district_quota：外层初中键、内层高中键
            for sk, row in d['data'].items():
                conv = conv_row(row, high_sid)
                # 审计：内层区属高中未命中实体表（如海珠外国语实验中学(江海校区)，
                # 实体表只有本部无校区实体/别名）→ 全部属 7 区内，待人工桥接
                for k in conv['schools']:
                    unmatched.append(('district_quota-inner', k, None, True))
                if sk in ids and ids[sk] not in outer_seen:
                    outer_seen.add(ids[sk])
                    outer_ids[ids[sk]] = conv
                else:
                    outer_schools[sk] = conv
                    if sk in ids:
                        id_conflicts.append((sk, ids[sk]))
        dist_out[tag] = {'ids': outer_ids, 'schools': outer_schools}
        print(f'[{tag}] 回填完成 → canonical 写回 + dist ids({len(outer_ids)})/schools({len(outer_schools)}) 拆分')

    # ================= special_matrix：去死字段 + autonomy_plan 转 id =================
    # 用户口径：dist 运行时 id 精准匹配。autonomy_plan 原文键 → SchoolMatcher resolve('high')
    # 转实体 id（法人名 resolve 到其唯一 high 实体，如广东仲元中学→本部）；实体表缺口原文
    # （如广雅花都/六中从化/六中花都等）→ autonomy_plan_schools 保底（无实体无详情页，仅数据
    # 完整性）。high_school_ids（原文→id 桥接）与 autonomy_plan_norm（前端名称兜底索引）是
    # 构建期中间产物，dist 不再需要（canonical 保留原文可溯源）。
    d = json.loads((CANON / 'special_matrix.json').read_text('utf-8'))
    sp = json.loads(json.dumps(d))
    for k in ('high_entities', 'high_schools', 'note', 'scope', 'updated', 'title',
              'autonomy_plan_source', 'special_plan_source', 'special_plan_summary',
              'high_school_ids', 'autonomy_plan_norm'):
        sp.pop(k, None)
    for v in (sp.get('special_plan') or {}).values():
        v.pop('name', None)
    autonomy_ids, autonomy_schools = {}, {}
    for raw, n in (sp.get('autonomy_plan') or {}).items():
        e = resolve(raw, 'high')
        if e:
            autonomy_ids[e['school_id']] = n
        else:
            autonomy_schools[raw] = n
    sp['autonomy_plan'] = autonomy_ids
    if autonomy_schools:
        sp['autonomy_plan_schools'] = autonomy_schools
    else:
        sp.pop('autonomy_plan_schools', None)
    print(f'[special_matrix] autonomy_plan 转 id：{len(autonomy_ids)}/{len(autonomy_ids) + len(autonomy_schools)} 命中，'
          f'{len(autonomy_schools)} 个实体表缺口原文进 autonomy_plan_schools 保底')
    dist_out['special_matrix'] = sp
    print('[special_matrix] 去死字段 + autonomy_plan 转 id 完成 → dist 写入')

    # ================= 写 dist =================
    for tag, data in dist_out.items():
        _sk = tag == 'quota_matrix'
        (DIST / f'{tag}.json').write_text(
            json.dumps(data, ensure_ascii=False, indent=2 if _sk else 1, sort_keys=_sk) + '\n', 'utf-8')

    # 未命中清单（构建期审计产物，非运行时数据）：7 区内（需人工桥接）与
    # 7 区外/未知（无实体，链接不可点属正确行为）分列 → 落 test/ 目录
    inside = sorted({n for _, n, dist, is7 in unmatched if is7 is True})
    outside = sorted({n for _, n, dist, is7 in unmatched if is7 is not True})
    (TEST / '_school_id_unmatched.json').write_text(
        json.dumps({
            'note': '升学通道官方名未命中实体表：7 区内需人工桥接（补进 build_entities.py 别名）；7 区外无 POI 实体，链接不可点属正确行为，原文保留展示。',
            'updated': '2026-09-12',
            'inside7_unmatched': inside,
            'outside7_or_unknown': outside,
        }, ensure_ascii=False, indent=1) + '\n', 'utf-8')
    print(f'\n7 区内未命中 {len(inside)} 个（待人工桥接）:')
    for n in inside[:30]:
        print('   ', n)
    print(f'\n7 区外/未知未命中 {len(outside)} 个（无实体，正常不可点）')
    if id_conflicts:
        print(f'\nid 键冲突 {len(id_conflicts)} 条（多名同 id，后者保底原文展示；待 registry alias 修复收敛）:')
        for k, sid in id_conflicts[:20]:
            print('   ', k, '→', sid)
    return 0


if __name__ == '__main__':
    sys.exit(main())
