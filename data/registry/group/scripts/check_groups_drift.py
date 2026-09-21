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

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
PRODUCT = os.path.join(ROOT, "data/registry/group/dist/education_groups.json")
MID_OUT = os.path.join(ROOT, "data/primary/enrollments")
_MID_GLOB = "middle_enrollment_2026_*.json"

# 各子检查通过时的一行概要：全部通过时只打印一行结论；任一失败时才逐项输出。
_ok_lines = []


def _flush_ok():
    """失败时把已通过的子检查概要行先打出来，便于定位失败发生在哪一项。"""
    if _ok_lines:
        print("\n".join(_ok_lines))
        _ok_lines.clear()


def _replay(script, *args):
    r = subprocess.run(["python3", os.path.join(ROOT, script), *args],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        _flush_ok()
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
        _flush_ok()
        print("产物一致性: ✗ middle_enrollment 重跑产物与入库不一致（说明产物被手改或脚本输出有变）：")
        for x in diffs:
            print(f"    DIFF {x}")
        print("  → 手改产物会被重跑覆盖（铁律：只改生产脚本），请固化修正到脚本后重跑并提交产物。")
        sys.exit(1)
    _ok_lines.append(f"产物一致性: ✓ build_middle_enrollment 重跑产物与入库完全一致（{len(glob.glob(os.path.join(MID_OUT, _MID_GLOB)))} 区）")


def _check_special_matrix():
    """特长生/自招矩阵业务快照测试（2026-09-21 用户拍板：替代字节全等"重跑 vs 入库"）。

    字节全等"重跑 vs 入库"在入库被 bug 污染时自我一致通过（白云艺术中学 matchNorm 化
    后变 null 即现场证据）；快照测试对比"重跑产物的业务信息"与独立基线
    （data/linkage/special_matrix_snapshot.json，含名单→实体 / 计划数 / 项目清单），
    业务信息变化显式暴露，须 --update-snapshot 显式更新基线（数据变更=正常迭代）。"""
    r = subprocess.run(["python3", os.path.join(ROOT, "scripts/linkage/check_special_matrix_snapshot.py")],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        _flush_ok()
        print(r.stdout[-2500:])
        print(r.stderr[-1500:])
        sys.exit(1)
    _ok_lines.append("业务快照: ✓ special_matrix 业务信息与基线全等（名单→实体/计划数/项目，独立基线）")


def _check_minban_official():
    """校验民办官方源（番禺 2026 民办招生计划）重算与权威表一致——禁手改防线。"""
    r = subprocess.run(["python3", os.path.join(ROOT, "data/registry/private/scripts/build_minban_official.py"), "--check"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        _flush_ok()
        print("民办官方源校验: ✗ " + (r.stdout[-1500:] or r.stderr[-1500:]).strip().replace("\n", "\n  "))
        sys.exit(1)
    _ok_lines.append("民办官方源校验: ✓ 番禺官方招生计划解析与权威表一致（禁手改）")


def _check_build_scores():
    """录取分数线业务快照测试（2026-09-21 由 special_matrix 快照模式推广）。

    替代字节全等"重跑 vs 入库"（入库被 bug 污染时自我一致通过）；对比重跑产物的
    [学校: 分数线/批次] 业务快照与独立基线（data/high/cutoff_score/dist/scores_snapshot.json），
    分数/批次变化显式暴露，须 --update-snapshot 显式更新基线（数据变更=正常迭代）。"""
    r = subprocess.run(["python3", os.path.join(ROOT, "data/high/cutoff_score/scripts/check_scores_snapshot.py")],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        _flush_ok()
        print(r.stdout[-2500:])
        print(r.stderr[-1500:])
        sys.exit(1)
    _ok_lines.append("业务快照: ✓ 录取分数线与基线全等（2025/2026 校×批次，独立基线）")


def _check_build_high_levels():
    """重跑 build_high_levels_js.py（python）到临时目录，与入库 high 表比对。

    高中学段判定链（2026-09-18 起实体表 stage 驱动）：level/src/levels.json / MIDDLE_ONLY_CAMPUSES /
    实体表 stage 任一源改动必须重跑本脚本；重跑漂移说明 high 表被手改或脚本输出有变。
    """
    tmp = os.path.join(tempfile.gettempdir(), "high_levels_repro")
    shutil.rmtree(tmp, ignore_errors=True)
    r = subprocess.run(["python3", os.path.join(ROOT, "data/poi/scripts/build_high_levels_js.py"), "--out-dir", tmp],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        _flush_ok()
        print("生产脚本重跑失败：data/poi/scripts/build_high_levels_js.py")
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        sys.exit(1)
    with open(os.path.join(ROOT, "data/poi/dist/high_poi.json")) as a, open(os.path.join(tmp, "high_poi.json")) as b:
        da, db = json.load(a), json.load(b)
        # school_id 由下一环 build_entities 回写（其自带一致性校验），清洗层只比其余字段
        strip = lambda d: {**d, "schools": [{k: v for k, v in s.items() if k != "school_id"} for s in d["schools"]]}
        if strip(da) != strip(db):
            _flush_ok()
            print("产物一致性: ✗ build_high_levels 重跑产物与入库不一致（说明 high 表被手改或脚本输出有变）：")
            print("  → 只改生产脚本/源表（level/src/levels.json / MIDDLE_ONLY_CAMPUSES / 实体表 stage），重跑并提交产物。")
            sys.exit(1)
    _ok_lines.append("产物一致性: ✓ build_high_levels 重跑产物与入库完全一致")


def _check_build_entities():
    """实体/POI 关联业务快照测试（2026-09-21 由 special_matrix 快照模式推广）。

    替代字节全等"重跑 vs 入库"（入库被 bug 污染时自我一致通过）；对比重跑产物的
    实体核心信息（school_id → name/stage/aliases + 3 表 POI school_id 关联）与独立基线
    （data/registry/entity/dist/entities_snapshot.json），实体/别名/关联变化显式暴露，
    须 --update-snapshot 显式更新基线（数据变更=正常迭代；坐标等噪音不入快照）。
    民办名单（minban_schools.json）与实体表/POI 的联动仍受本检查约束。"""
    r = subprocess.run(["python3", os.path.join(ROOT, "data/registry/entity/scripts/check_entities_snapshot.py")],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        _flush_ok()
        print(r.stdout[-2500:])
        print(r.stderr[-1500:])
        sys.exit(1)
    _ok_lines.append("业务快照: ✓ 实体/POI 关联与基线全等（1554 实体 + 3 表 POI，独立基线）")


def _head(path):
    """工作树文件 vs git HEAD 内容（产物=入库基线）。"""
    rel = os.path.relpath(path, ROOT)
    r = subprocess.run(["git", "-C", ROOT, "show", f"HEAD:{rel}"], capture_output=True, text=True)
    return r.stdout


def _check_xiaoshengchu():
    """重跑 xiaoshengchu 生产链路（build_xiaoshengchu_all + upgrade）到工作树，与入库比对。

    名字→school_id 匹配已下沉 Python 数据层（xs_resolver.py，build_xiaoshengchu_all 的
    merge_all 调用）；upgrade 只做去重/分组组装，不再做名字匹配。覆盖
    build_xiaoshengchu_all.py / xs_resolver.py / upgrade_xiaoshengchu.mjs 的改动感知：
    改脚本后未重跑提交产物，或产物被手改，都会被检出。比对失败还原工作树（保留重跑前状态）。"""
    files = [os.path.join(ROOT, "data/primary/transition/dist/xiaoshengchu_2026.json")]
    orig = {f: open(f, encoding="utf-8").read() for f in files}
    try:
        r = subprocess.run(["python3", os.path.join(ROOT, "data/primary/transition/scripts/build_xiaoshengchu_all.py"), "all_done"],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            _flush_ok()
            print("生产脚本重跑失败：data/primary/transition/scripts/build_xiaoshengchu_all.py all_done")
            print(r.stderr[-2000:])
            for f, c in orig.items():
                open(f, "w", encoding="utf-8").write(c)
            sys.exit(1)
        r = subprocess.run(["node", os.path.join(ROOT, "data/primary/transition/scripts/upgrade_xiaoshengchu.mjs")],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            _flush_ok()
            print("生产脚本重跑失败：data/primary/transition/scripts/upgrade_xiaoshengchu.mjs")
            print(r.stderr[-2000:])
            for f, c in orig.items():
                open(f, "w", encoding="utf-8").write(c)
            sys.exit(1)
        failed = [f for f in files if open(f, encoding="utf-8").read() != _head(f)]
        if failed:
            _flush_ok()
            for f, c in orig.items():
                open(f, "w", encoding="utf-8").write(c)
            print(f"产物一致性: ✗ xiaoshengchu 重跑产物与入库不一致：{', '.join(os.path.basename(f) for f in failed)}")
            print("  → 说明 build_xiaoshengchu_all / xs_resolver / upgrade 改动后未重跑提交产物，或产物被手改。"
                  "修复须固化到生产脚本后重跑并提交产物。")
            sys.exit(1)
        _ok_lines.append("产物一致性: ✓ build_xiaoshengchu_all + upgrade 重跑产物与入库完全一致")
    except SystemExit:
        raise
    except Exception:
        for f, c in orig.items():
            open(f, "w", encoding="utf-8").write(c)
        raise


def _check_school_groups():
    """重跑 build_school_groups.py（公共 school_id→集团映射，纯 id 产物）到工作树，与入库比对。

    覆盖 build_school_groups.py 的改动感知：改脚本/education 外键/entities 反查源后未重跑提交产物，
    或产物被手改都会被检出。brand_groups.json 的 --write-brand 写回是一次性数据层补全
    （依赖 entities 反查，幂等累积），不在本复现范围；比对失败还原工作树。"""
    files = [os.path.join(ROOT, "data/registry/group/dist/school_groups.json")]
    orig = {f: open(f, encoding="utf-8").read() for f in files}
    try:
        r = subprocess.run(["python3", os.path.join(ROOT, "data/registry/group/scripts/build_school_groups.py")],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            _flush_ok()
            print("生产脚本重跑失败：data/registry/group/scripts/build_school_groups.py")
            print(r.stderr[-2000:])
            for f, c in orig.items():
                open(f, "w", encoding="utf-8").write(c)
            sys.exit(1)
        failed = [f for f in files if open(f, encoding="utf-8").read() != orig[f]]
        if failed:
            _flush_ok()
            for f, c in orig.items():
                open(f, "w", encoding="utf-8").write(c)
            print(f"产物一致性: ✗ build_school_groups 重跑产物与工作树不一致：{', '.join(os.path.basename(f) for f in failed)}")
            print("  → 说明 build_school_groups.py/education 外键/entities 反查源改动后未重跑提交产物。"
                  "修复须固化到生产脚本后重跑并提交产物。")
            sys.exit(1)
        _ok_lines.append("产物一致性: ✓ build_school_groups 重跑产物与入库完全一致（school_groups.json）")
    except SystemExit:
        raise
    except Exception:
        for f, c in orig.items():
            open(f, "w", encoding="utf-8").write(c)
        raise


def _check_backfill_ids():
    """重跑 backfill_school_ids.py（quota_matrix/district_quota/batch2_scores/special_matrix
    外键回填 + _school_id_unmatched 未命中清单）到工作树，与入库比对。

    覆盖 backfill_school_ids.py 的改动感知：改脚本后未重跑提交产物，或产物被手改
    （如 _school_id_unmatched 被手工增删）都会被检出。比对失败还原工作树。"""
    names = ["quota_matrix.json", "special_matrix.json", "batch2_scores.json",
             "district_quota.json", "_school_id_unmatched.json"]
    files = [os.path.join(ROOT, "data/linkage", n) for n in names]
    orig = {f: open(f, encoding="utf-8").read() for f in files}
    try:
        r = subprocess.run(["python3", os.path.join(ROOT, "scripts/linkage/backfill_school_ids.py")],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            _flush_ok()
            print("生产脚本重跑失败：scripts/linkage/backfill_school_ids.py")
            print(r.stderr[-2000:])
            for f, c in orig.items():
                open(f, "w", encoding="utf-8").write(c)
            sys.exit(1)
        failed = [f for f in files if open(f, encoding="utf-8").read() != _head(f)]
        if failed:
            _flush_ok()
            for f, c in orig.items():
                open(f, "w", encoding="utf-8").write(c)
            print(f"产物一致性: ✗ backfill_school_ids 重跑产物与入库不一致：{', '.join(os.path.basename(f) for f in failed)}")
            print("  → 说明 backfill_school_ids.py 改动后未重跑提交产物，或产物被手改。"
                  "修复须固化到生产脚本后重跑并提交产物。")
            sys.exit(1)
        _ok_lines.append("产物一致性: ✓ backfill_school_ids 重跑产物与入库完全一致（quota/district_quota/batch2/special/_unmatched）")
    except SystemExit:
        raise
    except Exception:
        for f, c in orig.items():
            open(f, "w", encoding="utf-8").write(c)
        raise


def _check_government_groups():
    """政府文件底表覆盖校验：已支持区必须与官方名单成员级对齐（缺失=0）。

    底表快照在 data/registry/group/raw/government/，解析器 scripts/registry/parse_government_groups.py。
    原则（用户口径）：以政府文件为底表，脚本解析形成数据源；官方名单有而 partial 无 = 缺失须补。"""
    script = os.path.join(ROOT, "data/registry/group/scripts/parse_government_groups.py")
    import re as _re
    src = open(script, encoding="utf-8").read()
    m = _re.search(r'SOURCES = \{(.*?)\n\}', src, _re.S)
    districts = [d for d in _re.findall(r'"([a-z]+)": \{', m.group(1)) if d != "brand_aliases"]
    ok = True
    for d in districts:
        r = subprocess.run(["python3", script, d, "--exit-on-gap"],
                           capture_output=True, text=True, cwd=ROOT)
        tail = (r.stdout or "") + (r.stderr or "")
        if r.returncode != 0:
            ok = False
            _flush_ok()
            print(f"官方底表: ✗ {d} 有缺失成员")
            print("\n".join(tail.splitlines()[-6:]))
        else:
            _ok_lines.append(f"官方底表: ✓ {d} 与官方名单成员级对齐")
    if not ok:
        _flush_ok()
        sys.exit(1)


def main():
    # 1) education_groups
    tmp = os.path.join(tempfile.gettempdir(), "education_groups_repro.json")
    _replay("data/registry/group/scripts/merge_groups.py", tmp)
    with open(tmp) as f:
        repro = json.load(f)
    with open(PRODUCT) as f:
        prod = json.load(f)

    if repro == prod:
        _ok_lines.append(f"产物一致性: ✓ 重跑产物与入库产物完全一致（{prod.get('stats', {}).get('total_members', '?')} 成员）")
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
        print("  → 请在改源后重跑 `python3 data/registry/group/scripts/merge_groups.py` 并提交产物；"
              "如需确认差异为有意修正，请将修正固化到源（partial/brand_groups/entities）后重跑。")
        sys.exit(1)

    # 2) middle_enrollment（本次新增：机制判定/回填手改都会被重跑覆盖检出）
    _check_middle_enrollment()

    # 3) special plan + matrix（2026 特长生计划解析 + 升学通道矩阵）
    _check_special_matrix()
    _check_build_high_levels()
    _check_build_scores()
    _check_build_entities()
    _check_minban_official()

    # 4) xiaoshengchu 全链路（匹配已下沉 Python 数据层 xs_resolver；upgrade 只组装）
    _check_xiaoshengchu()

    # 5) backfill_school_ids（quota_matrix/district_quota/batch2_scores/special_matrix/_unmatched）
    _check_backfill_ids()

    # 6) school_groups 公共集团映射（build_school_groups 纯 id 产物）
    _check_school_groups()

    # 7) 政府文件底表覆盖（有官方底表的区必须成员级对齐）
    _check_government_groups()

    # 全部通过：只输出一行结论（各子检查概要仅在失败时逐项打印）
    print("✓ 产物漂移一致性通过")


if __name__ == "__main__":
    main()
