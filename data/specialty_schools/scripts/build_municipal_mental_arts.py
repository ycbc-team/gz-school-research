#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compile Guangzhou municipal mental health education characteristic schools
and aesthetic/art education pilot schools into a UTF-8-BOM CSV.
"""

import csv
import os

OUTPUT_PATH = "/Users/bytedance/Developer/gz_school_research/data/specialty_schools/municipal_mental_arts.csv"

HEADER = [
    "学校名称", "所在区", "类别", "级别", "批次",
    "认定年份", "认定项目全称", "发文单位", "官方来源URL", "备注"
]

# ---- Source URLs ----
URL_BATCH7 = "https://jyj.gz.gov.cn/gk/zfxxgkml/bmwj/qtwj/content/post_10196843.html"
URL_BATCH6 = "https://jyj.gz.gov.cn/yw/tzgg/content/post_8938203.html"
URL_BATCH5 = "https://static.nfapp.southcn.com/content/202001/22/c3014073.html"
URL_MEIYU  = "https://jyj.gz.gov.cn/gkmlpt/content/10/10807/mpost_10807656.html"

DISTRICTS = [
    "越秀区", "海珠区", "荔湾区", "天河区", "白云区", "黄埔区",
    "番禺区", "花都区", "南沙区", "从化区", "增城区"
]

def build_remark(is_inferred, is_unknown, extra_note=""):
    """Build remark string."""
    parts = []
    if is_unknown:
        parts.append("区未知")
    elif is_inferred:
        parts.append("区推断")
    if extra_note:
        parts.append(extra_note)
    return ";".join(parts)

def make_row(name, district, inferred, unknown, category, batch, year, project, org, url, extra_note=""):
    remark = build_remark(inferred, unknown, extra_note)
    return [name, district, category, "市级", batch, year, project, org, url, remark]

rows = []

# ============================================================
# 第七批广州市中小学心理健康教育特色学校 (2025-04-02)
# 43 schools
# ============================================================
C_MH = "心理健康教育"
PROJ_MH = "广州市中小学心理健康教育特色学校"
ORG = "广州市教育局"

# (name, district, inferred, unknown, extra_note)
batch7 = [
    ("清华附中湾区学校", "天河区", True, False, "清华附中湾区学校位于天河区奥体南路"),
    ("广州市城市建设职业学校", "", False, True, "市属中职学校，多校区"),
    ("广州市第三中学", "越秀区", True, False, "位于越秀区大南路"),
    ("广州市第七中学东山学校", "越秀区", True, False, "位于越秀区东山"),
    ("广州市第一中学双桥学校", "荔湾区", True, False, "一中双桥学校位于荔湾区"),
    ("广州市东风实验学校", "越秀区", True, False, "位于越秀区"),
    ("广州市五中滨江学校", "海珠区", True, False, "位于海珠区滨江路"),
    ("广州市第八十九中学", "天河区", True, False, "位于天河区龙洞"),
    ("广州市第一一三中学", "天河区", True, False, "位于天河区"),
    ("广州市白云中学", "白云区", False, False, ""),
    ("广州市白云区平沙培英学校", "白云区", False, False, ""),
    ("广州市庆丰实验学校", "白云区", True, False, "位于白云区石井庆丰"),
    ("广州市南沙潭山中学", "南沙区", False, False, ""),
    ("广东第二师范学院附属南沙珠江学校", "南沙区", True, False, "位于南沙区"),
    ("广东第二师范学院番禺附属初级中学", "番禺区", True, False, "位于番禺区"),
    ("广东番禺中学附属学校", "番禺区", True, False, "位于番禺区"),
    ("广州市花都区秀全中学", "花都区", False, False, ""),
    ("广州市花都区实验中学", "花都区", False, False, ""),
    ("广州市花都区新华街云山学校", "花都区", False, False, ""),
    ("广州市增城区中新中学", "增城区", False, False, ""),
    ("广州增城外国语实验中学", "增城区", True, False, "位于增城区"),
    ("广州市从化区第五中学", "从化区", False, False, ""),
    ("广州市从化区第二中学", "从化区", False, False, ""),
    ("广州市从化区鳌头中学", "从化区", False, False, ""),
    ("广州市启聪学校", "白云区", True, False, "市属特教学校，位于白云区石井"),
    ("广州市越秀区清水濠小学", "越秀区", False, False, ""),
    ("广州市越秀区红火炬小学", "越秀区", False, False, ""),
    ("广州市真光中学附属坑口小学", "荔湾区", True, False, "位于荔湾区芳村坑口"),
    ("广州市海珠区晓港湾小学", "海珠区", False, False, ""),
    ("广州市海珠区宝玉直小学", "海珠区", False, False, ""),
    ("广州市海珠区前进路小学", "海珠区", False, False, ""),
    ("广州市天河区侨乐小学", "天河区", False, False, ""),
    ("广州市天河区棠下小学", "天河区", False, False, ""),
    ("广州市白云区方圆实验小学", "白云区", False, False, ""),
    ("广州市白云区华师附中实验小学", "白云区", False, False, ""),
    ("广州市南沙区金洲小学", "南沙区", False, False, ""),
    ("广州大学附属小学", "番禺区", True, False, "位于番禺区大学城"),
    ("广州市番禺区亚运城小学", "番禺区", False, False, ""),
    ("广州市番禺区毓秀小学", "番禺区", False, False, ""),
    ("广州市花都区狮岭镇育华小学", "花都区", False, False, ""),
    ("广州市增城区香江学校", "增城区", False, False, ""),
    ("从化希贤小学", "从化区", True, False, "位于从化区"),
    ("广州市从化区雅居乐小学", "从化区", False, False, ""),
]

for name, dist, inf, unk, note in batch7:
    rows.append(make_row(name, dist, inf, unk, C_MH, "第七批", "2025",
                         PROJ_MH, ORG, URL_BATCH7, note))

# ============================================================
# 第六批广州市中小学心理健康教育特色学校 (2023-04-20)
# 41 schools
# ============================================================
batch6 = [
    ("广州市第六中学", "海珠区", True, False, "位于海珠区新港西路"),
    ("广东华侨中学", "越秀区", True, False, "位于越秀区起义路"),
    ("广州市协和中学", "白云区", True, False, "位于白云区"),
    ("广州市财经商贸职业学校", "", False, True, "市属中职学校"),
    ("广州市第七中学", "越秀区", True, False, "位于越秀区"),
    ("广州市越秀区铁一小学", "越秀区", False, False, ""),
    ("广州市越秀区雅荷塘小学", "越秀区", False, False, ""),
    ("广州市荔湾区康有为纪念小学", "荔湾区", False, False, ""),
    ("广州市荔湾区增滘小学", "荔湾区", False, False, ""),
    ("广州市海珠区知信小学", "海珠区", False, False, ""),
    ("广州市海珠区宝玉直实验小学", "海珠区", False, False, ""),
    ("广州奥林匹克中学", "天河区", True, False, "位于天河区"),
    ("广州市第七十五中学", "天河区", True, False, "位于天河区"),
    ("广州市天河区天府路小学", "天河区", False, False, ""),
    ("广州市天河区华阳小学", "天河区", False, False, ""),
    ("广州市天河第一小学", "天河区", False, False, ""),
    ("广州彭加木纪念中学", "白云区", True, False, "位于白云区石井"),
    ("广东外语外贸大学实验中学", "白云区", True, False, "位于白云区"),
    ("广州市白云区同和小学", "白云区", False, False, ""),
    ("广州市白云区云英实验学校", "白云区", False, False, ""),
    ("广州开发区外国语学校", "黄埔区", True, False, "位于黄埔区"),
    ("广州市黄埔区开元学校", "黄埔区", False, False, ""),
    ("广州市黄埔区玉泉学校", "黄埔区", False, False, ""),
    ("广州市南沙横沥中学", "南沙区", True, False, "位于南沙区横沥"),
    ("华南师范大学附属南沙小学", "南沙区", True, False, "位于南沙区"),
    ("广州市番禺区东怡小学", "番禺区", False, False, ""),
    ("广州市番禺区洛浦中心小学", "番禺区", False, False, ""),
    ("广州市番禺区实验中学", "番禺区", False, False, ""),
    ("广州市番禺区市桥南阳里小学", "番禺区", False, False, ""),
    ("广州市番禺区钟村中学", "番禺区", False, False, ""),
    ("广州市花都区邝维煜纪念中学", "花都区", False, False, ""),
    ("广州市花都区狮岭中学", "花都区", False, False, ""),
    ("广州市花都区秀全外国语学校", "花都区", False, False, ""),
    ("华南师范大学附属花都学校", "花都区", True, False, "位于花都区"),
    ("广州市增城区凤凰城中英文学校", "增城区", False, False, ""),
    ("广大附中增城实验中学", "增城区", True, False, "位于增城区"),
    ("广州市增城区高级中学", "增城区", False, False, ""),
    ("广州市增城区荔城街第二小学", "增城区", False, False, ""),
    ("广州市从化区职业技术学校", "从化区", False, False, ""),
    ("广州市从化区第四中学", "从化区", False, False, ""),
    ("广州市从化区吕田中学", "从化区", False, False, ""),
]

for name, dist, inf, unk, note in batch6:
    rows.append(make_row(name, dist, inf, unk, C_MH, "第六批", "2023",
                         PROJ_MH, ORG, URL_BATCH6, note))

# ============================================================
# 第五批广州市中小学心理健康教育特色学校 (2020-01-21)
# 13 schools (from 南方+ repost of official notice)
# ============================================================
batch5_extra = "来源为南方+转载官方通知，jyj.gz.gov.cn原始链接未直接定位"
batch5 = [
    ("广州市执信中学", "越秀区", True, False, "位于越秀区"),
    ("广州大学附属中学", "越秀区", True, False, "本部位于越秀区黄华路"),
    ("广州市西关培英中学", "荔湾区", True, False, "位于荔湾区西关"),
    ("中山大学附属中学", "海珠区", True, False, "位于海珠区新港西路"),
    ("广州市江南外国语学校", "海珠区", True, False, "位于海珠区"),
    ("广州白云广雅实验学校", "白云区", True, False, "位于白云区"),
    ("广州市番禺区石碁中学", "番禺区", False, False, ""),
    ("广州市南沙麒麟中学", "南沙区", True, False, "位于南沙区"),
    ("广州市增城区郑中钧中学", "增城区", False, False, ""),
    ("广州市越秀区东风西路小学", "越秀区", False, False, ""),
    ("广州市海珠区绿翠小学", "海珠区", False, False, ""),
    ("广州市番禺区南村镇中心小学", "番禺区", False, False, ""),
    ("广东第二师范学院番禺区附属小学", "番禺区", True, False, "位于番禺区"),
]

for name, dist, inf, unk, note in batch5:
    combined_note = ";".join([n for n in [note, batch5_extra] if n])
    rows.append(make_row(name, dist, inf, unk, C_MH, "第五批", "2020",
                         PROJ_MH, ORG, URL_BATCH5, combined_note))

# ============================================================
# 首批广州市中小学学科美育教学改革试点项目校 (2026-05-09)
# 30 schools, grouped by district in official announcement.
# ============================================================
C_MY = "美育/艺术教育"
PROJ_MY = "广州市中小学学科美育教学改革试点项目校"

meiyu = [
    # 一、市属学校 (district not given in grouping; infer)
    ("广东广雅中学", "荔湾区", True, False, "市属学校，本部位于荔湾区西村"),
    ("广州市第二中学", "越秀区", True, False, "市属学校，本部位于越秀区应元路"),
    ("广州市第六中学", "海珠区", True, False, "市属学校，位于海珠区新港西路"),
    ("广州外国语学校", "南沙区", True, False, "市属学校，位于南沙区"),
    ("清华附中湾区学校", "天河区", True, False, "市属学校，位于天河区奥体南路"),
    # 二、越秀区
    ("广州市培正中学", "越秀区", False, False, ""),
    ("广州市越秀区署前路小学", "越秀区", False, False, ""),
    ("广州市越秀区东山实验小学", "越秀区", False, False, ""),
    ("广州市越秀区农林下路小学", "越秀区", False, False, ""),
    # 三、海珠区
    ("广州市南武中学", "海珠区", False, False, ""),
    ("广州市海珠区逸景第一小学", "海珠区", False, False, ""),
    # 四、荔湾区
    ("广州市第一中学", "荔湾区", False, False, ""),
    ("广州市真光中学", "荔湾区", False, False, ""),
    ("广州市荔湾区沙面小学", "荔湾区", False, False, ""),
    # 五、天河区
    ("广州市天河区四海小学", "天河区", False, False, ""),
    # 六、白云区
    ("广州市培英中学", "白云区", False, False, ""),
    ("广东外语外贸大学实验中学", "白云区", False, False, ""),
    ("广州市白云区方圆实验小学", "白云区", False, False, ""),
    ("广州市白云区华师附中实验小学", "白云区", False, False, ""),
    # 七、黄埔区
    ("广州市八十六中学", "黄埔区", False, False, ""),
    ("北京师范大学广州实验学校", "黄埔区", False, False, ""),
    ("广州开发区第二小学", "黄埔区", False, False, ""),
    # 八、花都区
    ("广州市花都区新华中学", "花都区", False, False, ""),
    # 九、番禺区
    ("广东番禺中学附属学校", "番禺区", False, False, ""),
    ("广州市番禺区罗家桥虹小学", "番禺区", False, False, ""),
    # 十、南沙区
    ("华南师范大学附属南沙中学", "南沙区", False, False, ""),
    ("广州外国语学校附属学校", "南沙区", False, False, ""),
    ("华南师范大学附属南沙小学", "南沙区", False, False, ""),
    # 十一、从化区
    ("广州市从化区街口街团星小学", "从化区", False, False, ""),
    ("广州市从化区良口镇善施学校", "从化区", False, False, ""),
]

for name, dist, inf, unk, note in meiyu:
    rows.append(make_row(name, dist, inf, unk, C_MY, "首批", "2026",
                         PROJ_MY, ORG, URL_MEIYU, note))

# ============================================================
# Write CSV with UTF-8 BOM
# ============================================================
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(HEADER)
    writer.writerows(rows)

print(f"CSV written to: {OUTPUT_PATH}")
print(f"Total rows (excluding header): {len(rows)}")

from collections import Counter
batch_counts = Counter()
category_counts = Counter()
for r in rows:
    batch_counts[(r[2], r[4], r[5])] += 1
    category_counts[r[2]] += 1

print("\n--- Summary by category ---")
for cat, cnt in category_counts.items():
    print(f"  {cat}: {cnt} schools")

print("\n--- Summary by batch ---")
for (cat, batch, year), cnt in sorted(batch_counts.items(), key=lambda x: x[0][2]):
    print(f"  {batch} ({year}) [{cat}]: {cnt} schools")

# Check district coverage
unknown_district = [r[0] for r in rows if not r[1]]
print(f"\nSchools with unknown district: {len(unknown_district)}")
for s in unknown_district:
    print(f"  - {s}")
