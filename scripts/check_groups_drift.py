#!/usr/bin/env python3
"""产物漂移一致性校验（流程闭环核心，用户拍板"测试先跑生产脚本"）。

重跑本地生产脚本到临时文件，与入库产物对比（只跑本地数据处理，无高德等联网 API）：
- merge_groups.py → education_groups.json
- build_middle_enrollment.py --out-dir → middle_enrollment_2026_*.json（7 区）

- 完全一致 → 通过（产物=脚本输出，说明源改动已同步）
- 有差异 → 失败并列出差异（提醒"改了源忘了重跑产物"，或手改产物/脚本 bug 被覆盖回退）

用法：python3 scripts/check_groups_drift.py
"""
import json, os, subprocess, sys, tempfile, glob, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCT = os.path.join(ROOT, "data/registry/education_groups.json")
MID_OUT = os.path.join(ROOT, "data/primary/enrollments")
_MID_GLOB = "middle_enrollment_2026_*.json"


def _replay(script, *args):
    r = subprocess.run(["python3", os.path.join(ROOT, script), *args],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        print(f"生产脚本重跑失败：{script}")
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        sys.exit(1)


def _check_middle_enrollment():
    """重跑 build_middle_enrollment.py 到临时目录，与入库 7 区文件比对（防手改/机制回退）。"""
    tmp = os.path.join(tempfile.gettempdir(), "mid_enroll_repro")
    os.makedirs(tmp, exist_ok=True)
    for f in glob.glob(os.path.join(tmp, _MID_GLOB)):
        os.remove(f)
    _replay("scripts/primary/build_middle_enrollment.py", "--out-dir", tmp)
    diffs = []
    for f in sorted(glob.glob(os.path.join(MID_OUT, _MID_GLOB))):
        base = os.path.basename(f)
        with open(f) as a, open(os.path.join(tmp, base)) as b:
            if json.load(a) != json.load(b):
                diffs.append(base)
    if diffs:
        print("产物一致性: ✗ middle_enrollment 重跑产物与入库不一致（说明产物被手改或脚本输出有变）：")
        for x in diffs:
            print(f"    DIFF {x}")
        print("  → 手改产物会被重跑覆盖（铁律：只改生产脚本），请固化修正到脚本后重跑并提交产物。")
        sys.exit(1)
    print(f"产物一致性: ✓ build_middle_enrollment 重跑产物与入库完全一致（{len(glob.glob(os.path.join(MID_OUT, _MID_GLOB)))} 区）")


def _check_special_matrix():
    """重跑 build_special_plan + build_special_matrix 到临时文件，与入库比对（防解析漂移/手改产物）。"""
    tmp = tempfile.gettempdir()
    plan_tmp = os.path.join(tmp, "plan_special_repro.json")
    matrix_tmp = os.path.join(tmp, "special_matrix_repro.json")
    _replay("scripts/linkage/build_special_plan.py", plan_tmp)
    # previous 用入库产物：backfill 生成的初中外键只存在于入库，重跑到新文件会丢失
    _replay("scripts/linkage/build_special_matrix.py", matrix_tmp, os.path.join(ROOT, "data/linkage/special_matrix.json"))
    pairs = [
        (os.path.join(ROOT, "data/linkage/raw/special/plan_special_2026.json"), plan_tmp, "plan_special_2026"),
        (os.path.join(ROOT, "data/linkage/special_matrix.json"), matrix_tmp, "special_matrix"),
    ]
    failed = []
    for prod, repro, label in pairs:
        with open(prod) as a, open(repro) as b:
            if json.load(a) != json.load(b):
                failed.append(label)
    if failed:
        print(f"产物一致性: ✗ 重跑产物与入库不一致：{', '.join(failed)}（解析/映射漂移或手改产物）")
        print("  → 修复须固化到生产脚本后重跑并提交产物，禁止手改产物。")
        sys.exit(1)
    print("产物一致性: ✓ build_special_plan + build_special_matrix 重跑产物与入库完全一致")


def _check_minban_official():
    """校验民办官方源（番禺 2026 民办招生计划）重算与权威表一致——禁手改防线。"""
    r = subprocess.run(["python3", os.path.join(ROOT, "scripts/registry/build_minban_official.py"), "--check"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        print("民办官方源校验: ✗ " + (r.stdout[-1500:] or r.stderr[-1500:]).strip().replace("\n", "\n  "))
        sys.exit(1)
    print("民办官方源校验: ✓ 番禺官方招生计划解析与权威表一致（禁手改）")


def _check_build_entities():
    """重跑 build_entities.mjs（node）到临时目录，与入库 entities + 3 个 POI 表比对。

    民办名单（minban_schools.json）与实体表/POI 的联动：源表改动必须重跑 build_entities，
    禁止手改 entities.json；重跑漂移说明实体表被手改或民办名单表未重跑。
    """
    tmp = os.path.join(tempfile.gettempdir(), "entities_repro")
    shutil.rmtree(tmp, ignore_errors=True)
    r = subprocess.run(["node", os.path.join(ROOT, "scripts/registry/build_entities.mjs"), "--out-dir", tmp],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        print("生产脚本重跑失败：scripts/registry/build_entities.mjs")
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        sys.exit(1)
    pairs = [
        ("data/registry/entities.json", "entities"),
        ("data/primary/schools-gz.json", "primary POI"),
        ("data/middle/schools-gz.json", "middle POI"),
        ("data/high/schools-gz.json", "high POI"),
    ]
    failed = []
    for prod_rel, label in pairs:
        with open(os.path.join(ROOT, prod_rel)) as a, open(os.path.join(tmp, prod_rel)) as b:
            if json.load(a) != json.load(b):
                failed.append(label)
    if failed:
        print("产物一致性: ✗ build_entities 重跑产物与入库不一致：" + ", ".join(failed))
        print("  → 实体表/POI 被手改，或 minban_schools.json 等源表改动后未重跑 build_entities。修复须固化到生产脚本/源表后重跑并提交产物。")
        sys.exit(1)
    print("产物一致性: ✓ build_entities 重跑产物与入库完全一致（entities + 3 POI 表）")


def main():
    # 1) education_groups
    tmp = os.path.join(tempfile.gettempdir(), "education_groups_repro.json")
    _replay("scripts/merge_groups.py", tmp)
    with open(tmp) as f:
        repro = json.load(f)
    with open(PRODUCT) as f:
        prod = json.load(f)

    if repro == prod:
        print(f"产物一致性: ✓ 重跑产物与入库产物完全一致（{prod.get('stats', {}).get('total_members', '?')} 成员）")
    else:
        # 差异分类
        rb = {g["brand"]: g for g in repro.get("groups", [])}
        pb = {g["brand"]: g for g in prod.get("groups", [])}
        lost, wrong, gained = [], [], []
        for brand, g in rb.items():
            if brand not in pb:
                gained.append(f"[新增集团] {brand}")
                continue
            pm = {m["name"]: m for m in pb[brand].get("members", [])}
            for m in g.get("members", []):
                if m["name"] not in pm:
                    gained.append(f"{brand} | {m['name']} (school_id={m.get('school_id','')})")
                    continue
                bs = (pm[m["name"]].get("school_id") or "")
                as_ = (m.get("school_id") or "")
                if bs and not as_:
                    lost.append(f"{brand} | {m['name']} | {bs} → (缺失)")
                elif bs and as_ and bs != as_:
                    wrong.append(f"{brand} | {m['name']} | {bs} → {as_}")
                elif not bs and as_:
                    gained.append(f"{brand} | {m['name']} | (新增) {as_}")
        print(f"产物一致性: ✗ 重跑产物与入库产物不一致")
        print(f"  丢失 {len(lost)} / 错配 {len(wrong)} / 新增 {len(gained)}")
        for x in lost[:30]:
            print(f"    LOST {x}")
        for x in wrong[:30]:
            print(f"    WRONG {x}")
        for x in gained[:30]:
            print(f"    GAINED {x}")
        print("  → 请在改源后重跑 `python3 scripts/merge_groups.py` 并提交产物；"
              "如需确认差异为有意修正，请将修正固化到源（partial/brand_groups/entities）后重跑。")
        sys.exit(1)

    # 2) middle_enrollment（本次新增：机制判定/回填手改都会被重跑覆盖检出）
    _check_middle_enrollment()

    # 3) special plan + matrix（2026 特长生计划解析 + 升学通道矩阵）
    _check_special_matrix()
    _check_build_entities()
    _check_minban_official()


if __name__ == "__main__":
    main()
