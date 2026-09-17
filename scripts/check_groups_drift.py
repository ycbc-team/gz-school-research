#!/usr/bin/env python3
"""产物漂移一致性校验（流程闭环核心，用户拍板"测试先跑生产脚本"）。

重跑本地生产脚本到临时文件，与入库产物对比（只跑本地数据处理，无高德等联网 API）：
- merge_groups.py → education_groups.json
- build_middle_enrollment.py --out-dir → middle_enrollment_2026_*.json（7 区）

- 完全一致 → 通过（产物=脚本输出，说明源改动已同步）
- 有差异 → 失败并列出差异（提醒"改了源忘了重跑产物"，或手改产物/脚本 bug 被覆盖回退）

用法：python3 scripts/check_groups_drift.py
"""
import json, os, subprocess, sys, tempfile, glob

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


if __name__ == "__main__":
    main()
