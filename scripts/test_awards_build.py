#!/usr/bin/env python3
"""白名单竞赛构建产物回归测试。

测试从已解析的赛事名单开始，内部重建详情 dist 产物，再监控完整语义摘要和
关键学校归属。原始 `.xls` → parsed 的解析不属于本测试范围。
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUAYING = "gz-440106-dab5b807"
TIANHE_FOREIGN = {"gz-440106-069ddb41", "gz-440106-b711d94a"}
XIAOBEI = {"gz-440104-d5497b4b", "gz-440104-98359a64", "gz-440104-4ebbaf83", "gz-440104-1b6d4b9c"}
HUANSHI_WEST = "gz-440103-65d7792a"
GUANGFU_HUANGHUA = "gz-440104-b22c4eca"

# 这是完整产物的语义指纹，不依赖 JSON 缩进或字段排列。源文件/匹配规则变化
# 会触发失败，要求人工核对后再更新；不要为通过测试直接刷新这组值。
SNAPSHOT = {
    "innovation": {"records": 522, "matched": 392, "digest": "06e62dfd2dfb991450236c908df191a0deb604f499a33e609711b951f34512f6"},
    "chuangke": {"years": 2, "records": 145, "matched": 112, "digest": "773b3536ff6bacdc6d8e4c2989a067713d72ed09cc5fd11d264fcc5a38a57c39"},
    "science_literacy": {"records": 272, "matched": 185},
    "details": {"records": 689, "digest": "a2585590c2c39686a6095e2266126af16175d16d20d00d0958478bace26cd7aa"},
}


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def fail(message):
    print(f"  ✗ {message}")
    return False


def main():
    # parsed → dist：仅重建前端消费的白名单竞赛详情，不读取原始 xls 文件。
    subprocess.run(
        [sys.executable, str(ROOT / "data/awards/scripts/build_detailed_records.py")],
        cwd=ROOT, check=True,
    )
    innovation = []
    for path in sorted((ROOT / "data/awards/innovation/parsed").glob("innovation_*.json")):
        doc = json.loads(path.read_text("utf-8"))
        for record in doc["records"]:
            innovation.append({
                "stage": doc["stage"], "year": doc["year"], "school": record["school"],
                "project": record["project"], "award": record["award"], "school_ids": record["school_ids"],
            })
    chuangke = json.loads((ROOT / "data/awards/chuangke/parsed/chuangke.json").read_text("utf-8"))["records"]
    details = json.loads((ROOT / "data/awards/dist/detailed_records.json").read_text("utf-8"))
    science = json.loads((ROOT / "data/awards/science_literacy/parsed/science_literacy_2025.json").read_text("utf-8"))

    actual = {
        "innovation": {"records": len(innovation), "matched": sum(bool(x["school_ids"]) for x in innovation), "digest": digest(innovation)},
        "chuangke": {"years": len(chuangke), "records": sum(len(y["records"]) for y in chuangke),
                     "matched": sum(bool(r["school_ids"]) for y in chuangke for r in y["records"]), "digest": digest(chuangke)},
        "science_literacy": {"records": len(science["records"]), "matched": sum(bool(r["school_ids"]) for r in science["records"])},
        "details": {"records": len(details), "digest": digest(details)},
    }
    ok = True
    if actual != SNAPSHOT:
        ok = fail(f"竞赛构建产物摘要变化:\n  current={json.dumps(actual, ensure_ascii=False)}\n  expected={json.dumps(SNAPSHOT, ensure_ascii=False)}") and ok

    def find(competition, school, **conditions):
        return [r for r in details if r["competition"] == competition and r["school"] == school
                and all(r.get(k) == v for k, v in conditions.items())]

    huaying = find("innovation", "广州市华颖外国语学校", stage="middle", year=2025)
    if not (bool(huaying) and all(set(r["school_ids"]) == {HUAYING} for r in huaying)):
        ok = fail("华颖 2025 创新大赛奖项未精确归属") and ok

    tianhe = find("innovation", "广州市天河外国语学校") + find("chuangke", "广州市天河外国语学校")
    if not (bool(tianhe) and all(HUAYING not in r["school_ids"] for r in tianhe)
            and all(set(r["school_ids"]) == TIANHE_FOREIGN for r in tianhe)):
        ok = fail("天河外国语学校奖项混入华颖或校区集合漂移") and ok

    xiaobei = find("chuangke", "广州市越秀区小北路小学", stage="primary", year=2024)
    if not (len(xiaobei) == 1 and set(xiaobei[0]["school_ids"]) == XIAOBEI):
        ok = fail("小北路小学未展开四个校区") and ok

    huanshi = find("chuangke", "广州市第一中学附属环市西路小学（竹苑校区）", stage="primary", year=2025)
    if not (len(huanshi) == 1 and huanshi[0]["school_ids"] == [HUANSHI_WEST]):
        ok = fail("环市西路小学竹苑校区别名未精确归属") and ok

    guangfu = [r for r in innovation if r["school"] == "广州大学附属中学（校本部）"]
    if not (bool(guangfu) and all(r["school_ids"] == [GUANGFU_HUANGHUA] for r in guangfu)):
        ok = fail("广大附中校本部别名未指向黄华路校区") and ok

    science_details = find("science_literacy", "广州市铁一中学", year=2025)
    if not science_details or not all(r["stage"] in {"primary", "middle", "high"} for r in science_details):
        ok = fail("科学素养大赛学生获奖明细未进入详情产物") and ok

    print(f"竞赛构建回归: {len(innovation)} 条创新 + {actual['chuangke']['records']} 条创客 + {actual['science_literacy']['matched']} 条科学素养，{'通过' if ok else '失败'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
