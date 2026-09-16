#!/usr/bin/env python3
"""POI 匹配器回归用例（品牌关联漂移修复阶段 5）。

覆盖 2026-09 品牌关联全量测试发现的 94 处漂移修复中固化的关键案例：
- 同址异名/分校区回退（华阳/广大附中实验各校区/云雅初中部/金广实验）
- 泛词防吸附（广州实验中学、新塘三中远郊拦截、晓港湾不跨区）
- 宁可缺失不跨区错配（南悦/京溪主校无 POI → 缺失）
- 更名别名（九佛中学/九佛二中 2024 并入知识城中学 → 命中东/南校区）

用法：python3 scripts/test_match_poi.py
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import match_poi

POI_ALL = (
    match_poi.load_poi(os.path.join(ROOT, "data/primary/schools-gz.json"), "小学")
    + match_poi.load_poi(os.path.join(ROOT, "data/middle/schools-gz.json"), "初中")
    + match_poi.load_poi(os.path.join(ROOT, "data/high/schools-gz.json"), "高中")
)
ALIAS_MAP = match_poi.load_aliases(os.path.join(ROOT, "data/registry/entities.json"))

# (name, adcode, stage, expected_school_id 或 "缺失" 或 "远郊")
CASES = [
    ("金广实验学校", "440111", "小学", "gz-440111-f501b6b5"),
    ("广州市白云区广大附中实验中学（南校区）", "440111", "初中", "gz-440111-0078267c"),
    ("广州市白云区广大附中实验中学（星汇金沙校区）", "440111", "初中", "gz-440111-b95f2597"),
    ("云雅实验学校（初中部）", "440111", "初中", "gz-440111-6782d2c7"),
    ("华阳小学", "440106", "小学", "天河校区"),          # 主校无 POI，须回退到同区分校区
    ("海珠区晓港湾小学", "440105", "小学", "缺失"),        # 不得跨区落到黄埔港湾小学
    ("广州市荔湾区蒋光鼐纪念小学三元坊学校", "440103", "小学", "gz-440103-a5b0f405"),
    ("广州市荔湾区西关实验小学海北学校", "440103", "小学", "gz-440103-7a85adc9"),
    ("广州市增城区新塘镇第三中学", "440118", "初中", "远郊"),  # 远郊拦截，不得吸附广州三中
    ("广州实验中学", "440112", "初中", "gz-440112-87f27cf4"),  # 不得误匹配白云广大附中实验
    ("广州市白云区广州空港实验中学（本部）", "440111", "初中", "gz-440111-d4c4285e"),
    ("广州市白云区京溪小学", "440111", "小学", "缺失"),        # 主校无 POI、4 分校区不收敛 → 匹配器层宁可缺失（多校区由锚点表在 merge 层展开）
    ("九佛中学", "440112", "初中", "gz-440112-badbc2ab"),   # 2024 并入知识城中学=东校区（南方+ 官方查证）
    ("九佛第二中学", "440112", "初中", "gz-440112-ec15555e"), # 2024 并入知识城中学=南校区（南方+ 官方查证）
    ("南悦中学", "440111", "初中", "缺失"),                 # 不得命中同名充电站/停车场
]

def main():
    failures = []
    for name, adcode, stage, expect in CASES:
        r = match_poi.match_school(name, POI_ALL, ALIAS_MAP, preferred_adcode=adcode, preferred_stage=stage)
        got = r.get("school_id") or r.get("poi_match", "")
        if expect == "缺失":
            ok = r.get("poi_match") == "7区内真实缺失"
        elif expect == "远郊":
            ok = r.get("poi_match") == "远郊不在POI范围"
        elif expect == "天河校区":
            ok = bool(r.get("school_id", "").startswith("gz-440106"))
        else:
            ok = got == expect
        if not ok:
            failures.append(f"{name} -> {got}（应为 {expect}）")
    print(f"匹配器回归: {len(CASES)} 用例, {len(failures)} 失败")
    if failures:
        for f in failures:
            print(f"  ✗ {f}")
        sys.exit(1)
    print("  ✓ 全部通过")

if __name__ == "__main__":
    main()
