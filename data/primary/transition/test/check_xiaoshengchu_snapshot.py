#!/usr/bin/env python3
"""小升初升学事实表（xiaoshengchu_2026.json）快照对比（npm run check 链）。

重跑 xiaoshengchu 生产链路到临时目录（绝不碰正式 dist）：
  build_xiaoshengchu_all.py all_done --out-dir <tmp>   （重建 7 区 + 汇总，含 xs_resolver 解析）
  upgrade_xiaoshengchu.mjs --src <tmp>/xiaoshengchu_all.json --out <tmp>/xiaoshengchu_2026.json
提取结构化快照（records 按 school_id 索引 → 字段 + groups 维表），与独立基线全等对比：

- 全等 → 通过：小升初产物未发生意外变化
- 有差异 → 失败并逐条列出（旧 → 新）：新增/删除/修改显式暴露
  （如来源表更新、实体匹配调整、去重规则回退）

基线独立于产物，改动须显式 --update-snapshot（数据变更=正常迭代，先看 diff
确认是有意变更还是回归，禁止改产物掩盖）。source_url/source_note 等来源字段不入快照。

用法：
  python3 data/primary/transition/test/check_xiaoshengchu_snapshot.py                    # 对比
  python3 data/primary/transition/test/check_xiaoshengchu_snapshot.py --update-snapshot  # 更新基线
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
SNAPSHOT = os.path.join(ROOT, "data/primary/transition/test/snapshots/xiaoshengchu_snapshot.json")
BUILD = os.path.join(ROOT, "data/primary/transition/scripts/build_xiaoshengchu_all.py")
UPGRADE = os.path.join(ROOT, "data/primary/transition/scripts/upgrade_xiaoshengchu.mjs")
# 噪音字段：source_urls/source_note（来源描述）不入快照；records 行键 = school_id
RECORD_FIELDS = ("group_id", "feed_school_ids", "feed_unresolved", "direct_feed_school_id", "data_gaps")


def extract() -> dict:
    """重跑 xiaoshengchu 全链路到临时目录 → 提取结构化快照。"""
    tmp = tempfile.mkdtemp(prefix="xiaoshengchu_snapshot_")
    try:
        r = subprocess.run(["python3", BUILD, "all_done", "--out-dir", tmp],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            print("生产脚本重跑失败：build_xiaoshengchu_all.py all_done --out-dir")
            print(r.stdout[-2000:])
            print(r.stderr[-2000:])
            sys.exit(1)
        all_json = os.path.join(tmp, "xiaoshengchu_all.json")
        out_json = os.path.join(tmp, "xiaoshengchu_2026.json")
        r = subprocess.run(["node", UPGRADE, "--src", all_json, "--out", out_json],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            print("生产脚本重跑失败：upgrade_xiaoshengchu.mjs")
            print(r.stdout[-2000:])
            print(r.stderr[-2000:])
            sys.exit(1)
        j = json.load(open(out_json, encoding="utf-8"))
        records = {}
        for r0 in j["records"]:
            # 行键 = school_id（同校多记录不重复；无 school_id 的历史缺口记录逐条保留
            # （group_id, index）防去重）
            key = r0.get("school_id")
            if not key:
                key = f"(nogap#{r0.get('group_id')}#{len(records)})"
            records[str(key)] = {f: r0.get(f) for f in RECORD_FIELDS}
        groups = {}
        for g in j.get("groups", []):
            groups[str(g["id"])] = {"name": g.get("name"), "data_gaps": g.get("data_gaps")}
        return {"year": j.get("year"), "records": records, "groups": groups}
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
        json.dump({**new, "note": "小升初升学事实表快照（非产物字节，source_url/source_note 不入快照；"
                                  "records 按 school_id 索引，groups 为分组维表）。更新：--update-snapshot。",
                   "updated": "2026-09-23"}, open(SNAPSHOT, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1, sort_keys=True)
        print(f"✓ 基线已更新：{os.path.relpath(SNAPSHOT, ROOT)}（{len(new['records'])} 条记录 / {len(new['groups'])} 组）")
        return 0
    if not os.path.exists(SNAPSHOT):
        print(f"基线不存在：{SNAPSHOT}。首次运行请先 --update-snapshot 固化当前正确产物。")
        return 1
    base = json.load(open(SNAPSHOT, encoding="utf-8"))
    diffs = []
    b, n = base.get("records", {}), new.get("records", {})
    if len(b) != len(n):
        diffs.append(f"    records 数量: {len(b)} → {len(n)}")
    diffs += diff_dict(b, n, "records")
    bg, ng = base.get("groups", {}), new.get("groups", {})
    if len(bg) != len(ng):
        diffs.append(f"    groups 数量: {len(bg)} → {len(ng)}")
    diffs += diff_dict(bg, ng, "groups")
    if diffs:
        print("小升初快照: ✗ 产物与基线不一致（新增/删除/修改已逐条列出）：")
        print("\n".join(diffs[:40]))
        print("  → 先逐条确认是有意变更（官方源更新/实体匹配调整/去重规则修正）还是回归；确认后显式更新基线：")
        print("     python3 data/primary/transition/test/check_xiaoshengchu_snapshot.py --update-snapshot")
        print("  禁止直接改基线或产物掩盖 diff。")
        return 1
    print(f"小升初快照: ✓ 产物与基线全等（{len(new['records'])} 条记录 / {len(new['groups'])} 组，独立基线）")
    return 0


if __name__ == "__main__":
    sys.exit(run("--update-snapshot" in sys.argv))
