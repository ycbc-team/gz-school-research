#!/usr/bin/env python3
"""初中招生产物快照对比（npm run check 链）。

重跑 build_middle_enrollment.py --out-dir 到临时目录（绝不碰 dist），提取结构化快照
（records 的 school → 字段 + mechanism 分布），与独立基线全等对比：

- 全等 → 通过：初中招生产物未发生意外变化
- 有差异 → 失败并逐条列出（旧 → 新）：新增/删除/修改显式暴露
  （如机制判定回退、school_id 漂移、反推路径改动）

基线独立于产物，改动须显式 --update-snapshot（数据变更=正常迭代，先看 diff
确认是有意变更还是回归，禁止改产物掩盖）。source/source_url 等来源字段不入快照。

用法：
  python3 data/middle/enrollment/test/check_middle_snapshot.py                    # 对比
  python3 data/middle/enrollment/test/check_middle_snapshot.py --update-snapshot  # 更新基线
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
SNAPSHOT = os.path.join(ROOT, "data/middle/enrollment/test/snapshots/middle_snapshot.json")
BUILD = os.path.join(ROOT, "data/middle/enrollment/scripts/build_middle_enrollment.py")
DISTRICT_KEYS = ["panyu", "baiyun", "liwan", "yuexiu", "haizhu", "tianhe", "huangpu"]
# 噪音字段：source/source_url（来源描述/URL）不入快照；行键 = school（官方名单名，脚本输入确定）
RECORD_FIELDS = ("school", "school_id", "school_ids", "plan_classes", "scope",
                 "mechanism", "mechanism_note", "group_members")


def extract() -> dict:
    """重跑 build_middle_enrollment.py 到临时目录 → 按区提取结构化快照。"""
    tmp = tempfile.mkdtemp(prefix="middle_snapshot_")
    try:
        r = subprocess.run(["python3", BUILD, "--out-dir", tmp],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            print("生产脚本重跑失败：build_middle_enrollment.py")
            print(r.stdout[-2000:])
            print(r.stderr[-2000:])
            sys.exit(1)
        districts = {}
        for dk in DISTRICT_KEYS:
            j = json.load(open(os.path.join(tmp, f"middle_enrollment_2026_{dk}.json"), encoding="utf-8"))
            records = {}
            for r0 in j["records"]:
                # 行键 = school（官方名单名；同校多校区合并记录不重复）
                records[r0["school"]] = {f: r0.get(f) for f in RECORD_FIELDS}
            districts[dk] = {"district": j["district"], "records": records}
        return {"districts": districts}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def diff_dict(old: dict, new: dict, path: str, limit: int = 30) -> list:
    out = []
    for k in sorted(set(old) | set(new), key=str):
        if old.get(k) != new.get(k):
            if k not in old:
                out.append(f"    + {path}.{k}: {json.dumps(new[k], ensure_ascii=False)[:120]}")
            elif k not in new:
                out.append(f"    - {path}.{k}: {json.dumps(old[k], ensure_ascii=False)[:120]}")
            else:
                out.append(f"    ~ {path}.{k}: {json.dumps(old[k], ensure_ascii=False)[:100]} → "
                           f"{json.dumps(new[k], ensure_ascii=False)[:100]}")
            if len(out) >= limit:
                out.append(f"    …（仅显示前 {limit} 条，共差异多于此）")
                break
    return out


def run(update: bool) -> int:
    new = extract()
    if update:
        json.dump({**new, "note": "初中招生产物快照（非产物字节，source/source_url 不入快照；records 按 school 索引）。"
                                "更新：--update-snapshot。",
                   "updated": "2026-09-23"}, open(SNAPSHOT, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1, sort_keys=True)
        n = sum(len(d["records"]) for d in new["districts"].values())
        print(f"✓ 基线已更新：{os.path.relpath(SNAPSHOT, ROOT)}（{len(new['districts'])} 区 {n} 条记录）")
        return 0
    if not os.path.exists(SNAPSHOT):
        print(f"基线不存在：{SNAPSHOT}。首次运行请先 --update-snapshot 固化当前正确产物。")
        return 1
    base = json.load(open(SNAPSHOT, encoding="utf-8"))
    diffs = []
    for dk in DISTRICT_KEYS:
        b, n = base.get("districts", {}).get(dk, {}), new["districts"].get(dk, {})
        if len(b.get("records", {})) != len(n.get("records", {})):
            diffs.append(f"    {dk}.records 数量: {len(b.get('records', {}))} → {len(n.get('records', {}))}")
        diffs += diff_dict(b.get("records", {}), n.get("records", {}), f"{dk}.records")
    if diffs:
        print("初中招生快照: ✗ 产物与基线不一致（新增/删除/修改已逐条列出）：")
        print("\n".join(diffs[:40]))
        print("  → 先逐条确认是有意变更（官方源更新/机制判定修正/实体匹配调整）还是回归；确认后显式更新基线：")
        print("     python3 data/middle/enrollment/test/check_middle_snapshot.py --update-snapshot")
        print("  禁止直接改基线或产物掩盖 diff。")
        return 1
    n = sum(len(d["records"]) for d in new["districts"].values())
    print(f"初中招生快照: ✓ 产物与基线全等（{len(new['districts'])} 区 {n} 条记录，独立基线）")
    return 0


if __name__ == "__main__":
    sys.exit(run("--update-snapshot" in sys.argv))
