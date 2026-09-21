#!/usr/bin/env python3
"""从 education_groups.json 生成 P3 覆盖清单 Markdown"""
import json, os
from collections import Counter, defaultdict

BASE = "/Users/bytedance/Developer/gz_school_research"
d = json.load(open(os.path.join(BASE, "data/registry/group/dist/education_groups.json")))
groups = d["groups"]
stats = d["stats"]

lines = []
lines.append("# 教育集团成员覆盖清单（P3）")
lines.append("")
lines.append("> 比对范围：`data/registry/group/dist/education_groups.json`（7区教育集团全量版，区教育局官方口径+招考办2026名额分配表+品牌组）")
lines.append(f"> 比对基准：POI 三层 `data/poi/dist/primary_poi.json`（960小学）/ `data/poi/dist/middle_poi.json` / `data/poi/dist/high_poi.json`（126高中）")
lines.append("> 匹配方法：normName 全等匹配（去\"广州市\"前缀、括号统一后去括号、去空白）+ entities.json 别名表复核 + 校区/区名变体复核")
lines.append("> 数据来源：各区政府/区教育局官网文件（见各集团 source_urls）；示范高中集团初中成员来自招考办2026名额分配表；8个重点品牌来自 brand_groups.json")
lines.append(f"> 更新日期：{d['updated']}")
lines.append("")

# 一、覆盖统计
lines.append("## 一、覆盖统计")
lines.append("")
lines.append("| 状态 | 数量 | 说明 |")
lines.append("|---|---|---|")
lines.append(f"| 精确命中 | {stats['poi_exact']} | normName 全等匹配 POI 三层 |")
lines.append(f"| 变体命中 | {stats['poi_variant']} | 校区后缀/区名前缀/简称/同校异名等写法差异，实际已覆盖 |")
lines.append(f"| 7区内真实缺失 | {stats['poi_missing_7dist']} | 7区内、高德未收录 POI 或新更名/新办校尚未入POI库 |")
lines.append(f"| 远郊不在POI范围 | {stats['poi_far']} | 花都/南沙/增城/从化及市外学校，POI 数据层当前仅覆盖7区 |")
lines.append(f"| **合计（成员校）** | **{stats['total_members']}** | |")
lines.append("")
lines.append(f"**集团总数：{stats['total_groups']}**（含跨区品牌集团2个）")
lines.append("")

# 分区统计
lines.append("### 分区统计")
lines.append("")
lines.append("| 区 | 集团数 | 成员数 | 精确命中 | 变体命中 | 7区内缺失 | 远郊 |")
lines.append("|---|---|---|---|---|---|---|")
district_order = ["越秀","海珠","天河","荔湾","白云","黄埔","番禺","跨区"]
for dist in district_order:
    gs = [g for g in groups if g["district"]==dist]
    if not gs: continue
    ms = [m for g in gs for m in g["members"]]
    exact = sum(1 for m in ms if m["poi_match"]=="精确命中")
    variant = sum(1 for m in ms if m["poi_match"]=="变体命中")
    missing = sum(1 for m in ms if m["poi_match"]=="7区内真实缺失")
    far = sum(1 for m in ms if m["poi_match"]=="远郊不在POI范围")
    lines.append(f"| {dist} | {len(gs)} | {len(ms)} | {exact} | {variant} | {missing} | {far} |")
lines.append("")

# 二、各区集团清单
lines.append("## 二、各区集团清单")
lines.append("")
for dist in district_order:
    gs = [g for g in groups if g["district"]==dist]
    if not gs: continue
    lines.append(f"### {dist}区（{len(gs)}个集团）")
    lines.append("")
    lines.append("| 集团 | 类型 | 核心校 | 成员数 | 来源 |")
    lines.append("|---|---|---|---|---|")
    for g in gs:
        core = "、".join(g.get("core",[]))
        src_count = len(g.get("source_urls",[]))
        lines.append(f"| {g['brand']} | {g.get('type','')} | {core} | {len(g.get('members',[]))} | {src_count}个官方源 |")
    lines.append("")

# 三、7区内真实缺失清单
lines.append("## 三、7区内真实缺失清单")
lines.append("")
missing_all = [(g, m) for g in groups for m in g["members"] if m["poi_match"]=="7区内真实缺失"]
# 分类
new_renamed = []  # 荔湾新更名
new_built = []    # 黄埔新办
pending = []      # 待开办
other = []        # 其他
for g, m in missing_all:
    name = m["name"]
    if "配建" in name or "待开办" in name or "地块" in name:
        pending.append((g, m))
    elif g["district"]=="荔湾" and ("附属" in name or "实验" in name):
        new_renamed.append((g, m))
    elif g["district"]=="黄埔":
        new_built.append((g, m))
    else:
        other.append((g, m))

lines.append(f"共 {len(missing_all)} 所，按性质分类：")
lines.append("")

if new_renamed:
    lines.append(f"### 3.1 2024-2026年新更名/新授权校（{len(new_renamed)}所，荔湾）")
    lines.append("")
    lines.append("这些学校在2023年荔湾小学集团化办学改革中更名（原校名+附属/实验后缀），高德POI尚未更新名称，实际学校存在。")
    lines.append("")
    lines.append("| 所属集团 | 学校名 | 学段 |")
    lines.append("|---|---|---|")
    for g, m in new_renamed:
        lines.append(f"| {g['brand']} | {m['name']} | {m.get('stage','')} |")
    lines.append("")

if new_built:
    lines.append(f"### 3.2 新办校未入POI库（{len(new_built)}所，黄埔）")
    lines.append("")
    lines.append("| 所属集团 | 学校名 | 学段 | 备注 |")
    lines.append("|---|---|---|---|")
    for g, m in new_built:
        lines.append(f"| {g['brand']} | {m['name']} | {m.get('stage','')} | 新办校，高德未收录 |")
    lines.append("")

if pending:
    lines.append(f"### 3.3 待开办配建校（{len(pending)}所，白云）")
    lines.append("")
    lines.append("规划配建学校，尚未开办，无实体POI。")
    lines.append("")
    lines.append("| 所属集团 | 学校名 | 备注 |")
    lines.append("|---|---|---|")
    for g, m in pending:
        lines.append(f"| {g['brand']} | {m['name']} | 待开办 |")
    lines.append("")

if other:
    lines.append(f"### 3.4 其他义务教育阶段真实缺口（{len(other)}所）")
    lines.append("")
    lines.append("| 所属集团 | 学校名 | 学段 | 所在区 | 备注 |")
    lines.append("|---|---|---|---|---|")
    for g, m in other:
        lines.append(f"| {g['brand']} | {m['name']} | {m.get('stage','')} | {g['district']} | 高德未收录POI |")
    lines.append("")

# 四、远郊不在POI范围
lines.append("## 四、远郊不在POI范围（花都/南沙/增城/从化/市外）")
lines.append("")
far_all = [(g, m) for g in groups for m in g["members"] if m["poi_match"]=="远郊不在POI范围"]
lines.append(f"共 {len(far_all)} 所。当前 POI 数据层仅覆盖7区，远郊4区及市外学校不在采集范围。")
lines.append("")
lines.append("| 所属集团 | 学校名 | 学段 | 所在远郊 |")
lines.append("|---|---|---|---|")
for g, m in far_all:
    # 推断远郊地区
    far_dist = ""
    for kw in ["花都","南沙","增城","从化","英德","清远"]:
        if kw in m["name"]:
            far_dist = kw
            break
    lines.append(f"| {g['brand']} | {m['name']} | {m.get('stage','')} | {far_dist} |")
lines.append("")

# 五、数据来源说明
lines.append("## 五、数据来源与口径说明")
lines.append("")
lines.append("### 5.1 各区官方文件")
lines.append("")
source_summary = {
    "越秀": "越秀区教育局《越秀区教育集团一览表》（2026-06-26，post_10874811），9个教育集团完整名单",
    "海珠": "海珠区教育局2025-11-13批次成立/扩容通知（海教〔2025〕196/197/198号 + 海教办〔2025〕9/10/11/12号）+ 2023年五中/97中集团文件，共10个集团",
    "天河": "天河区政府《天河区九大教育集团》总览（2026-07，post_10894356）+ 各集团成立通稿，9大集团52校（本表核实47校，差5校为老集团成员名册未公开）",
    "荔湾": "荔湾区创建全国义务教育优质均衡发展区自评报告（14集团/59校口径）+ 中学集团化方案（mpost_9110592）+ 小学集团化布局（mpost_9354813）+ 2025公办小学联系信息表（post_10495836），共15个集团（含广雅）",
    "黄埔": "黄埔区政府《黄埔区基础教育集团》总览（2026-07，post_10882461，13集团74校）+ 2022年授牌通报（post_8554368）+ 部门预算PDF + 市招考办名额分配表交叉确认",
    "白云": "白云区政府「1913」体系通稿（mpost_9567523，19个教育集团+13个教育联盟）+ 白云区教育局官方成员校名册，只录19个教育集团（不含13个教育联盟），已剔除幼儿园集团",
    "番禺": "番禺区政府总览（2026-04，post_10777705，53个集团含联盟/234校）+ 各集团成立/扩容通知，优先录核心区域9个集团，远郊村小联盟简略",
}
for dist in ["越秀","海珠","天河","荔湾","黄埔","白云","番禺"]:
    lines.append(f"- **{dist}**：{source_summary[dist]}")
lines.append("")
lines.append("### 5.2 与现有数据的关系")
lines.append("")
lines.append("- `education_groups_2026.json`（招考办2026名额分配表，43核心校/118初中成员）：7区内示范高中集团的初中成员已合并入本文件，远郊4区集团核心校不录（跨区成员标注远郊）")
lines.append("- `brand_groups.json`（8个重点品牌）：广铁一中、清华附中湾区学校作为跨区品牌集团录入；省实/广雅/执信/二中/广附/华附在各区已有对应集团，成员已合并")
lines.append("- `entities.json`：名称桥接别名表，用于POI匹配变体复核")
lines.append("")
lines.append("### 5.3 已知局限")
lines.append("")
lines.append("1. **黄埔区成员名册不完整**：hp.gov.cn 未发布「13集团×74校」单点枚举表，6个集团（怡园、开发区外国语、开发区二小、开发区中学、长洲、知识城/广外）成员名册有限，已核实22所成员，剩余约50校待官方文件补全")
lines.append("2. **天河区老集团成员差5校**：先烈东/广州中学/天外/113中四个老集团在 thnet.gov.cn 无完整成员通稿，成员划分依据地理集群+已知线索")
lines.append("3. **番禺区只录核心集团**：番禺53个集团含联盟，本表录9个核心区域集团，远郊村小集团/联盟未单独建条")
lines.append("4. **荔湾区多校区计数差异**：沙面6校区、康有为东漖/白鹅潭等为同法人多校区，本表按核心校单列计，与官方59校口径有差异")
lines.append("5. **33所7区内缺失**：主要为2024-2026新更名校（荔湾14所）、新办校（黄埔4所）、待开办配建校（白云3所）、白云义务教育缺口（10所）、品牌集团成员（1所），均非编造，实际学校存在但POI未收录")
lines.append("")
lines.append("### 5.4 不录入范围")
lines.append("")
lines.append("- 远郊4区（花都/南沙/增城/从化）的集团核心校不录，跨区到7区的成员校标注来源")
lines.append("- 幼儿园/幼教联盟不录（白云民航幼儿园集团已剔除）")
lines.append("- 教育联盟不录（白云13个教育联盟、番禺4个教育联盟、越秀6个小学学区均不录）")
lines.append("- 不用POI名称正则反推集团（用户明确禁止B方案）")
lines.append("")

out_path = os.path.join(BASE, "data/registry/group/docs/coverage/集团成员覆盖清单_P3.md")
with open(out_path, "w") as f:
    f.write("\n".join(lines))
print(f"已写入 {out_path}")
print(f"总行数: {len(lines)}")
