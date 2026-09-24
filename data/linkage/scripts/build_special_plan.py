#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 2026 年体育/艺术特长生招生计划（学校 × 项目）。

- 输入：data/linkage/raw/special/附件1.2026年体育艺术类特长生布局项目及计划学校明细表.docx
       （官方《广州市教育局关于印发2026年普通高中学校体育艺术类特长生招生计划的通知》附件1）
- 输出：data/linkage/parsed/special/plan_special_2026.json
口径：计划数 = 各校（校区）体育/艺术特长生招生计划（含优秀体育后备人才在内的小计）；
      项目行人数为该项目计划数，括号内"其中体育后备人才不超N人"为内部限制，不进主数值。
校验：每校体育/艺术小计须等于该项目计划之和，否则报错（防止解析漂移）。
"""
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

SRC = 'data/linkage/raw/special/附件1.2026年体育艺术类特长生布局项目及计划学校明细表.docx'
OUT = sys.argv[1] if len(sys.argv) > 1 else 'data/linkage/parsed/special/plan_special_2026.json'
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def extract_tables():
    z = zipfile.ZipFile(SRC)
    xml = z.read('word/document.xml').decode('utf-8')
    root = ET.fromstring(xml)
    tables = []
    for tbl in root.iter(W + 'tbl'):
        rows = []
        for tr in tbl.iter(W + 'tr'):
            cells = [''.join(t.text or '' for t in tc.iter(W + 't')).strip()
                     for tc in tr.iter(W + 'tc')]
            if any(cells):
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def normalize_school(s: str) -> str:
    """领军龙行的学校名规范化：去掉"（"领军龙"学校）"标记并补齐右括号。
    如「广州市执信中学（执信路校区，"领军龙"学校）」→「广州市执信中学（执信路校区）」。
    """
    # 两种官方写法：①「（执信路校区，"领军龙"学校）」→ 去「，"领军龙"学校）」；
    # ②「（"领军龙"学校）」→ 去「（"领军龙"学校）」
    s = re.sub(r'[，,][“"]领军龙[”"]学校[)）]$', '', s.strip())
    s = re.sub(r'[（(][“"]领军龙[”"]学校[)）]$', '', s)
    if s.count('（') > s.count('）'):
        s += '）'
    return s


def plan_int(s: str) -> int:
    m = re.match(r'\d+', s.strip())
    if not m:
        raise ValueError(f'cannot parse plan number: {s!r}')
    return int(m.group())


def parse():
    schools = []
    for rows in extract_tables():
        header = rows[0]
        # 附件2 工作安排表 / 附件3 咨询电话表：跳过
        if any(('工作事项' in c) or ('时间' in c) for c in header):
            continue
        if any('单位名称' in c for c in header):
            continue
        cur = None
        for cells in rows:
            # 表头
            if cells[0].startswith('序号'):
                continue
            non_empty = [c for c in cells if c]
            if not non_empty:
                continue
            if cells[0].strip().isdigit():
                # 附件2 工作安排表混入：[序号, 时间, 工作内容, ...] — 跳过
                if re.match(r'^\d+月', cells[1].strip()):
                    continue
                # 领军龙足球试点单列行：[序号, 学校（含"领军龙"标记）, "男足22"]
                m_ft = re.match(r'^(男足|女足)(\d+)$', cells[2].strip()) if len(cells) >= 3 else None
                if m_ft and len(cells) == 3:
                    school = normalize_school(cells[1])
                    cur = {'school': school, 'sports': [], 'arts': [],
                           'sports_total': None, 'arts_total': None,
                           'football_special': True, '_cat': '体育'}
                    schools.append(cur)
                    cur['sports_total'] = int(m_ft.group(2))
                    cur['sports'].append({'project': m_ft.group(1), 'plan': int(m_ft.group(2)),
                                          'note': '领军龙足球试点单列'})
                    continue
                # 常规学校行：[序号, 学校, 类别, 小计, 项目?, 人数?]
                if len(cells) < 4:
                    raise ValueError(f'unknown school row: {cells}')
                if not re.fullmatch(r'\d+', cells[3].strip()):
                    continue  # 工作安排表等混入行（小计非数字）
                cur = {'school': cells[1], 'sports': [], 'arts': [],
                       'sports_total': None, 'arts_total': None, '_cat': cells[2].strip()}
                schools.append(cur)
                cat = cells[2].strip()
                total = plan_int(cells[3])
                if cat == '体育':
                    cur['sports_total'] = total
                elif cat == '艺术':
                    cur['arts_total'] = total
                else:
                    raise ValueError(f'unknown category {cat!r} at {cells}')
                if len(non_empty) >= 3 and len(cells) >= 6 and cells[4].strip():
                    _add_project(cur, cat, cells[4], cells[5])
                continue
            if len(cells) >= 3 and cells[2].strip() in ('体育', '艺术'):
                # 类别切换行：['', '', 类别, 小计, 项目, 人数]
                cat = cells[2].strip()
                cur['_cat'] = cat
                total = plan_int(cells[3])
                if cat == '体育':
                    cur['sports_total'] = total
                else:
                    cur['arts_total'] = total
                if len(non_empty) >= 3 and len(cells) >= 6 and cells[4].strip():
                    _add_project(cur, cat, cells[4], cells[5])
                continue
            # 项目续行：[项目, 人数]（合并单元格后其余为空）
            if len(non_empty) >= 2:
                if not re.match(r'^\d', non_empty[1].strip()):
                    continue  # 工作安排表等混入行（人数非数字）
                _add_project(cur, cur['_cat'], non_empty[0], non_empty[1])
    return schools


def _add_project(cur, cat, proj, num):
    d = {'project': proj.strip()}
    raw = num.strip()
    d['plan'] = plan_int(raw)
    m = re.search(r'其中[^）]*', raw)
    if m:
        d['note'] = m.group(0).strip()
    cur['sports' if cat == '体育' else 'arts'].append(d)


def main():
    schools = parse()
    # 校验小计 = 项目之和
    errors = []
    for s in schools:
        for cat, key in (('体育', 'sports'), ('艺术', 'arts')):
            total = s[f'{key}_total']
            if total is None:
                continue  # 该类别无计划（单类招生的学校正常）
            ssum = sum(p['plan'] for p in s[key])
            if total != ssum:
                errors.append(f"{s['school']} {cat}小计{total} != 项目之和{ssum} "
                              f"({[p['plan'] for p in s[key]]})")
    if errors:
        raise SystemExit('\n'.join(errors))
    out = {
        'source': 'gzzk-special-plan-2026',
        'doc': '广州市教育局关于印发2026年普通高中学校体育艺术类特长生招生计划的通知 附件1',
        'url': 'https://jyj.gz.gov.cn/yw/zsks/content/post_10755771.html',
        'school_count': len(schools),
        'schools': schools,
    }
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'OK: {len(schools)} 校 → {OUT}')


if __name__ == '__main__':
    main()
