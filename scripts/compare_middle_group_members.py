#!/usr/bin/env python3
"""初中直建前后 group_members 对比审计（2026-09-23）。

背景：4 区 dist 构建由 xiaoshengchu 反推切换为官方转录直建后，parsed 中间产物
记录顺序/条数变化大（一校多规则展开），无法直接 diff。本脚本按「学校」维度聚合
对比 group_members（该校所在全部派位组的成员校并集）：
  - 旧：git HEAD~1 parsed/middle_enrollment_2026_<区>.json（反推版，一校一条）
  - 新：工作区 parsed/middle_enrollment_2026_<区>.json（官方直建，一校多规则）

输出：逐区逐校 group_members 集合变化（新增/移除成员），以及「无派位组成员」
（single_zone/直升行 group_members=None 不算变化）的汇总。

用法：python3 scripts/compare_middle_group_members.py [--git-ref HEAD~1]
"""
import json, subprocess, sys

DISTRICTS = ["yuexiu", "haizhu", "tianhe", "huangpu"]
GIT_REF = "HEAD~1"

def git_show(path):
    r = subprocess.run(["git", "show", f"{GIT_REF}:{path}"], capture_output=True)
    if r.returncode != 0 or not r.stdout:
        return None
    return json.loads(r.stdout)

def group_members_by_school(records):
    """按 school 聚合全部 group_members 并集（一校多组展开）。"""
    out = {}
    for r in records:
        gm = r.get("group_members")
        if not gm:
            continue
        out.setdefault(r["school"], set()).update(gm)
    return out

def main():
    total_add = total_rm = 0
    for dk in DISTRICTS:
        old = git_show(f"data/middle/enrollment/parsed/middle_enrollment_2026/middle_enrollment_2026_{dk}.json")
        new = json.load(open(f"data/middle/enrollment/parsed/middle_enrollment_2026/middle_enrollment_2026_{dk}.json"))
        if old is None:
            print(f"[{dk}] 旧产物缺失（{GIT_REF} 无该文件）——跳过对比")
            continue
        o = group_members_by_school(old.get("records", []))
        n = group_members_by_school(new.get("records", []))
        print(f"===== {dk}: 有派位组成员的学校 旧{len(o)} → 新{len(n)} =====")
        for school in sorted(set(o) | set(n)):
            os_, ns_ = o.get(school, set()), n.get(school, set())
            if os_ == ns_:
                continue
            added, removed = ns_ - os_, os_ - ns_
            total_add += len(added); total_rm += len(removed)
            tag = []
            if added: tag.append(f"+{len(added)} 成员")
            if removed: tag.append(f"-{len(removed)} 成员")
            if school in o and school not in n:
                tag.append("(该校已无派位组记录)")
            if school not in o and school in n:
                tag.append("(该校新增派位组记录)")
            print(f"  {school} [{', '.join(tag)}]")
            if added: print(f"      新增: {sorted(added)}")
            if removed: print(f"      移除: {sorted(removed)}")
    print(f"\n汇总: 成员新增 {total_add} 处 / 移除 {total_rm} 处")

if __name__ == "__main__":
    main()
