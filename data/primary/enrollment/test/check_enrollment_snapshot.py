#!/usr/bin/env python3
"""小学招生产物快照对比（npm run check 链）。

重跑 build_primary_2026.py --out-dir 到临时目录（绝不碰 dist），提取结构化快照
（records 的 school → 字段 + minban + unmatched/ambiguous），与独立基线全等对比：

- 全等 → 通过：小学招生产物未发生意外变化
- 有差异 → 失败并逐条列出（旧 → 新）：新增/删除/修改显式暴露
  （如地段 zone 改动、匹配 school_id 漂移、民办计划增删）

基线独立于产物，改动须显式 --update-snapshot（数据变更=正常迭代，先看 diff
确认是有意变更还是回归，禁止改产物掩盖）。坐标/时间戳等噪音字段不入快照。

用法：
  python3 data/primary/enrollment/test/check_enrollment_snapshot.py                    # 对比
  python3 data/primary/enrollment/test/check_enrollment_snapshot.py --update-snapshot  # 更新基线
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
SNAPSHOT = os.path.join(ROOT, "data/primary/enrollment/test/snapshots/enrollment_snapshot.json")
BUILD = os.path.join(ROOT, "data/primary/enrollment/scripts/build_primary_2026.py")
DISTRICTS = ["yuexiu", "liwan", "haizhu", "tianhe", "panyu", "baiyun", "huangpu"]
DISTRICT_NAMES = {"yuexiu": "越秀区", "liwan": "荔湾区", "haizhu": "海珠区", "tianhe": "天河区",
                  "panyu": "番禺区", "baiyun": "白云区", "huangpu": "黄埔区"}
# 噪音字段：坐标/来源 URL 不入快照
RECORD_FIELDS = ("district", "plan_classes", "zone", "note", "phone", "school_id", "poi_name")
MINBAN_FIELDS = ("district", "plan_classes", "plan_count", "school_id", "poi_name")


def extract() -> dict:
    """重跑 build_primary_2026.py all --out-dir TMP → 各区结构化快照。"""
    tmp = tempfile.mkdtemp(prefix="enrollment_snapshot_")
    try:
        r = subprocess.run(["python3", BUILD, "all", "--out-dir", tmp],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            print("生产脚本重跑失败：build_primary_2026.py")
            print(r.stdout[-2000:])
            print(r.stderr[-2000:])
            sys.exit(1)
        districts = {}
        for k in DISTRICTS:
            p = os.path.join(tmp, f"2026-{k}.json")
            j = json.load(open(p, encoding="utf-8"))
            records = {}
            for r0 in j.get("records", []):
                records[r0["school"]] = {f: r0.get(f) for f in RECORD_FIELDS}
            minban = {}
            for m in j.get("minban", []):
                minban[m["school"]] = {f: m.get(f) for f in MINBAN_FIELDS}
            districts[DISTRICT_NAMES[k]] = {
                "records": records,
                "minban": minban,
                "unmatched": sorted(j.get("unmatched", [])),
                "ambiguous": sorted(
                    f"{a['school']}↔{a['poi']}" for a in j.get("ambiguous", [])),
            }
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
        json.dump({**new, "note": "小学招生产物快照（非产物字节，坐标/来源URL不入快照；records 按 school 索引）。"
                                "更新：--update-snapshot。",
                   "updated": "2026-09-22"}, open(SNAPSHOT, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1, sort_keys=True)
        n = sum(len(d["records"]) for d in new["districts"].values())
        print(f"✓ 基线已更新：{os.path.relpath(SNAPSHOT, ROOT)}（{len(new['districts'])} 区 {n} 条记录）")
        return 0
    if not os.path.exists(SNAPSHOT):
        print(f"基线不存在：{SNAPSHOT}。首次运行请先 --update-snapshot 固化当前正确产物。")
        return 1
    base = json.load(open(SNAPSHOT, encoding="utf-8"))
    diffs = []
    for dname in DISTRICT_NAMES.values():
        b, n = base.get("districts", {}).get(dname, {}), new["districts"].get(dname, {})
        if len(b.get("records", {})) != len(n.get("records", {})):
            diffs.append(f"    {dname}.records 数量: {len(b.get('records', {}))} → {len(n.get('records', {}))}")
        diffs += diff_dict(b.get("records", {}), n.get("records", {}), f"{dname}.records")
        diffs += diff_dict(b.get("minban", {}), n.get("minban", {}), f"{dname}.minban")
        diffs += diff_dict({u: True for u in b.get("unmatched", [])},
                           {u: True for u in n.get("unmatched", [])}, f"{dname}.unmatched")
        diffs += diff_dict({a: True for a in b.get("ambiguous", [])},
                           {a: True for a in n.get("ambiguous", [])}, f"{dname}.ambiguous")
    if diffs:
        print("小学招生快照: ✗ 产物与基线不一致（新增/删除/修改已逐条列出）：")
        print("\n".join(diffs[:40]))
        print("  → 先逐条确认是有意变更（官方源更新/zone 修正/实体匹配调整）还是回归；确认后显式更新基线：")
        print("     python3 data/primary/enrollment/test/check_enrollment_snapshot.py --update-snapshot")
        print("  禁止直接改基线或产物掩盖 diff。")
        return 1
    n = sum(len(d["records"]) for d in new["districts"].values())
    print(f"小学招生快照: ✓ 产物与基线全等（{len(new['districts'])} 区 {n} 条记录，独立基线）")
    return 0


if __name__ == "__main__":
    sys.exit(run("--update-snapshot" in sys.argv))
