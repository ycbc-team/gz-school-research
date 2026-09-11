import Foundation
import Vision
import ImageIO
import AppKit

// 用法: swift ocr_vision.swift <image> <out.json> [minConf]
// 输出 OCR 文本框（左上原点像素坐标）。用 CGImageSource 加载，避免 NSImage 对灰度/大图不稳定。
let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("usage: swift ocr_vision.swift image out.json [minConf]\n".data(using: .utf8)!)
    exit(1)
}
let inURL = URL(fileURLWithPath: args[1])
guard let data = try? Data(contentsOf: inURL),
      let src = CGImageSourceCreateWithData(data as CFData, nil),
      let cg = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
    FileHandle.standardError.write("load image failed\n".data(using: .utf8)!)
    exit(1)
}
let minConf = args.count >= 4 ? Double(args[3]) ?? 0.3 : 0.3

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
request.recognitionLanguages = ["zh-Hans", "en-US"]
let handler = VNImageRequestHandler(cgImage: cg, options: [:])
do { try handler.perform([request]) } catch {
    FileHandle.standardError.write("perform failed: \(error)\n".data(using: .utf8)!)
    exit(1)
}

struct Item: Codable { var x0: Double; var y0: Double; var x1: Double; var y1: Double; var text: String; var conf: Double }
var items: [Item] = []
let H = Double(cg.height); let W = Double(cg.width)
if let results = request.results {
    for obs in results {
        guard let cand = obs.topCandidates(1).first, Float(cand.confidence) >= Float(minConf) else { continue }
        let bb = obs.boundingBox
        items.append(Item(
            x0: bb.origin.x * W,
            y0: (1 - bb.origin.y - bb.height) * H,
            x1: (bb.origin.x + bb.width) * W,
            y1: (1 - bb.origin.y) * H,
            text: cand.string, conf: Double(cand.confidence)))
    }
}
let data = try JSONEncoder().encode(items)
try data.write(to: URL(fileURLWithPath: args[2]))
print("items: \(items.count)")
