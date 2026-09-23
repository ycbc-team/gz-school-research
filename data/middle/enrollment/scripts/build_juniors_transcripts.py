#!/usr/bin/env python3
"""复现越秀/海珠/天河/黄埔初中转录 json（parsed/_transcripts/<区>_2026_juniors.json）。

数据源：transcripts_juniors/*.py（2026-09-23 用 Read 多模态直读官网后落盘的转录数据）：
  yuexiu_juniors.py   → yuexiu_2026_juniors.json（2022 官方分组表 11 组×10 初中 + 8 直升，网页）
  haizhu_juniors.py   → haizhu_2026_juniors.json（附件1 派位 10 组 + 19 直升 + 计划表 28 校班数，网页图片）
  tianhe_juniors.py   → tianhe_2026_juniors.json（PDF 附件6 公办 24 + 附件7 企事业 3 + 附件8 民办 24）
  huangpu_juniors.py  → huangpu_2026_juniors.json（PDF 附件5 派位 7 组 + 直升 22 组）

官方原件：越秀/海珠在共享 raw（yuexiu_2026_juniors_groups.html、haizhu_2026_juniors_faq_*.jpg、
haizhu_2026_juniors_plan.png，2026-09-23 补下载）；天河/黄埔为共享 raw PDF（tianhe_2026_official.pdf、
huangpu_2026_official.pdf）。数据与构建脚本交叉校验过（见 README 对齐表）。

用法: python3 data/middle/enrollment/scripts/build_juniors_transcripts.py
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
OUT = os.path.join(ROOT, "data", "middle", "enrollment", "parsed", "_transcripts")
DATA_DIR = os.path.join(HERE, "transcripts_juniors")

META = {
    "yuexiu": {
        "source": "2022年越秀区小学升初中电脑派位生分组表（官网 post_8301356；2026 细则 post_10790590 第九条确认分组保持稳定，志愿填报学校数 12→10 所）",
        "source_url": "http://www.yuexiu.gov.cn/gzjg/qzf/qjyj/jyzl/gk/zswd/content/post_8301356.html",
        "note": "无班数/范围（官方分组表仅组结构）；中学名按官网简称展开为官方全称（省越天胜=广东实验中学越秀学校(天胜校区)等，2026-09-21 核对）；矿泉中学→培正矿泉学校（瑶台改造）",
        "mechanism": "group_paidui",
    },
    "haizhu": {
        "source": "2026年海珠区初中招生问答（mpost_10799155）附件1《2026年海珠区公办初中招生普通电脑派位分组表》+ 正文对口直升 + 2026年海珠区公办初中招生计划表（mpost_10788494）",
        "source_url": "https://www.haizhu.gov.cn/gzhzjy/gkmlpt/content/10/10799/mpost_10799155.html",
        "source_url_plan": "https://www.haizhu.gov.cn/bmml/jyj/content/mpost_10788494.html",
        "note": "派位组内全部初中为可填志愿；直升校为可选路径（直升则放弃派位）。计划表班数网页直读 2026-09-23",
        "mechanism": "group_paidui",
    },
    "tianhe": {
        "source": "2026年天河区义务教育阶段学校招生工作细则（穗天教〔2026〕2号，官网 PDF 10791180）附件6《公办初中划片范围及招生计划表》+ 附件7《企事业办中小学招生计划表》+ 附件8《民办学校招生计划表》",
        "source_url": "http://www.thnet.gov.cn/attachment/8/8016/8016210/10791180.pdf",
        "note": "Read 多模态直读官网 PDF 转录（2026-09-23）；附件6 公办 24 序号（22/23 号为两校区合并行）；附件6 合计 288+2（特教）与逐行和有差，22/23 号班数待复核；附件8 民办 32 所中 24 所有初中部",
    },
    "huangpu": {
        "source": "2026年黄埔区义务教育学校招生工作实施细则（穗埔教〔2026〕265号，官网 PDF 10791836）附件5《2026年黄埔区小升初电脑随机派位及对口直升分组表》",
        "source_url": "http://www.hp.gov.cn/attachment/8/8016/8016631/10791836.pdf",
        "note": "Read 多模态直读官网 PDF 转录（2026-09-23）；官方文件无班数/范围列（班数在区属公办小学计划表，小学侧已转录）；派位组/直升组小学列按官方原文，含服务地段范围",
        "mechanism": "group_paidui + direct_feed",
    },
}
DISTRICT = {"yuexiu": "越秀区", "haizhu": "海珠区", "tianhe": "天河区", "huangpu": "黄埔区"}
# 各转录文件的主体键（其余为元信息）
BODY_KEYS = {
    "yuexiu": ["groups", "direct_feed"],
    "haizhu": ["groups", "prim_group", "direct_feed", "plan_classes"],
    "tianhe": ["gongban", "qiye", "minban"],
    "huangpu": ["paiwei_groups", "zhisheng_groups"],
}


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(DATA_DIR, f"{name}_juniors.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.DATA


def validate(dk, body, meta):
    """转录完整性校验（防数据源文件被误改/漏改）。"""
    if dk == "yuexiu":
        for g in body["groups"]:
            assert g["group"] in ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一"], g
            assert len(g["juniors"]) == 10 and len(g["primaries"]) >= 3, g
    if dk == "haizhu":
        assert len(body["groups"]) == 10 and len(body["prim_group"]) == 71 and len(body["plan_classes"]) == 28
    if dk == "tianhe":
        assert len(body["gongban"]) == 24 and len(body["qiye"]) == 3 and len(body["minban"]) == 24
        for r in body["gongban"]:
            assert r["school"] and r["plan_classes"] is not None
    if dk == "huangpu":
        assert len(body["paiwei_groups"]) == 7 and len(body["zhisheng_groups"]) == 22


def main():
    os.makedirs(OUT, exist_ok=True)
    for dk, meta in META.items():
        body = load(dk)
        validate(dk, body, meta)
        out = {"year": 2026, "district": DISTRICT[dk], **meta, **body}
        path = os.path.join(OUT, f"{dk}_2026_juniors.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"✓ {dk}_2026_juniors.json（校验通过）")


if __name__ == "__main__":
    sys.exit(main())
