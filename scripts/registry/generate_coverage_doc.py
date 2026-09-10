#!/usr/bin/env python3
"""从 coverage_result.json 生成 P1 覆盖清单 Markdown 文档，
并入人工复核结论（同校异名、区字差异、简称变体等）。"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
data = json.load(open(os.path.join(ROOT, 'scripts/registry/coverage_result.json'), encoding='utf-8'))

# 人工复核修正：将 v3 脚本的"未命中"中实际覆盖的学校标注为变体命中
# key = norm_name, value = (修正后状态, 命中层, POI名, 备注)
MANUAL_FIX = {
    '广东华侨中学越秀校区': ('变体命中', '初中+高中', '广东华侨中学(起义路校区)', '招考办表用"越秀校区"代实际"起义路校区"（起义路位于越秀区），同校异名'),
    '广东华侨中学白云校区': ('变体命中', '初中+高中', '广东华侨中学(金沙洲校区)', '招考办表用"白云校区"代实际"金沙洲校区"（金沙洲位于白云区），同校异名'),
    '九十七中晓园学校': ('变体命中', '初中', '广州市第九十七中学晓园学校', '"九十七中"与"第九十七中学"写法差异'),
    '白云区黄石学校': ('变体命中', '初中+小学', '黄石学校(中学部)', '区名前缀+校区后缀差异；POI初中层为"黄石学校(中学部)"'),
    '白云区江高镇第三初级中学': ('变体命中', '初中', '广州市江高三中', '全称与简称差异'),
    '白云区龙归学校': ('变体命中', '初中+小学', '龙归学校(初中部)', '区名前缀+校区后缀差异'),
    '白云区广州空港实验中学': ('变体命中', '初中+高中', '广州空港实验中学(校本部)/(东校区)', '区名前缀差异；POI初中+高中层均有'),
    '番禺区实验中学': ('变体命中', '高中', '番禺实验中学', '区字差异（集团表带"区"，高德POI不带）；levels.json已收录为市示范性高中'),
}

def norm_name(s):
    return (s.replace('广州市','').replace('（','(').replace('）',')')
             .replace('(','').replace(')','').replace(' ','').replace('\t',''))

def get_final_status(item):
    """获取最终覆盖状态，优先人工复核"""
    nn = item['norm_name']
    if nn in MANUAL_FIX:
        return MANUAL_FIX[nn]
    return (item['status'], '', '', '')

# 重新统计
final_stats = {'精确命中': 0, '变体命中': 0, '真实缺失': 0, '远郊不在POI范围': 0}
all_schools = []  # (group_core, role, item, final_status_tuple)

for g in data['groups']:
    core = g['core']
    level = g['level']
    core_item = g['core']
    fs = get_final_status(core_item)
    if fs[0] == '未命中':
        fs = ('真实缺失', fs[1], fs[2], fs[3])
    final_stats[fs[0]] += 1
    all_schools.append((core['name'], '核心校', core_item, fs, level))
    
    for m in g['members']:
        fs = get_final_status(m)
        if fs[0] == '未命中':
            fs = ('真实缺失', fs[1], fs[2], fs[3])
        final_stats[fs[0]] += 1
        all_schools.append((core['name'], '成员校', m, fs, level))

# 生成 Markdown
lines = []
lines.append('# 教育集团成员覆盖清单（P1）')
lines.append('')
lines.append('> 比对范围：`data/registry/education_groups_2026.json`（招考办2026名额分配表，43核心校 + 118成员校 = 161校）')
lines.append('> 比对基准：POI 三层 `data/middle/schools-gz.json`（475初中）/ `data/primary/schools-gz.json`（931小学）/ `data/high/schools-gz.json`（126高中）')
lines.append('> 匹配方法：normName 全等匹配（去"广州市"前缀、括号统一后去括号、去空白）+ 校区/区名变体复核 + 高德逐校核实')
lines.append('> 数据来源：广州市招考办 http://gzzk.gz.gov.cn/gkmlpt/content/10/10809/post_10809470.html （2026-05-12）')
lines.append('')

lines.append('## 一、覆盖统计')
lines.append('')
lines.append('| 状态 | 数量 | 说明 |')
lines.append('|---|---|---|')
lines.append(f'| 精确命中 | {final_stats["精确命中"]} | normName 全等匹配 POI 三层 |')
lines.append(f'| 变体命中 | {final_stats["变体命中"]} | 校区后缀/区名前缀/简称/同校异名等写法差异，实际已覆盖 |')
lines.append(f'| 真实缺失 | {final_stats["真实缺失"]} | 7区内、高德未收录 POI，数据层缺失 |')
lines.append(f'| 远郊不在POI范围 | {final_stats["远郊不在POI范围"]} | 花都/南沙/增城/从化，POI 数据层当前仅覆盖7区（荔湾/越秀/海珠/天河/白云/黄埔/番禺） |')
lines.append(f'| **合计** | **{sum(final_stats.values())}** | |')
lines.append('')

lines.append('## 二、7区内真实缺失（高德未收录）')
lines.append('')
lines.append('以下学校在招考办集团表中存在，但高德地图未收录对应中学 POI，数据层无法补录（不编造坐标）。')
lines.append('')
lines.append('| 所属集团/核心校 | 角色 | 学校名 | 所在区 | 备注 |')
lines.append('|---|---|---|---|---|')
for group_core, role, item, fs, level in all_schools:
    if fs[0] == '真实缺失':
        lines.append(f'| {group_core} | {role} | {item["name"]} | {item.get("district","-")} | 高德搜索无对应中学POI |')
lines.append('')

lines.append('## 三、远郊不在7区POI范围（花都/南沙/增城/从化）')
lines.append('')
lines.append(f'共 {final_stats["远郊不在POI范围"]} 所。当前 POI 数据层仅覆盖7区（荔湾/越秀/海珠/天河/白云/黄埔/番禺），远郊4区学校不在采集范围。如需扩展远郊覆盖，见 P3。')
lines.append('')
lines.append('| 所属集团/核心校 | 角色 | 学校名 | 所在区 |')
lines.append('|---|---|---|---|')
for group_core, role, item, fs, level in all_schools:
    if fs[0] == '远郊不在POI范围':
        lines.append(f'| {group_core} | {role} | {item["name"]} | {item.get("district","-")} |')
lines.append('')

lines.append('## 四、逐集团覆盖明细')
lines.append('')

for g in data['groups']:
    core = g['core']
    level = g['level']
    core_item = g['core']
    fs = get_final_status(core_item)
    if fs[0] == '未命中':
        fs = ('真实缺失', fs[1], fs[2], fs[3])
    
    lines.append(f'### {core["name"]}（{level}）')
    lines.append('')
    lines.append('| 角色 | 学校名 | 覆盖状态 | 命中层 | 匹配POI名 | 备注 |')
    lines.append('|---|---|---|---|---|---|')
    
    # core row
    layers_str = fs[1] if fs[1] else '/'.join(core_item['layers'].keys()) if core_item['layers'] else '-'
    poi_str = fs[2] if fs[2] else '; '.join([v['poi_name'] for v in core_item['layers'].values()]) if core_item['layers'] else '-'
    note_str = fs[3] if fs[3] else ''
    lines.append(f'| 核心校 | {core_item["name"]} | {fs[0]} | {layers_str} | {poi_str} | {note_str} |')
    
    for m in g['members']:
        fs = get_final_status(m)
        if fs[0] == '未命中':
            fs = ('真实缺失', fs[1], fs[2], fs[3])
        layers_str = fs[1] if fs[1] else '/'.join(m['layers'].keys()) if m['layers'] else '-'
        poi_str = fs[2] if fs[2] else '; '.join([v['poi_name'] for v in m['layers'].values()]) if m['layers'] else '-'
        note_str = fs[3] if fs[3] else ''
        lines.append(f'| 成员校 | {m["name"]} | {fs[0]} | {layers_str} | {poi_str} | {note_str} |')
    lines.append('')

lines.append('## 五、方法与局限')
lines.append('')
lines.append('1. **匹配口径**：以 `packages/shared/src/support.ts` 的 `normName` 为基准（去"广州市"前缀、全半角括号统一后去括号、去空白），仅做全等匹配；对未命中学校逐校人工复核变体（校区后缀/区名前缀/简称/同校异名）。')
lines.append('2. **远郊限制**：POI 三层当前仅覆盖7区（荔湾/越秀/海珠/天河/白云/黄埔/番禺），花都/南沙/增城/从化不在采集范围，相关学校标注为"远郊不在POI范围"而非"缺失"。')
lines.append('3. **真实缺失**：7区内仅2所（南悦中学、三元里中学）高德未收录中学POI，不编造坐标，留待后续核实（可能为新校未收录、已更名合并、或招考办表用旧名）。')
lines.append('4. **完全中学**：部分核心校同时列为成员校（如番禺区实验中学、广州空港实验中学），表示该校为完全中学（含初中+高中），高中段已在 POI 层，初中段是否需单独补点需进一步确认。')
lines.append('5. **数据来源**：集团关系来自广州市招考办2026-05-12官方表；POI 坐标来自高德地图 Web 服务 API。')
lines.append('')

out_dir = os.path.join(ROOT, 'docs/education-groups-coverage')
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, '集团成员覆盖清单_P1.md')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print(f'文档已生成: {out_path}')
print(f'最终统计: {final_stats}')
