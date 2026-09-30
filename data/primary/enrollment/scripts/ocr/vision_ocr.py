#!/usr/bin/env python3
"""macOS Vision OCR 工具：图片 → 文本+归一化坐标行。

用法: python3 vision_ocr.py <img_path> [--json out.json]
依赖: pip3 install pyobjc-framework-Vision pyobjc-framework-Quartz
返回: 每行 {"text", "x", "y", "w", "h"}（坐标 0-1 归一化，y 向下增大）
"""
import argparse
import json
import sys

from Foundation import NSURL


def ocr(path):
    import Quartz
    import Vision
    url = NSURL.fileURLWithPath_(path)
    src = Quartz.CGImageSourceCreateWithURL(url, None)
    if src is None:
        raise SystemExit(f"无法读取图片: {path}")
    cg = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    # 新版 macOS 默认 revision 可能仍是仅支持英文的 v1；显式选择支持
    # 简体中文的最高 revision，避免 setRecognitionLanguages_ 后静默失败。
    revisions = []
    for revision in Vision.VNRecognizeTextRequest.supportedRevisions():
        languages, error = (
            Vision.VNRecognizeTextRequest
            .supportedRecognitionLanguagesForTextRecognitionLevel_revision_error_(
                Vision.VNRequestTextRecognitionLevelAccurate, revision, None
            )
        )
        if error is None and "zh-Hans" in languages:
            revisions.append(revision)
    if not revisions:
        raise SystemExit("当前 macOS Vision 未提供支持 zh-Hans 的文字识别 revision")
    req.setRevision_(max(revisions))
    req.setRecognitionLanguages_(["zh-Hans", "en-US"])
    req.setUsesLanguageCorrection_(True)
    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg, None)
    ok, error = handler.performRequests_error_([req], None)
    if not ok:
        raise SystemExit(f"Vision OCR 执行失败: {error or '未知错误'}")
    out = []
    for o in req.results() or []:
        b = o.boundingBox()  # 归一化 (x, y, w, h)，原点左下
        txt = o.topCandidates_(1)[0].string()
        out.append({
            "text": txt,
            "x": b.origin.x,
            "y": 1.0 - b.origin.y - b.size.height,  # 转为左上原点
            "w": b.size.width,
            "h": b.size.height,
        })
    out.sort(key=lambda r: (round(r["y"], 3), r["x"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("img")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    lines = ocr(a.img)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(lines, f, ensure_ascii=False, indent=1)
    print(f"{len(lines)} 行 → {a.json or 'stdout'}", file=sys.stderr)
    for l in lines:
        print(f"{l['y']:.3f} {l['x']:.3f} {l['text']}")


if __name__ == "__main__":
    main()
