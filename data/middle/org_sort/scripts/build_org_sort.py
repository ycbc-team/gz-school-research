#!/usr/bin/env python3
"""七区初中机构整理档位名单 → 整合产物（school_id 由 SchoolMatcher 统一匹配）。

真源：data/middle/org_sort/src/*.json —— 机构手工整理的纯名单（区名/档位/校名/区特点，无 school_id）。
产物：data/middle/org_sort/dist/compiled.json —— 轻量整合版：[{district, level, school_id}, ...]，
      不含 label/source/description/note 等展示字段，供前端默认排序直接消费。
规则（宁缺毋滥）：
  - 每个校名只允许收敛出一个 school_id（SchoolMatcher 同区/同学段收敛，多候选不猜配）；
  - 匹配不上的条目不写入产物，逐条输出到 STDOUT，由人工确认后补实体别名或放弃；
  - 不跨区错配：preferred_adcode 取名单所在区，跨区回退仅限 SchoolMatcher 显式放行。
本脚本不做业务别名（民间公认简称/校区叫法已下沉至 data/registry/entity/scripts/build_entities.py
的 OFFICIAL_MIDDLE_ALIAS 实体别名；此处仅保留通用变体：去括号/去"本部"修饰/数字序数化）。

运行：python3 data/middle/org_sort/scripts/build_org_sort.py
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))  # org_sort/scripts/ → 项目根
ORG_SORT_DIR = os.path.join(ROOT, "data", "middle", "org_sort", "src")
OUT = os.path.join(ROOT, "data", "middle", "org_sort", "dist", "compiled.json")

sys.path.insert(0, os.path.join(ROOT, "data", "registry", "entity", "scripts"))
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

# 注意：本项目不在业务脚本内置别名/锚定（曾用 ORG_SORT_ANCHORS，2026-09-18 起全部下沉到
# data/registry/entity/scripts/build_entities.py 的 OFFICIAL_MIDDLE_ALIAS 实体别名，供所有链路共用）。

# 显式宁缺：名单名对应校区在实体/榜单确认不存在，且通用变体（去括号等）会错配到其它校区。
# 这不是业务别名，而是排除错配（宁缺毋滥的一部分）。
EXPLICIT_DROP = set()   # 当前无显式宁缺（培英云城已下沉实体别名匹配云城校区实体 730c7404）

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
        poi_paths=[(os.path.join(ROOT, "data", "poi", "dist", "middle_poi.json"), "初中")],
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
                # 显式宁缺（错配排除）
                if name in EXPLICIT_DROP:
                    unmatched.append((district, lv["level"], name))
                    continue
                # SchoolMatcher 变体匹配（宁缺毋滥：多候选/缺失返回 None，不猜配）。
                # 民间简称/校区叫法（含“本部”、雁园/逸景、东圃更名等）已由实体表别名承载。
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
