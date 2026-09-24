#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""区属高中名额分配到本区初中：视觉校验表（src）→ 规范表（B 层）

数据源：
- data/linkage/src/district_quota_vision.json   视觉校验权威表（329 所，人工逐区目视读取，含出处）
- data/linkage/parsed/quota_grid_final.json     OCR 网格（仅作对照校验，不当数据源）
- data/linkage/parsed/schoolnames.json          OCR 校名（对照用）

历史：fd72c57（视觉校验 297→330 所）/ a6c37a9（9 大行错位）曾直接改 dist 产物、未写回脚本，
导致 OCR 基线（297 所）与提交版（329 所）长期脱节。本脚本将视觉表固化为 src 校正源，
OCR 网格降级为校验参照：重跑时对比告警（漏读/错值），不再覆盖数据。

输出：data/linkage/parsed/canonical/district_quota.json
      {updated, source, note, data: {初中名: {区属高中POI名: 名额}}}
      （无 middle_school_ids——由 C 层 backfill_school_ids.py 生成）
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LINK = os.path.join(ROOT, 'data', 'linkage')
VISION = os.path.join(LINK, 'src', 'district_quota_vision.json')
GRID = os.path.join(LINK, 'parsed', 'quota_grid_final.json')
SN = os.path.join(LINK, 'parsed', 'schoolnames.json')
OUT = os.path.join(LINK, 'parsed', 'canonical', 'district_quota.json')

# 每区区属列短名（col24 起，按表头从左到右）→ POI 全名（OCR 对照用）
DISTRICT_COLS = {
  '荔湾区': ['广州市第一中学(高中部)', '广州市第四中学(高中部锐园校区)', '广州市南海中学(高中部)',
            '广州市西关外国语学校(高中部)', '广州市真光中学(本部校区)', '广州市真光中学(汾水校区)',
            '广州市真光中学(广钢校区)'],
  '越秀区': ['广州市第七中学(高中部)', '广州市第七中学(麓湖校区)', '广州市第十三中学',
            '广州市第十六中学', '广州市第十六中学(水荫校区)', '广州市第十七中学',
            '广东实验中学越秀学校', '培正中学', '广州市育才中学(西校区)'],
  '海珠区': ['广州市第五中学', '广州市第五中学(金碧校区)', '广州市南武中学(高中部)',
            '广州市南武中学(岭南画派纪念校区)', '广州市第九十七中学', '广州市第九十七中学(江南新苑校区)',
            '广州市第四十一中学', '广州市海珠外国语实验中学', '广州市海珠外国语实验中学(江海校区)'],
  '天河区': ['广州中学(凤凰校区)', '广州市第七十五中学(天平架校区)', '广州市第一一三中学(金融城校区)',
            '广州市第一一三中学(元岗校区)', '广州市第八十九中学', '广州市天河中学(珠江新城校区)',
            '广州奥林匹克中学(高中部)', '广州市天河外国语学校(珠江新城校区)', '广州市天河外国语学校(智慧城校区)'],
  '白云区': ['广州市培英中学(云城校区)', '广州市培英中学(鹤洞校区)', '广州市第六十五中学(同德校区)',
            '广州市第六十五中学(江府校区)', '广州大同中学(高中部)', '广州市白云中学',
            '广州彭加木纪念中学', '广州市广外实验中学', '广州空港实验中学(校本部)'],
  '黄埔区': ['广州市第八十六中学', '广州市黄埔区玉泉学校', '广州市黄埔军校中学', '广州石化中学',
            '北京师范大学广州实验学校', '广州市黄埔区开元学校', '广州实验中学', '广州市黄埔区苏元学校'],
  '番禺区': ['广东仲元中学', '广东番禺中学', '广州市番禺区实验中学', '象贤中学', '石碁中学',
            '洛溪新城中学', '禺山高级中学', '石北中学', '番禺区石楼中学', '南村中学',
            '广州市番禺区大龙中学', '广东第二师范学院番禺附属中学'],
}
# 页 → 区（OCR 对照用）
PAGE_DISTRICT = {0: '荔湾区', 1: '荔湾区', 2: '越秀区', 3: '越秀区', 4: '海珠区', 5: '海珠区',
                 6: '天河区', 7: '天河区', 8: '天河区', 9: '白云区', 10: '白云区', 11: '白云区', 12: '白云区',
                 13: '黄埔区', 14: '黄埔区', 15: '黄埔区', 16: '番禺区', 17: '番禺区', 18: '番禺区', 19: '番禺区'}


def clean(s):
    if not s:
        return None
    s2 = re.sub(r'[^\d]', '', str(s))
    return int(s2) if s2 else None


def normalize(name: str) -> str:
    """校名规范化（OCR 对照用）：破折号错字还原 + 去空白"""
    return (name or '').replace('\u2014', '一').replace(' ', '').strip()


def build_ocr_table():
    """OCR 网格区属列组装（对照参照，与历史 build_district_quota.py 同逻辑）"""
    g = json.load(open(GRID, encoding='utf-8'))
    sn = json.load(open(SN, encoding='utf-8'))
    result = {}
    for pno in sorted(g, key=int):
        pg = g[pno]
        names = sn.get(pno, [])
        if int(pno) not in PAGE_DISTRICT:
            continue
        cols = DISTRICT_COLS[PAGE_DISTRICT[int(pno)]]
        nrows = len(pg['rows']) // 2
        for r in range(nrows):
            name = names[r] if r < len(names) else ''
            if not name or re.match(r'^.{2,4}区$', name):
                continue
            row = {}
            for i, hn in enumerate(cols):
                v = clean(pg['data'].get(str(24 + i), {}).get(str(r), ''))
                if v:
                    row[hn] = v
            if row:
                result[normalize(name)] = row
    return result


def compare_ocr(vision_data, ocr):
    """视觉权威表 vs OCR 网格：报告差异（不覆盖）。返回 (告警数, 详情行)"""
    warnings = []
    vision_norm = {}
    for k, v in vision_data.items():
        vision_norm.setdefault(normalize(k), []).append((k, v))
    ocr_keys = set(ocr)
    vis_keys = set(vision_norm)
    # 1. 视觉表有、OCR 无（历史漏读/错名）
    missing = vis_keys - ocr_keys
    for k in sorted(missing):
        warnings.append(f'OCR 漏读 {len(vision_norm[k])} 校: {vision_norm[k][0][0]}')
    # 2. OCR 有、视觉表无（OCR 错名/残次）
    extra = ocr_keys - vis_keys
    for k in sorted(extra):
        sample = next(iter(ocr[k]), '')
        warnings.append(f'OCR 多出(错名/残次): {sample}')
    # 3. 同名值差异
    for k in sorted(vis_keys & ocr_keys):
        for vis_name, vrow in vision_norm[k]:
            orow = ocr[k]
            for hn, v in sorted(vrow.items()):
                ov = orow.get(hn)
                if ov is not None and ov != v:
                    warnings.append(f'值差 {vis_name} {hn}: 视觉 {v} vs OCR {ov}')
    return warnings


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    vision = json.load(open(VISION, encoding='utf-8'))
    data = vision['data']

    # OCR 对照（告警不覆盖）
    try:
        ocr = build_ocr_table()
        warnings = compare_ocr(data, ocr)
        print(f'OCR 对照: 视觉 {len(data)} 所 vs OCR {len(ocr)} 所，差异告警 {len(warnings)} 条')
        for w in warnings[:40]:
            print('  -', w)
        if len(warnings) > 40:
            print(f'  … 其余 {len(warnings) - 40} 条见 src/district_quota_vision.json note（历史已知错值家族）')
    except FileNotFoundError as e:
        print(f'!! OCR 对照跳过（缺源文件: {e}）')

    out = {
        'title': '区属高中名额分配到本区初中（B 层规范表，视觉校验权威值）',
        'updated': '2026',
        'source': vision['source'],
        'note': vision['note'],
        'data': data,
    }
    json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=1, sort_keys=True)
    print('保存', OUT, f'({len(data)} 所初中)')


if __name__ == '__main__':
    main()
