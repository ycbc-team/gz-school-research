#!/usr/bin/env python3
"""
校名匹配工具：给定区 adcode 和校名（官方名单中的原始名），在 entities.json 中查找匹配实体。
用法: python3 scripts/registry/match_school.py <adcode> "<校名>" [--stage primary|middle|high]
输出: 匹配到的实体列表（school_id, name, stage, aliases, nature），无匹配则输出 NO_MATCH。

匹配规则（按优先级）：
1. 精确匹配 name 或 aliases（规范化后：去空白、去"广州市/广州/XX区"前缀、去"小学/初中/高中/学校/实验学校/九年一贯制"等后缀的影响通过包含匹配处理）
2. 规范化后包含匹配（官方名包含实体名或反之）
3. 核心词匹配（去除常见前后缀后的主体词）
"""
import json
import re
import sys
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENTITIES_PATH = os.path.join(REPO, 'data/registry/entities.json')

# 统一匹配库：norm 本体收敛至 school_match.normName（NFKC/繁简/去广州市/删括号/去空白）
sys.path.insert(0, os.path.join(REPO, 'scripts/registry'))
from school_match import normName as _normName

# 区 adcode -> 区名
ADCODE_DIST = {
    '440103': '荔湾区', '440104': '越秀区', '440105': '海珠区',
    '440106': '天河区', '440111': '白云区', '440112': '黄埔区',
    '440113': '番禺区',
}

def normalize(name):
    """规范化校名：统一 normName + 区名前缀剥离（检索辅助）。"""
    s = _normName(name)
    for d in ADCODE_DIST.values():
        s = re.sub(r'^' + d, '', s)
    return s

def core_name(name):
    """提取核心校名（去前后缀）。"""
    s = normalize(name)
    # 去括号内容
    s = re.sub(r'\(.*?\)', '', s)
    # 去常见后缀
    suffixes = ['九年一贯制学校', '九年一贯制', '十二年一贯制学校', '十二年一贯制',
                '完全中学', '高级中学', '实验学校', '实验小学', '实验中学',
                '外国语学校', '外语学校', '中英文学校', '双语学校',
                '小学', '初中', '中学', '高中', '学校']
    for suf in sorted(suffixes, key=len, reverse=True):
        if s.endswith(suf):
            s = s[:-len(suf)]
            break
    # 去常见前缀
    prefixes = ['广州市', '广州']
    for p in prefixes:
        if s.startswith(p):
            s = s[len(p):]
    return s.strip(' -_')

def load_entities():
    with open(ENTITIES_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['entities']

def match(adcode, school_name, stage=None):
    entities = load_entities()
    # 过滤区
    candidates = [e for e in entities if e['school_id'].startswith(f'gz-{adcode}-')]
    if stage:
        candidates = [e for e in candidates if e['stage'] == stage]

    norm_query = normalize(school_name)
    core_query = core_name(school_name)

    results = []
    for e in candidates:
        all_names = [e['name']] + e.get('aliases', [])
        norm_names = [normalize(n) for n in all_names]
        core_names = [core_name(n) for n in all_names]

        score = 0
        reason = ''
        # 1. 精确匹配
        if norm_query in norm_names:
            score = 100
            reason = 'exact'
        # 2. 核心词精确匹配
        elif core_query and core_query in core_names:
            score = 90
            reason = 'core_exact'
        # 3. 包含匹配
        elif any(norm_query and (norm_query in nn or nn in norm_query) for nn in norm_names if nn):
            score = 70
            reason = 'contains'
        # 4. 核心词包含匹配
        elif core_query and any(core_query and (core_query in cn or cn in core_query) for cn in core_names if cn):
            score = 50
            reason = 'core_contains'

        if score > 0:
            results.append({
                'score': score,
                'reason': reason,
                'school_id': e['school_id'],
                'name': e['name'],
                'stage': e['stage'],
                'aliases': e.get('aliases', []),
                'nature': e.get('nature', ''),
            })

    results.sort(key=lambda x: -x['score'])
    return results

def main():
    if len(sys.argv) < 3:
        print('用法: python3 match_school.py <adcode> "<校名>" [--stage primary|middle|high]')
        sys.exit(1)
    adcode = sys.argv[1]
    name = sys.argv[2]
    stage = None
    if '--stage' in sys.argv:
        idx = sys.argv.index('--stage')
        stage = sys.argv[idx + 1]

    results = match(adcode, name, stage)
    if not results:
        print('NO_MATCH')
    else:
        for r in results[:5]:
            print(f"[{r['score']}|{r['reason']}] {r['school_id']} | {r['stage']:8s} | {r['name']} | nature={r['nature'] or '公办(未标)'}")
            if r['aliases']:
                print(f"    aliases: {', '.join(r['aliases'][:5])}")

if __name__ == '__main__':
    main()
