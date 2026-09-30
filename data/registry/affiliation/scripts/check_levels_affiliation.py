#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性验证脚本：levels.json 中省属/市属标记 vs affiliation 官方名单（市属 32 / 省属 64）。

核对四向：
  1) levels 标「省属」的高中 → 必须命中省属名单中的普通高中（广东实验中学/华南师范大学附属中学）
  2) levels 标「市属」的高中 → 必须命中市属 32 单位中的普通中学（10 所）
  3) 反向：省属名单普通高中 → levels 中必须有且标「省属」
  4) 反向：市属名单普通中学 → levels 中必须有且标「市属」

名称匹配统一走 school_match.normName（项目唯一真源），levels 侧取 name + aliases。
官方名单中的高职/教辅/中职/特殊学校不参与高中口径核对（levels 是普通高中清单）。

用法：python3 data/registry/affiliation/scripts/check_levels_affiliation.py
退出码：0=全部一致；1=存在差异（打印详细报告）。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
LEVELS = ROOT / "data/registry/affiliation/src/levels.json"
SHI = ROOT / "data/registry/affiliation/parsed/jyj_直属事业单位列表_2025-02-14.json"
SHENG = ROOT / "data/registry/affiliation/parsed/gdjy_2025年部门预算_下属单位.json"

sys.path.insert(0, str(ROOT / "data/registry/entity/scripts"))
from school_match import normName as norm  # noqa: E402

# 市属 32 单位中不属于「普通高中」的排除特征词（高职/教辅/中职/特殊/劳动技术）
_NON_HIGH_HINTS = (
    "职业技术学院", "职业学院", "师范高等专科学校", "招生考试", "教育研究",
    "评估", "电化教育", "基建", "卫生健康", "劳动技术", "启聪", "启明",
    "新穗", "启新", "职业学校", "师范学校", "事务中心", "基金会",
)


def is_high_school(name: str) -> bool:
    """官方名单单位 → 是否普通高中（含完全中学；艺术中学/协和学校/清华附中湾区学校算）。"""
    return not any(h in name for h in _NON_HIGH_HINTS)


def normset(names):
    return {norm(n) for n in names}


def main() -> int:
    levels = json.loads(LEVELS.read_text(encoding="utf-8"))
    shi = json.loads(SHI.read_text(encoding="utf-8"))
    sheng = json.loads(SHENG.read_text(encoding="utf-8"))

    # 官方普通高中名单（名称 + norm key）
    shi_high = [u["name"] for u in shi["units"] if is_high_school(u["name"])]
    shi_high_keys = normset(shi_high)
    sheng_high = [u["name"] for u in sheng["units"]
                  if u.get("category") == "省属中小学" and "小学" not in u["name"]]
    sheng_high_keys = normset(sheng_high)

    # levels 侧：affiliation → schools（含 aliases 可命中）
    lev_sheng, lev_shi = [], []
    for sc in levels["schools"]:
        aff = sc.get("affiliation", "")
        if aff == "省属":
            lev_sheng.append(sc)
        elif aff == "市属":
            lev_shi.append(sc)

    def hit(sc, keys):
        return norm(sc["name"]) in keys or any(norm(a) in keys for a in sc.get("aliases", []))

    issues = []

    # 1) levels 省属 → 官方省属高中
    for sc in lev_sheng:
        if not hit(sc, sheng_high_keys):
            issues.append(f"[levels标省属→官方无] {sc['name']}（aliases: {sc.get('aliases', [])}）")
    # 2) levels 市属 → 官方市属高中
    for sc in lev_shi:
        if not hit(sc, shi_high_keys):
            issues.append(f"[levels标市属→官方32单位无] {sc['name']}（aliases: {sc.get('aliases', [])}）")
    # 3) 官方省属高中 → levels
    for name in sheng_high:
        if not any(hit(sc, {norm(name)}) for sc in lev_sheng):
            issues.append(f"[官方省属→levels缺失/未标省属] {name}")
    # 4) 官方市属高中 → levels
    for name in shi_high:
        if not any(hit(sc, {norm(name)}) for sc in lev_shi):
            issues.append(f"[官方市属→levels缺失/未标市属] {name}")

    print(f"levels 总数: {len(levels['schools'])}；省属 {len(lev_sheng)} 所、市属 {len(lev_shi)} 所")
    print(f"官方省属普通高中: {sheng_high}")
    print(f"官方市属普通中学: {shi_high}")
    print(f"levels 省属: {[s['name'] for s in lev_sheng]}")
    print(f"levels 市属: {[s['name'] for s in lev_shi]}")
    print("-" * 60)
    if not issues:
        print("✓ 全部一致：levels 省市属标记与官方名单无出入")
        return 0
    print(f"发现 {len(issues)} 处差异：")
    for i in issues:
        print("  -", i)
    print("\n说明：差异为待人工核实的口径出入（如「广州大学附属中学」为市属但未列入 jyj 直属事业单位列表）。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
