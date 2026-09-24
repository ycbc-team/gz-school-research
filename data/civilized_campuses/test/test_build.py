#!/usr/bin/env python3
"""文明校园业务唯一测试入口：全国、省级、广州市正式及创建储备。"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

B = Path(__file__).resolve().parents[1]
ROOT = B.parents[1]
DIST = B / "dist" / "civilized_campus_school_ids.json"

def run(args):
    result = subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, text=True, capture_output=True)
    if result.returncode: raise SystemExit(result.stdout + result.stderr)

def assert_snapshot(command, snapshot):
    with tempfile.TemporaryDirectory(prefix="civilized-campus-") as temp:
        actual = Path(temp) / snapshot.name
        run([*command, str(actual)])
        assert json.loads(actual.read_text(encoding="utf-8")) == json.loads(snapshot.read_text(encoding="utf-8")), f"匹配审阅已变化：请人工确认后更新 {snapshot.relative_to(ROOT)}"

def main():
    # 全国：名单、黑名单及快照
    national_build = B / "scripts" / "build_dist.py"
    run([national_build, "--check"])
    data = json.loads(DIST.read_text(encoding="utf-8"))
    for level in ("national", "provincial", "municipal", "advanced"):
        assert isinstance(data[level], list) and data[level] == sorted(set(data[level]))
        assert all(x.startswith("gz-") for x in data[level])
    assert data["national"], "national 不得为空"
    national_snapshot = B / "test" / "national_civilized_campus_match_review.json"
    assert_snapshot([national_build, "--review-output"], national_snapshot)

    # 省级第一届正式名单
    provincial = json.loads((B / "parsed" / "provincial_civilized_campuses.json").read_text(encoding="utf-8"))["records"]
    assert len(provincial) == 61
    assert_snapshot([B / "scripts" / "build_provincial_dist.py", "--review-output"], B / "test" / "provincial_civilized_campuses_match_review.json")

    # 广州：正式和创建储备快照必须分开
    municipal = json.loads((B / "parsed" / "guangzhou_civilized_campuses.json").read_text(encoding="utf-8"))["records"]
    assert sum(x["level"] == "市级正式" for x in municipal) == 49
    assert sum(x["level"] == "创建储备" for x in municipal) == 63
    with tempfile.TemporaryDirectory(prefix="civilized-campus-") as temp:
        formal, advanced = Path(temp) / "formal.json", Path(temp) / "advanced.json"
        run([B / "scripts" / "build_guangzhou_dist.py", "--formal-review-output", formal, "--advanced-review-output", advanced])
        for actual, expected in ((formal, B / "test" / "guangzhou_civilized_campuses_formal_match_review.json"), (advanced, B / "test" / "guangzhou_civilized_campuses_advanced_match_review.json")):
            assert json.loads(actual.read_text(encoding="utf-8")) == json.loads(expected.read_text(encoding="utf-8")), f"匹配审阅已变化：请人工确认后更新 {expected.relative_to(ROOT)}"
    print("[civilized] ok: national / provincial / municipal / advanced")

if __name__ == "__main__": main()
