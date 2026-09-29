#!/usr/bin/env python3
"""从 7 区 minban_*.json 提取 need_entity(需补实体) 与 need_verify(待核实) 完整清单，输出 JSON。

输出结构保持历史契约（中文表头键 + _district/_adcode）：
  need_entity: 官方校名/学段/来源URL/建议实体name/备注
  need_verify: 校名/school_id / stage/来源URL/待核实原因
"""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
SRC_DIR = os.path.join(REPO, "data", "registry", "private", "src")
OUT = os.path.join(REPO, "data", "registry", "private", "parsed", "pending_items.json")

DISTRICTS = [
    ("440103", "荔湾", "liwan"),
    ("440104", "越秀", "yuexiu"),
    ("440105", "海珠", "haizhu"),
    ("440106", "天河", "tianhe"),
    ("440111", "白云", "baiyun"),
    ("440112", "黄埔", "huangpu"),
    ("440113", "番禺", "panyu"),
]


def urls_to_str(urls, ref):
    if urls:
        return "；".join(urls)
    return ref or ""


def main():
    all_need_entity = []
    all_need_verify = []

    for adcode, name, pinyin in DISTRICTS:
        filepath = os.path.join(SRC_DIR, f"minban_{pinyin}.json")
        if not os.path.exists(filepath):
            print(f"[SKIP] {filepath}")
            continue
        data = json.load(open(filepath, encoding="utf-8"))
        sec = data.get("sections", {})

        for r in sec.get("need_entity", []):
            all_need_entity.append({
                "官方校名": r.get("official_name", ""),
                "学段": r.get("stage", ""),
                "来源URL": urls_to_str(r.get("source_urls", []), r.get("source_ref")),
                "建议实体name": r.get("suggested_name", ""),
                "备注": r.get("note", ""),
                "_district": name,
                "_adcode": adcode,
            })

        for r in sec.get("need_verify", []):
            sid = r.get("school_id") or ""
            stage = r.get("stage") or ""
            sid_stage = f"{sid} / {stage}" if sid and stage else (sid or stage)
            all_need_verify.append({
                "校名": r.get("name", ""),
                "school_id / stage": sid_stage,
                "来源URL": urls_to_str(r.get("source_urls", []), r.get("source_ref")),
                "待核实原因": r.get("reason", ""),
                "_district": name,
                "_adcode": adcode,
            })

        print(f"{name}({adcode}): 需补实体={len(sec.get('need_entity', []))}, 待核实={len(sec.get('need_verify', []))}")

    print(f"\n总计：需补实体={len(all_need_entity)}, 待核实={len(all_need_verify)}")

    out = {"need_entity": all_need_entity, "need_verify": all_need_verify}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n已写入 {OUT}")

    print("\n=== 需补实体校名清单 ===")
    for i, r in enumerate(all_need_entity):
        print(f"  {i+1}. [{r['_district']}] {r['官方校名']} | {r['学段']}")


if __name__ == "__main__":
    main()
