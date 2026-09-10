import Foundation
import Vision
import AppKit

// 用法: swift ocr_vision.swift <image.png> <out.json>
let args = CommandLine.arguments
guard args.count >= 3, let img = NSImage(contentsOfFile: args[1]) else {
    FileHandle.standardError.write("usage: swift ocr_vision.swift image.png out.json\n".data(using: .utf8)!)
    exit(1)
}
guard let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    FileHandle.standardError.write("no cgImage\n".data(using: .utf8)!)
    exit(1)
}
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
request.recognitionLanguages = ["zh-Hans", "en-US"]
let handler = VNImageRequestHandler(cgImage: cg, options: [:])
try handler.perform([request])

struct Item: Codable { var x0: Double; var y0: Double; var x1: Double; var y1: Double; var text: String; var conf: Double }
var items: [Item] = []
if let results = request.results {
    let H = Double(cg.height)
    for obs in results {
        guard let cand = obs.topCandidates(1).first else { continue }
        let bb = obs.boundingBox  // 归一化，原点左下
        // 转成图像坐标（左上原点）
        let x0 = bb.origin.x * Double(cg.width)
        let y0 = (1 - bb.origin.y - bb.height) * H
        let x1 = (bb.origin.x + bb.width) * Double(cg.width)
        let y1 = (1 - bb.origin.y) * H
        items.append(Item(x0: x0, y0: y0, x1: x1, y1: y1, text: cand.string, conf: Double(cand.confidence)))
    }
}
let enc = JSONEncoder()
enc.outputFormatting = [.sortedKeys]
let data = try enc.encode(items)
try data.write(to: URL(fileURLWithPath: args[2]))
print("items: \(items.count)")
