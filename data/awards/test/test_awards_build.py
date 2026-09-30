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

ROOT = Path(__file__).resolve().parents[3]  # data/awards/test → ROOT
HUAYING = "gz-440106-dab5b807"
TIANHE_FOREIGN = {"gz-440106-069ddb41", "gz-440106-b711d94a"}
XIAOBEI = {"gz-440104-d5497b4b", "gz-440104-98359a64", "gz-440104-4ebbaf83", "gz-440104-1b6d4b9c"}
HUANSHI_WEST = "gz-440103-65d7792a"
GUANGFU_HUANGHUA = "gz-440104-b22c4eca"
SUYUAN = {"gz-440112-8bf29a28", "gz-440112-a0244635"}   # 苏元学校（高中实体 + 西校区初中实体）
HUIJING = "gz-440106-0d1e149e"                          # 天河区汇景实验学校
NANWU = {"gz-440105-515da9e2", "gz-440105-dd2723fc"}    # 南武中学高中部 + 岭南画派纪念校区

# 这是完整产物的语义指纹，不依赖 JSON 缩进或字段排列。源文件/匹配规则变化
# 会触发失败，要求人工核对后再更新；不要为通过测试直接刷新这组值。
SNAPSHOT = {
    "innovation": {"records": 522, "matched": 392, "digest": "8d0825e6069e64043b0f25057e5e7aff8a63d3b994729ed1a83f4d53333dd392"},
    "chuangke": {"years": 2, "records": 145, "matched": 113, "digest": "68e923581fc8558056281643674f7c58457adfda30f49bee61dfbcf3b7731534"},
    "science_literacy": {"records": 531, "matched": 352},
    "tech_sports": {"records": 2708, "matched": 1850, "digest": "575d610b5082aa4c424c5121d08f0e9be6d64565bed42d968761b5bc46e0c432"},
    "science_experiment": {"records": 584, "matched": 411, "digest": "d8e46d9e20a2604a370dd07d4900c312d783623d6bc875eb8e9e564519abd117"},
    "yueyunbei": {"records": 29771, "matched": 23567, "digest": "ef49d92a6fd870931dc841dd1dfe03df1b8f798128d1b9e7c54ba8d49b036678"},
    "details": {"records": 26685, "digest": "45372e79c1bd23481421a3edcbe3adf941e299efc19ddd4eb915eb9d62a279d1"},
}


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def fail(message):
    print(f"  ✗ {message}")
    return False


def main():
    # parsed → dist：仅重建前端消费的白名单竞赛详情，不读取原始 xls 文件。
    r = subprocess.run(
        [sys.executable, str(ROOT / "data/awards/scripts/build_detailed_records.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    if r.returncode != 0:
        print("  ✗ 竞赛详情产物重建失败（build_detailed_records.py）")
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        sys.exit(r.returncode)
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
    science = []
    for path in sorted((ROOT / "data/awards/science_literacy/parsed").glob("science_literacy_*.json")):
        science.extend(json.loads(path.read_text("utf-8"))["records"])
    tech = []
    for path in sorted((ROOT / "data/awards/tech_sports/parsed").glob("tech_sports_*.json")):
        tech.extend(json.loads(path.read_text("utf-8"))["records"])
    science_experiment = []
    for path in sorted((ROOT / "data/awards/science_experiment/parsed").glob("science_experiment_*.json")):
        science_experiment.extend(json.loads(path.read_text("utf-8"))["records"])
    yueyunbei = []
    for path in sorted((ROOT / "data/awards/yueyunbei/parsed").glob("yueyunbei_*.json")):
        yueyunbei.extend(json.loads(path.read_text("utf-8"))["records"])

    actual = {
        "innovation": {"records": len(innovation), "matched": sum(bool(x["school_ids"]) for x in innovation), "digest": digest(innovation)},
        "chuangke": {"years": len(chuangke), "records": sum(len(y["records"]) for y in chuangke),
                     "matched": sum(bool(r["school_ids"]) for y in chuangke for r in y["records"]), "digest": digest(chuangke)},
        "science_literacy": {"records": len(science), "matched": sum(bool(r["school_ids"]) for r in science)},
        "tech_sports": {"records": len(tech), "matched": sum(bool(r["school_ids"]) for r in tech), "digest": digest(tech)},
        "science_experiment": {"records": len(science_experiment), "matched": sum(bool(r["school_ids"]) for r in science_experiment), "digest": digest(science_experiment)},
        "yueyunbei": {"records": len(yueyunbei), "matched": sum(bool(r["school_ids"]) for r in yueyunbei), "digest": digest(yueyunbei)},
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

    suyuan = find("tech_sports", "广州市黄埔区苏元学校", stage="secondary", year=2026)
    if not (bool(suyuan) and any(set(r["school_ids"]) == SUYUAN for r in suyuan)):
        ok = fail("苏元学校测向 M15 组未归属苏元初高中实体") and ok

    huijing = find("tech_sports", "广州市天河区汇景实验学校", stage="secondary", year=2026)
    if not (bool(huijing) and all(set(r["school_ids"]) == {HUIJING} for r in huijing)):
        ok = fail("汇景实验学校中学组团队未精确归属") and ok

    nanwu = find("tech_sports", "广州市南武中学", stage="high", year=2026)
    if not (bool(nanwu) and all(set(r["school_ids"]) == NANWU for r in nanwu)):
        ok = fail("南武中学测向 M18 组未挂高中实体") and ok

    qifu_2024 = find("tech_sports", "广州市番禺区祈福新邨学校", stage="primary", year=2024)
    if not (bool(qifu_2024) and all(set(r["school_ids"]) == {"gz-440113-1963cc5e"} for r in qifu_2024)):
        ok = fail("祈福新邨学校 2024 模型系列未精确归属") and ok

    qifu_2025 = find("tech_sports", "广州市番禺区祈福新邨学校", stage="primary", year=2025)
    if not (bool(qifu_2025) and all(set(r["school_ids"]) == {"gz-440113-1963cc5e"} for r in qifu_2025)):
        ok = fail("祈福新邨学校 2025 市级总决赛未精确归属") and ok

    exp = find("science_experiment", "广州市番禺区市桥左边小学", stage="primary", year=2025)
    if not (bool(exp) and all(set(r["school_ids"]) for r in exp)):
        ok = fail("科学实验大赛获奖明细未进入详情产物") and ok

    yue = find("yueyunbei", "广州市番禺区祈福新邨学校", stage="primary", year=2026)
    if not (bool(yue) and all(set(r["school_ids"]) == {"gz-440113-1963cc5e"} for r in yue)):
        ok = fail("祈福新邨学校 2026 粤韵杯未精确归属") and ok

    if not ok:
        print(f"✗ 竞赛构建回归: {len(innovation)} 条创新 + {actual['chuangke']['records']} 条创客 + "
              f"{actual['science_literacy']['matched']} 条科学素养 + {actual['tech_sports']['matched']} 条科技体育，失败")
        sys.exit(1)
    print("✓ 竞赛构建回归通过")


if __name__ == "__main__":
    main()
