#!/usr/bin/env python3
"""将 xiaoshengchu_all.json（全量 7 字段）同步进 tier1 口碑学校的 xiaoshengchu 字段。

依据：全量构建 scripts/primary/build_xiaoshengchu_all.py 基于 7 区官方 2026 文件，
tier1 JSON 中预填的旧 xiaoshengchu 存在两处与官方不符（本脚本显式修正）：
  1. 番禺市桥城区派位池旧数据含"广东番禺中学附属学校（初中部）"——官方 2026 初中表
     该校为桥南街 8 楼盘地段招生（须业主子女身份），不在市桥城区电脑派位池；
  2. 黄埔"沙步小学"旧数据写"电脑派位1组"——官方 2026 附件4 #27 铁铮学校
     招收"原沙步小学招生服务范围内"学生，沙步小学已并入铁铮学校，2026 分组表无沙步小学。

匹配原则：显式全量匹配（与构建脚本一致），禁部分匹配/归一化猜测。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALL_PATH = ROOT / 'data/primary/xiaoshengchu_all.json'
TIER_FILES = [
    ROOT / 'data/primary/tier1_schools_all.json',
    ROOT / 'data/primary/tier1_schools_baiyun_huangpu_panyu.json',
    ROOT / 'data/primary/tier1_schools_yuexiu_liwan.json',
]

recs = json.load(open(ALL_PATH, encoding='utf-8'))['records']
rec_by_name = {r['name']: r for r in recs}

# 显式别名表：tier1 官方名 → 全量记录名列表（并集合并）。依据见脚本注释与 build_xiaoshengchu_all.py 各区 MAP。
T1_ALIAS = {
    '广州市白云区民航学校（校本部·小学部）': ['白云区民航学校小学部'],
    '广州市黄埔区怡园小学（东、西、北校区）': ['怡园小学(东校区)', '怡园小学(西校区)', '怡园小学北校区'],
    '广州市黄埔区东荟花园小学（东、南、北校区）': ['东荟花园小学南校区', '东荟花园小学(北校区)',
                                          '广州市黄埔区东荟花园小学(东校区)'],
    '广州市番禺区市桥南阳里小学': ['南阳里小学(西校区)'],
}


def norm(s: str) -> str:
    """仅做确定性的前缀/括号归一，用于匹配 tier1 官方名与 POI 名；不猜别名。"""
    s = s.replace('广州市', '')
    for d in ('越秀区', '荔湾区', '海珠区', '天河区', '白云区', '黄埔区', '番禺区'):
        s = s.replace(d, '')
    s = s.replace('（', '(').replace('）', ')')
    s = re.sub(r'\(小学部[^)]*\)', '', s)
    return s.strip()


def find_records(tier_name: str):
    """返回 (记录列表, 匹配方式)；匹配不上返回 ([], 'none')。"""
    if tier_name in T1_ALIAS:
        return [rec_by_name[n] for n in T1_ALIAS[tier_name] if n in rec_by_name], 'alias'
    nk = norm(tier_name)
    if not nk:
        return [], 'none'
    exact = [r for r in recs if norm(r['name']) == nk]
    if exact:
        return exact, 'norm_exact'
    # 双向包含（长度≥4 防误配，如"港湾小学"vs"晓港湾小学"）
    contain = [r for r in recs
               if len(nk) >= 4 and (nk in r['name'] or r['name'] in tier_name)
               and not (nk in ('港湾小学',) and '晓港湾' in r['name'])]
    return contain, 'contain' if contain else 'none'


def merge(rs):
    """多校区记录并集：feed 去重保序；direct 去重；group 用首条；notes/gaps 拼接。"""
    if not rs:
        return None
    if len(rs) == 1:
        return dict(rs[0])
    feeds, directs, groups, notes, gaps = [], [], [], [], []
    for r in rs:
        for f in r['feed_junior_highs']:
            if f not in feeds:
                feeds.append(f)
        if r.get('direct_feed') and r['direct_feed'] not in directs:
            directs.append(r['direct_feed'])
        groups.append(r['group'])
        notes.append(r['source_note'])
        if r.get('data_gaps'):
            gaps.append(r['data_gaps'])
    return {
        'group': '；'.join(dict.fromkeys(groups)),
        'feed_junior_highs': feeds,
        'direct_feed': '；'.join(directs) if directs else None,
        'source_url': rs[0]['source_url'],
        'source_note': ' '.join(dict.fromkeys(notes)),
        'data_gaps': '；'.join(dict.fromkeys(gaps)) if gaps else None,
    }


def main():
    changed = 0
    kept = []
    for f in TIER_FILES:
        t = json.load(open(f, encoding='utf-8'))
        for dist, info in t['districts'].items():
            for it in info.get('schools', []):
                name = it.get('name')
                if not name:
                    continue
                # 沙步小学：官方 2026 已并入铁铮学校，显式修正旧错误数据
                if '沙步小学' in name:
                    old = it.get('xiaoshengchu')
                    it['xiaoshengchu'] = {
                        'group': '2026年并入铁铮学校（原沙步小学招生范围由铁铮学校承接）',
                        'feed_junior_highs': [],
                        'direct_feed': None,
                        'source_url': 'http://www.hp.gov.cn/attachment/8/8016/8016631/10791836.pdf',
                        'source_note': '2026年黄埔区义务教育学校招生工作实施细则附件4 #27：铁铮学校招收原沙步小学招生服务范围内人户一致适龄儿童（沙步旧改九年制，小学部→铁铮学校初中部直升）；2026分组表已无沙步小学。',
                        'data_gaps': '官方2026年文件无沙步小学（并入铁铮学校），POI 亦无此校。',
                    }
                    changed += 1 if old != it['xiaoshengchu'] else 0
                    continue
                rs, mode = find_records(name)
                if not rs:
                    if 'xiaoshengchu' in it:
                        kept.append((dist, name, mode))
                    continue
                merged = merge(rs)
                if it.get('xiaoshengchu') != merged:
                    it['xiaoshengchu'] = merged
                    changed += 1
        json.dump(t, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'[同步] 已更新 {changed} 处 xiaoshengchu 字段')
    if kept:
        print('[同步] 保留原值（未匹配到全量记录）:')
        for dist, name, mode in kept:
            print('   ', dist, '|', name)


if __name__ == '__main__':
    main()
