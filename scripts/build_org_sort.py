#!/usr/bin/env python3
"""七区初中机构整理档位名单 → 整合产物（school_id 由 SchoolMatcher 统一匹配）。

真源：data/middle/org_sort/*.json —— 机构手工整理的纯名单（区名/档位/校名/区特点，无 school_id）。
产物：data/middle/org_sort_compiled.json —— 轻量整合版：[{district, level, school_id}, ...]，
      不含 label/source/description/note 等展示字段，供前端默认排序直接消费。
规则（宁缺毋滥）：
  - 每个校名只允许收敛出一个 school_id（SchoolMatcher 同区/同学段收敛，多候选不猜配）；
  - 匹配不上的条目不写入产物，逐条输出到 STDOUT，由人工确认后决定锚定或放弃；
  - 不跨区错配：preferred_adcode 取名单所在区，跨区回退仅限 SchoolMatcher 显式放行。

运行：python3 scripts/build_org_sort.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORG_SORT_DIR = os.path.join(ROOT, "data", "middle", "org_sort")
OUT = os.path.join(ROOT, "data", "middle", "org_sort_compiled.json")

sys.path.insert(0, os.path.join(ROOT, "scripts", "registry"))
from school_match import SchoolMatcher

# 七区 adcode（与 data/linkage 榜单 district 全名一致）
DISTRICT_ADCODE = {
    "天河区": "440106",
    "番禺区": "440113",
    "荔湾区": "440103",
    "越秀区": "440104",
    "海珠区": "440105",
    "白云区": "440111",
    "黄埔区": "440112",
}

# 历史人工确认锚定（参考 build_middle_enrollment.MIDDLE_ANCHORS 惯例）：名单简称不在实体表
# alias 中、SchoolMatcher 无法收敛，但对应关系唯一无歧义（已按榜单/实体表人工核对）。
# 涉及校区选择/多候选/数据缺失的条目不在此锚定，统一输出未匹配清单由用户确认。
ORG_SORT_ANCHORS = {
    # 天河
    "天河外国语": "gz-440106-069ddb41",          # 广州市天河外国语学校
    "华工附中": "gz-440106-9bed7efb",            # 华南理工大学附属实验学校
    "暨大附中": "gz-440106-11e15e8d",            # 暨南大学附属实验学校
    "113 中学五山本部": "gz-440106-2e9f6f7b",    # 广州市第一一三中学（五山本部；陶育实验学校为另一校）
    # 番禺
    "仲元初中部": "gz-440113-acf92324",          # 广东仲元中学（初中榜单记录）
    "华碧": "gz-440113-db326e94",                # 广州市番禺区华南碧桂园学校
    "番附（番禺中学附属）": "gz-440113-53650c78",  # 广东番禺中学附属学校（SchoolMatcher 曾错配到番禺中学实验学校 95be9ccc）
    # 荔湾
    "西关外国语本部": "gz-440103-b41a3512",      # 广州市西关外国语学校（实体：初中部）
    "省实荔湾（广钢）": "gz-440103-53cac770",    # 广东实验中学荔湾学校
    "西关广雅（东风西）": "gz-440103-693412ae",  # 西关广雅实验学校（东风西路校区）
    "广州市一中本部": "gz-440103-2653da64",      # 广州市第一中学（实体：姜中宏校区；姜中宏校区归属待用户确认）
    "丰宁": "gz-440104-3b870a8e",                # 广州市第四中学丰宁学校
    "真光金道": "gz-440103-f203d28d",            # 广州市真光中学金道学校
    "真光东漖": "gz-440103-2c188507",            # 广州市真光中学东漖学校
    # 越秀
    "执信本部": "gz-440104-f3ca07ff",            # 广州市执信中学（越秀校区）
    "二中本部": "gz-440104-7f3031fc",            # 广州市第二中学（越秀校区）
    "广大附中黄华路": "gz-440104-b22c4eca",      # 广州大学附属中学（越秀校区）
    "三中": "gz-440104-d9ec2dbb",                # 广州市第三中学
    "三中实验": "gz-440104-39515a9d",            # 广州市第三中学实验学校
    "广东华侨中学起义路": "gz-440104-1560332d",  # 广东华侨中学（越秀校区）
    "育才中学本部": "gz-440104-191aaa35",        # 广州市育才中学（东校区，榜单收录；SchoolMatcher 曾错配到育才实验学校 ff8d7e05）
    "十三中": "gz-440104-0a17f1eb",              # 榜单收录记录（实体名：第十三中学文德校区；SchoolMatcher 曾匹配到无榜单数据的禺山校区 9b88f912）
    # 海珠
    "南武初中本部": "gz-440105-eaf414df",        # 广州市南武中学
    "六中本部初中": "gz-440105-12b49e3f",        # 广州市第六中学（海珠校区）
    "中大附中": "gz-440105-e363a214",            # 中山大学附属中学
    "琶洲执信": "gz-440105-cac39935",            # 广州市执信中学琶洲实验学校
    "南武附属": "gz-440105-77baeea5",            # 广州市南武中学附属学校
    "海珠实验中学（海实）": "gz-440105-e76b659d",  # 海实=广州市海珠外国语实验中学（榜单收录；SchoolMatcher 曾错配到海珠实验中学东校区 badc0974 无榜单数据）
    "四十一中": "gz-440105-b210556b",            # 榜单收录记录（实体名：第四十一中学东校区；SchoolMatcher 曾匹配到无榜单数据的 40a80ebb）
    # 白云
    "65 中本部初中": "gz-440111-c8461d5d",       # 暂按明德校区（实体名含“初中部”）；是否指江府校区待确认
    "培英实验": "gz-440111-e14818fc",            # 广州市白云区培英实验学校（同和校区）
    "云雅实验": "gz-440111-6782d2c7",            # 广州市白云区云雅实验学校
    "广外附中": "gz-440111-7e484346",            # 暂按广东外语外贸大学实验中学；是否有其他指向待确认
    # 白云
    "培英中学（云城校区）": None,               # 显式宁缺：实体/榜单无“云城校区”（去括号变体曾错配到科技城校区 e128c24f）
    "白云中学": None,                            # 显式宁缺：榜单有汇侨/棠景两校区、无本部数据；用户未指定校区，待确认
    # 黄埔
    "八十六中（初中本部）": "gz-440112-06029745",  # 榜单记录为广州市第八十六中学（实体名：分校）；初中部实体 43108516 待确认
    "华附知识城初中": "gz-440112-3847727f",      # 华南师范大学附属中学（知识城校区）
    "广附黄埔实验": "gz-440112-705c66e3",       # 广大附中黄埔实验学校
    "知识城中学": "gz-440112-3f877ace",          # 广州知识城中学（北校区）
    "九佛中学": None,                            # 显式宁缺：实体与榜单均未收录（SchoolMatcher 曾错配到知识城东校区 badbc2ab）
}

# 中文数字（1-99；3 位编号如 113/123 按逐位读法“一一三/一二三”处理）
CN_NUM = {
    1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九",
    10: "十", 11: "十一", 12: "十二", 13: "十三", 14: "十四", 15: "十五", 16: "十六",
    17: "十七", 18: "十八", 19: "十九", 20: "二十", 21: "二十一", 22: "二十二",
    23: "二十三", 24: "二十四", 25: "二十五", 26: "二十六", 27: "二十七", 28: "二十八",
    29: "二十九", 30: "三十", 31: "三十一", 32: "三十二", 33: "三十三", 34: "三十四",
    35: "三十五", 36: "三十六", 37: "三十七", 38: "三十八", 39: "三十九", 40: "四十",
    41: "四十一", 42: "四十二", 43: "四十三", 44: "四十四", 45: "四十五", 46: "四十六",
    47: "四十七", 48: "四十八", 49: "四十九", 50: "五十", 51: "五十一", 52: "五十二",
    53: "五十三", 54: "五十四", 55: "五十五", 56: "五十六", 57: "五十七", 58: "五十八",
    59: "五十九", 60: "六十", 61: "六十一", 62: "六十二", 63: "六十三", 64: "六十四",
    65: "六十五", 66: "六十六", 67: "六十七", 68: "六十八", 69: "六十九", 70: "七十",
    71: "七十一", 72: "七十二", 73: "七十三", 74: "七十四", 75: "七十五", 76: "七十六",
    77: "七十七", 78: "七十八", 79: "七十九", 80: "八十", 81: "八十一", 82: "八十二",
    83: "八十三", 84: "八十四", 85: "八十五", 86: "八十六", 87: "八十七", 88: "八十八",
    89: "八十九", 90: "九十", 91: "九十一", 92: "九十二", 93: "九十三", 94: "九十四",
    95: "九十五", 96: "九十六", 97: "九十七", 98: "九十八", 99: "九十九",
}


def ordinalize(s: str) -> str:
    """学校编号数字序数化：“113 中学”→“第一一三中学”、“89 中”→“第八十九中学”。"""
    def repl(m):
        d = int(m.group())
        if d == 0:
            return m.group()
        if d >= 100:
            digits = "一二三四五六七八九"
            return "第" + "".join(digits[int(ch) - 1] for ch in m.group())
        return "第" + CN_NUM[d]
    return re.sub(r"\d+", repl, s)


def variants(name: str):
    """渐进放宽的匹配变体：原样 → 去括号 → 去“本部/初中部”修饰 → 数字序数化组合。"""
    vs = [name]
    bare = re.sub(r"[（(].*?[)）]", "", name).strip()
    if bare and bare != name:
        vs.append(bare)
    for base in list(vs):
        trimmed = re.sub(r"(本部|初中部|初中)$", "", base).strip()
        if trimmed and trimmed != base and len(trimmed) >= 4:
            vs.append(trimmed)
    for base in list(vs):
        orded = ordinalize(base)
        if orded != base:
            vs.append(orded)
    seen, out = set(), []
    for v in vs:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def main():
    matcher = SchoolMatcher.load(
        poi_paths=[(os.path.join(ROOT, "data", "middle", "schools-gz.json"), "初中")],
        entities_path=os.path.join(ROOT, "data", "registry", "entities.json"))

    compiled = []
    unmatched = []  # (district, level, name, reason)
    for fname in sorted(os.listdir(ORG_SORT_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(ORG_SORT_DIR, fname), encoding="utf-8") as f:
            doc = json.load(f)
        district = doc["district"]
        adcode = DISTRICT_ADCODE.get(district)
        for lv in doc["levels"]:
            for name in lv["schools"]:
                # 1) 历史人工确认锚定优先（重跑不漂移；None = 显式宁缺，进入未匹配清单）
                if name in ORG_SORT_ANCHORS:
                    aid = ORG_SORT_ANCHORS[name]
                    if aid:
                        compiled.append({"district": district, "level": lv["level"], "school_id": aid})
                    else:
                        unmatched.append((district, lv["level"], name))
                    continue
                # 2) SchoolMatcher 变体匹配（宁缺毋滥：多候选/缺失返回 None，不猜配）
                hit_id, hit_variant = None, None
                for v in variants(name):
                    r = matcher.resolve(v, preferred_adcode=adcode, preferred_stage="初中")
                    if r and r.get("school_id"):
                        hit_id, hit_variant = r["school_id"], v
                        break
                if hit_id:
                    compiled.append({"district": district, "level": lv["level"], "school_id": hit_id})
                else:
                    unmatched.append((district, lv["level"], name))

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(compiled, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"整合完成：{len(compiled)} 条匹配 → {OUT}")
    print(f"\n未匹配 {len(unmatched)} 条（未写入产物，需人工确认）：")
    for district, level, name in unmatched:
        print(f"  - {district} 第{level}档：{name}")


if __name__ == "__main__":
    main()
