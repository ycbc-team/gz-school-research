"""重建 quota_matrix.json 三列(名额考生/省市/区属)
数据源：31 页官方 PDF 逐页整页目视 OCR（quota_vision_values.P），
覆盖此前逐格 Vision / 整行 OCR 的 6↔9 混淆、缺行、校名错位等问题。
本脚本只替换 schools 列表（kaosheng/sheng_quota/qu_quota + 校名修正 + 补缺行），
sz 明细与 school_id 尽量沿用旧矩阵；新增行按注册表已有 id 或按规则生成。
"""
import json, hashlib, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quota_vision_values as VV  # P: {page: {row: [kao, ss, qu]}}, P16_INSERT

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OLD = os.path.join(ROOT, 'data/linkage/quota_matrix.json')
GRID = os.path.join(ROOT, 'data/linkage/raw/quota_grid_final.json')
SN = os.path.join(ROOT, 'data/linkage/raw/schoolnames.json')
OUT = OLD

DIST_CODE = {'荔湾区':'440103','越秀区':'440104','海珠区':'440105','天河区':'440106',
             '白云区':'440111','黄埔区':'440112','番禺区':'440113','花都区':'440114',
             '南沙区':'440115','从化区':'440117','增城区':'440118'}
PAGE_DIST = {0:'荔湾区',1:'荔湾区',2:'越秀区',3:'越秀区',4:'海珠区',5:'海珠区',6:'天河区',7:'天河区',8:'天河区',
 9:'白云区',10:'白云区',11:'白云区',12:'白云区',13:'黄埔区',14:'黄埔区',15:'黄埔区',16:'番禺区',17:'番禺区',
 18:'番禺区',19:'番禺区',20:'花都区',21:'花都区',22:'花都区',23:'南沙区',24:'南沙区',25:'从化区',26:'从化区',
 27:'增城区',28:'增城区',29:'增城区',30:'增城区'}
HEADER_PAGES = {0,2,4,6,9,13,16,20,23,25,27}  # 区头所在页

# 官方区头
HDR = {'荔湾区':(6417,332,2053),'越秀区':(10225,543,2686),'海珠区':(8326,431,2036),
       '天河区':(10774,555,2673),'白云区':(13441,696,2272),'黄埔区':(10744,560,1984),
       '番禺区':(16024,838,4474),'花都区':(11223,599,2448),'南沙区':(7017,362,1419),
       '从化区':(6717,355,1486),'增城区':(14831,806,2250)}

# 校名修正（页行 -> 正确名）
# 注：(18,9) 官方原文"广州铁一中学（番禺校区）"（序号49，266/14/73），schoolnames 读残缺为"广州市铁"；
# (18,10) 官方原文"广州大学附属中学（番禺校区）"（序号50，557/29/154），曾误用 NAME_FIX 改成铁一，已移除。
NAME_FIX = {
    (0,6): '广州市第四中学丰宁学校',
    (0,7): '广州市西关培英中学',
    (18,9): '广州铁一中学（番禺校区）',
    (19,16): '广州市番禺区北正华学校',
    (28,18): '广州市斐思学校',
    (20,6): '广州市花都区新雅街清埔初级中学',
}

# school_id 解析：不再使用点对点 SID_FIX，统一走 resolve_school_id 通用匹配
# （区 + 名字/别名 → 注册表实体，初中学部优先），实体表变更后重跑本脚本自动联动。
# 匹配层级：norm 全等(3) > normName 复刻全等(2) > 去教育机构后缀 core(1) > 前缀包含(0.5)；
# 学部按 middle → primary → high 分层，歧义时同区优先。

# OCR 校名规范化（对旧矩阵沿用的校名也生效；只改名称不改 school_id 沿用）：
# 历史 OCR/录入把「第一一五中学」误写为 U+2014 破折号「第—一五中学」等，统一还原为「一」，
# 使通用匹配器可直接命中实体，避免错字下沉到下游各表（backfill 覆盖表不再兜底此类）。
def normalize_school_name(name: str) -> str:
    return (name or '').replace('\u2014', '一')

def names_for(pno):
    g = json.load(open(SN, encoding='utf-8'))
    ns = g.get(str(pno), [])
    if len(ns) >= 2 and ns[0] == '' and ns[1].endswith('区'):
        ns = ns[1:]
    return ns

def _norm(s: str) -> str:
    """去「广州市/广东/广州」前缀 + 去空白 + 全角括号转半角（保留括号内容）"""
    s = (s or '').replace('（', '(').replace('）', ')')
    s = re.sub(r'\s', '', s)
    return s.replace('广州市', '').replace('广东省', '').replace('广东', '').replace('广州', '')

def _pynorm(s: str) -> str:
    """复刻 TS normName：去括号符号 + 去「广州市/广东」前缀 + 去空白"""
    s = (s or '').replace('（', '(').replace('）', ')').replace('(', '').replace(')', '')
    return s.replace('广州市', '').replace('广东', '').replace(' ', '').strip()

_CORE_SUFFIX = ('初级中学', '初中部', '小学部', '中学校', '中学', '小学', '学校')
def _core(s: str) -> str:
    n = _norm(s)
    for suf in _CORE_SUFFIX:
        if n.endswith(suf) and len(n) > len(suf):
            return n[:-len(suf)]
    return n

_STAGE_ORDER = {'middle': 0, '初中': 0, '九年一贯': 0, 'primary': 1, 'poi': 1.5, 'high': 2, '': 2}

def _is_mid_stage(st: str) -> bool:
    return st in ('middle', '初中', '九年一贯')

class SidResolver:
    """quota 校名 -> 注册表实体 school_id 的通用解析器（实体表变更自动联动）。"""

    def __init__(self):
        self.ents = []
        try:
            reg = json.load(open(os.path.join(ROOT, 'data/registry/entities.json'), encoding='utf-8'))
            self.ents = reg.get('entities', reg) if isinstance(reg, dict) else reg
        except Exception:
            pass
        self.pois = []
        try:
            sg = json.load(open(os.path.join(ROOT, 'data/poi/dist/middle_poi.json'), encoding='utf-8'))
            self.pois = sg.get('schools', sg) if isinstance(sg, dict) else sg
        except Exception:
            pass
        self.known = {e.get('school_id') for e in self.ents if e.get('school_id')}
        self.warn = []

    def _candidates(self, name: str):
        qn, qp, qc = _norm(name), _pynorm(name), _core(name)
        q_is_mid = ('中学' in qn) and ('小学' not in qn)
        q_is_pri = ('小学' in qn) and ('中学' not in qn)
        cands = []
        for e in self.ents:
            keys = [e.get('name')] + list(e.get('aliases') or [])
            eid, st = e.get('school_id'), e.get('stage') or ''
            if not eid:
                continue
            hit = 0
            for k in keys:
                if k and _norm(k) == qn:
                    hit = 3
                    break
            if not hit:
                for k in keys:
                    if k and _pynorm(k) == qp:
                        hit = 2
                        break
            if not hit:
                for k in keys:
                    if not k:
                        continue
                    # core 兜底禁止「中学」↔「小学」学部交叉（如三元里中学≠三元里小学）
                    k_has_mid = ('中学' in k) and ('小学' not in k)
                    k_has_pri = ('小学' in k) and ('中学' not in k)
                    if (q_is_mid and k_has_pri) or (q_is_pri and k_has_mid):
                        continue
                    if _core(k) == qc and _norm(k) != qn:
                        hit = 1
                        break
            if not hit:
                for k in keys:
                    if k and _norm(k).startswith(qn) and len(_norm(k)) > len(qn):
                        hit = 0.5
                        break
            if hit:
                cands.append((hit, eid, st))
        if not cands:
            for p in self.pois:
                pn = p.get('name') or p.get('school') or ''
                if _norm(pn) == qn:
                    cands.append((3, p.get('school_id') or p.get('id'), 'poi'))
                    break
        return cands

    def resolve(self, name: str, dist: str, old_id: str | None):
        code = DIST_CODE.get(dist, '')
        cands = self._candidates(name)
        # 学部分层：middle 候选存在则只看 middle；否则 primary；再 high
        for layer in ('middle', '初中', '九年一贯', 'primary', 'poi', 'high'):
            lay = [c for c in cands if c[2] == layer]
            if lay:
                cands = lay
                break
        if cands:
            top = max(cands, key=lambda c: (c[0], -_STAGE_ORDER.get(c[2], 2)))
            best = [c for c in cands if c[0] == top[0] and _STAGE_ORDER.get(c[2], 2) == _STAGE_ORDER.get(top[2], 2)]
            if len(best) > 1:
                dc = dist.replace('市', '')
                in_dist = []
                for c in best:
                    e2 = next((x for x in self.ents if x.get('school_id') == c[1]), None)
                    if e2 and (dc in (e2.get('name') or '') or any(dc in a for a in (e2.get('aliases') or []))):
                        in_dist.append(c)
                if len(in_dist) == 1:
                    best = in_dist
                else:
                    best = []
            new = best[0][1] if best else None
        else:
            new = None
        # 决策：有效旧 id 且区一致且含 middle 学部 → 沿用（稳定锚点，防实体表矛盾回归）
        if old_id in self.known:
            ok_region = not code or old_id.startswith(f'gz-{code}-')
            old_mid = any(e.get('school_id') == old_id and _is_mid_stage(e.get('stage') or '') for e in self.ents)
            if ok_region and old_mid:
                return old_id
            if ok_region and old_id == new:
                return old_id
            new_mid = new and any(e.get('school_id') == new and _is_mid_stage(e.get('stage') or '') for e in self.ents)
            if ok_region:
                if new_mid:
                    return new
                return old_id
            if new and (not code or new.startswith(f'gz-{code}-')):
                return new
            self.warn.append(f'旧 id 区不一致且匹配器无同区结果：{name} 旧 {old_id} 新 {new}')
            return old_id
        if new:
            return new
        h = hashlib.md5(name.encode('utf-8')).hexdigest()[:8]
        self.warn.append(f'未匹配到实体：{name}（生成占位 {h}）')
        return f'gz-{code}-{h}'

def main():
    old = json.load(open(OLD, encoding='utf-8'))
    grid = json.load(open(GRID, encoding='utf-8'))
    # 旧矩阵 (page,row) -> rec
    old_by = {}
    for s in old['schools']:
        old_by[(s['page'], s['row'])] = s
    resolver = SidResolver()

    schools = []
    districts = []
    for pno in sorted(PAGE_DIST):
        dist = PAGE_DIST[pno]
        if pno in HEADER_PAGES and dist not in districts:
            districts.append(dist)
        g = grid[str(pno)]
        nrows = len(g['rows']) // 2
        if nrows == 0:
            continue
        names = names_for(pno)
        # 每页行计划: (grid_row 或 None=插入, 插入名, 插入值)
        plan = []
        if pno == 16:
            for r in range(1, 9):
                plan.append((r, None, None))
            for _, nm, val in VV.P16_INSERT:
                if nm.startswith('广东第二师范学院广州南站'):
                    plan.append((None, nm, val))
            for r in range(9, 18):
                plan.append((r, None, None))
            for _, nm, val in VV.P16_INSERT:
                if nm.startswith('广东第二师范学院番禺附属'):
                    plan.append((None, nm, val))
        else:
            r0 = 1 if pno in HEADER_PAGES else 0
            for r in range(r0, nrows):
                plan.append((r, None, None))
        for item in plan:
            r, ins_name, ins_val = item
            if r is None:
                name = normalize_school_name(ins_name)
                kao, ss, qu = ins_val
                rec = {'page': pno, 'row': None, 'school': name,
                       'kaosheng': kao, 'sheng_quota': ss, 'qu_quota': qu,
                       'sz': {}, 'sz_sum': 0, 'is_district_head': False,
                       'district': dist}
            else:
                name = normalize_school_name(NAME_FIX.get((pno, r)) or (names[r] if r < len(names) else ''))
                if not name:
                    print(f'!! p{pno} r{r} 无校名，跳过'); continue
                val = VV.P.get(pno, {}).get(r)
                if val is None:
                    print(f'!! p{pno} r{r} {name} 无目视值，跳过'); continue
                rec = {'page': pno, 'row': r, 'school': name,
                       'kaosheng': val[0], 'sheng_quota': val[1], 'qu_quota': val[2]}
                o = old_by.get((pno, r))
                if o:
                    rec['sz'] = o.get('sz', {})
                    rec['sz_sum'] = o.get('sz_sum', 0)
                    if o.get('school_id'):
                        rec['school_id'] = o['school_id']
                else:
                    rec['sz'] = {}
                    rec['sz_sum'] = 0
                rec['is_district_head'] = False
                rec['district'] = dist
            if 'school_id' not in rec:
                rec['school_id'] = resolver.resolve(rec['school'], dist, None)
            else:
                rec['school_id'] = resolver.resolve(rec['school'], dist, rec['school_id'])
            schools.append(rec)

    # 校验区级合计
    agg = {}
    for s in schools:
        d = agg.setdefault(s['district'], [0, 0, 0])
        d[0] += s['kaosheng'] or 0
        d[1] += s['sheng_quota'] or 0
        d[2] += s['qu_quota'] or 0
    ok_all = True
    for d, t in HDR.items():
        a = agg.get(d, [0, 0, 0])
        ok = tuple(a) == t
        ok_all = ok_all and ok
        mark = '✓' if ok else '✗'
        print(f'{d}: 考生{a[0]}/{t[0]} 省市{a[1]}/{t[1]} 区属{a[2]}/{t[2]} {mark}')
    print(f'总学校 {len(schools)}，区级合计{"全部对齐" if ok_all else "存在残差"}')
    if resolver.warn:
        print(f'[school_id 警告 {len(resolver.warn)}]')
        for w in resolver.warn:
            print('  -', w)
    else:
        print('[school_id] 全部命中实体或沿用有效 id')

    out = dict(old)
    out['schools'] = schools
    out['districts'] = districts
    out['updated'] = '2026-09-15'
    # 幂等 note：先剥离历史追加段，再一次性写入（可重复重跑，不累积重复文本）
    REBUILD_NOTE = (' 2026-09-15 重建：31页整页目视复核三列（考生/省市/区属），修正6↔9混淆、补回缺行'
                    '（番禺二师南站附属/二师番禺附中、荔湾四中丰宁/海龙博雅、花都清埔初级），修复荔湾西关培英校名错位。')
    SZ_GAP_NOTE = ' 二师南站附属/二师番禺附中为本次补行，sz 分额明细暂缺(sz_sum=0)。'
    base = old.get('note', '')
    for seg in (REBUILD_NOTE, SZ_GAP_NOTE):
        base = base.replace(seg, '')
    out['note'] = base.rstrip() + REBUILD_NOTE + SZ_GAP_NOTE
    json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=1, sort_keys=True)  # 固定字段顺序，防重跑漂移
    print('保存', OUT)

if __name__ == '__main__':
    main()
