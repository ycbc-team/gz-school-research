#!/usr/bin/env python3
"""复现解析：越秀区小学新生登记范围（yuexiu_2026.json）

输入: raw/yuexiu_2026_official.doc（招生简章附件5，.doc 旧格式）
      1) macOS textutil 转文本（脚本内完成）→ raw/yuexiu_2026_diduan.txt
      2) 解析 "（NN）2026年广州市越秀区XXX一年级新生登记范围" 块
输出: parsed/_transcripts/yuexiu_2026.json
      {"district","source","source_url","schools":[{school,plan_classes,zone,note,phone}, ...]}

同一块号多次出现（多校区/多行政街）→ 合并 zone；plan_classes 取自"说明: 计划招生X个班"。
用途: 复现 2026-09-10 人工转录，保证可审计可重跑。
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
DATA = os.path.join(ROOT, "data", "primary", "enrollment")
PARSED = os.path.join(DATA, "parsed", "_transcripts")
RAW = os.path.join(ROOT, "data", "enrollment", "raw")
OUT = os.path.join(DATA, "parsed", "_transcripts", "yuexiu_2026.json")

SRC_URL = "http://www.yuexiu.gov.cn/gzjg/qzf/qjyj/jyzl/gk/zxjyxx/content/post_10790024.html"
SOURCE = "越秀区教育局《2026年越秀区小学新生登记范围》（招生简章附件5）"


def doc_to_txt(doc_path, txt_path):
    if os.path.exists(txt_path):
        return
    subprocess.run(["textutil", "-convert", "txt", doc_path, "-output", txt_path], check=True)


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


def main():
    doc_path = os.path.join(RAW, "yuexiu_2026_official.doc")
    txt_path = os.path.join(PARSED, "yuexiu_2026_diduan.txt")
    doc_to_txt(doc_path, txt_path)
    t = open(txt_path, encoding="utf-8", errors="replace").read()

    # 块切分：以 （NN）/(NN) 开头或直接标题开头的新块（textutil 转换可能丢部分块号）
    blocks = []
    for m in re.finditer(r"(?:[（(]\s*\d{1,2}\s*[）)]\s*)?(20\d\d年广州市(?:越秀区)?[^\n]+?一年级新生登记范围)\s*\n", t):
        blocks.append((m.start(), m.group(1)))
    if not blocks:
        raise SystemExit("未解析到任何块")
    schools = []
    for i, (pos, title) in enumerate(blocks):
        end = blocks[i + 1][0] if i + 1 < len(blocks) else len(t)
        body = t[pos:end]
        # 去掉标题行
        nl = body.find("\n")
        body = body[nl:] if nl >= 0 else ""
        # 学校名清洗
        name = title
        name = name.replace("2026年广州市越秀区", "").replace("2026年广州市", "").replace("一年级新生登记范围", "")
        name = clean(name)
        # 范围：行政街 + 范围行（直到 说明:）
        plan = None
        pm = re.search(r"说明[:：]\s*计划招生\s*(\d+)\s*个班", body)
        if pm:
            plan = int(pm.group(1))
        # zone: 去掉标题行、表头行、说明行，保留行政街与范围
        lines = []
        for ln in body.splitlines():
            s = ln.strip()
            if not s or s == "行政街" or re.match(r"^范\s*围$", s) or s.startswith("说明"):
                continue
            lines.append(s)
        zone = "\n".join(lines)
        schools.append({"school": name, "plan_classes": plan, "zone": zone, "note": "", "phone": ""})

    # 同名校合并 zone（多校区/多行政街）
    merged = []
    by_name = {}
    for s in schools:
        if s["school"] in by_name:
            by_name[s["school"]]["zone"] += "\n" + s["zone"]
            if by_name[s["school"]]["plan_classes"] is None:
                by_name[s["school"]]["plan_classes"] = s["plan_classes"]
        else:
            by_name[s["school"]] = dict(s)
            merged.append(by_name[s["school"]])

    out = {"district": "越秀区", "source": SOURCE, "source_url": SRC_URL, "schools": merged}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"✓ {OUT}  {len(merged)} 校（块 {len(schools)}）")

    # 与现状对比
    old = json.load(open(OUT, encoding="utf-8"))
    old_s = {s["school"]: s for s in old["schools"]}
    print(f"现状 {len(old_s)} 校，新 {len(merged)} 校")
    new_names = {s["school"] for s in merged}
    print("现状有、新无:", [k for k in old_s if k not in new_names])
    print("新有、现状无:", [s["school"] for s in merged if s["school"] not in old_s])
    diff_cnt = 0
    for s in merged:
        o = old_s.get(s["school"])
        if not o:
            continue
        if o.get("plan_classes") != s["plan_classes"]:
            print(f"  班数 DIFF {s['school']}: 现={o.get('plan_classes')} 新={s['plan_classes']}")
            diff_cnt += 1
        if (o.get("zone") or "") != (s["zone"] or ""):
            print(f"  zone DIFF {s['school']}: 现{len(o.get('zone',''))}字 新{len(s['zone'])}字")
            diff_cnt += 1
    print(f"差异 {diff_cnt} 处")


if __name__ == "__main__":
    main()
