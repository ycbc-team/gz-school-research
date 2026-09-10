# 升学通道数据（data/linkage）— 采集进度与技术复盘

> 目标：为"高中→初中→小学"升学链路模型（Q_j 升学通道指数）收集官方数据。
> 范围：特控率高的省市属学校（levels.json 11 所，21 个校区）。
> 冲突规避：本目录全部为新建，未触碰 `data/primary|middle|high/`、`apps/`（另一 agent 在做 vue 重构）、`data/combined.js`。

---

## 一、已完成并落盘

| 文件 | 内容 | 状态 |
|---|---|---|
| `batch2_scores.json` | 2026 第二批次（名额分配）录取分数：**省市属 20 校区 × 463 所初中**，字段 admitted / min_score / last_score | ✅ 官方文本层正常，可靠 |
| `raw/batch2_scores.pdf` | 第二批次录取分数原表（304 页） | ✅ 留痕 |
| `raw/batch2_scores_all.json` | 7280 行全量解析（含区属/民办） | ✅ 留痕 |
| `raw/quota_detail.pdf` | 2026 名额分配结果（全市 31 页，每区 2-5 页） | ✅ 已攻克（见下） |
| **`quota_matrix.json`** | **2026 名额分配完整矩阵：498 所初中 ×（名额考生/省市属/区属 + 21 省市属校区 n_ji）** | ✅ **校验 0 不一致（col1=Σ21 全过）** |
| `raw/quota_grid_final.json` | 全量网格原始数据（每页 rows/cols/data） | ✅ 留痕 |
| `scripts/linkage/assemble_quota.py` | grid → matrix 组装脚本 | ✅ 可复现 |
| `scripts/linkage/parse_batch2.py` / `scripts/linkage/build_linkage_batch2.py` | 第二批次解析与省市属过滤脚本 | ✅ 可复现 |
| `raw/headers/header_ocr.json` + 各页表头图 | 7 区第 1 页表头列序（Read 视觉确认） | ✅ 列序可信 |

## 二、核心障碍（已攻克）：名额分配明细 PDF 的 CID 字体

`quota_detail.pdf`（31 页，含每所初中的"名额考生 / 省市属名额 / 区属名额 / 各高中指标数 n_ji"矩阵）：
- 文本层：**CID 无 ToUnicode 映射**，pdfplumber / pdfminer / pymupdf `get_text` 均返回乱码。
- 渲染层：**pymupdf、pypdfium2（Chrome 同款引擎）、macOS PDFKit 渲染的字形全部错乱**（数字"595"渲染成"6417"类错误字形）。
- **攻克路径**：`pdftoppm -r 300`（poppler）渲染 300dpi 位图 → cv2 检测列线/行界 → 单格裁剪 → tesseract 逐格 OCR（psm10 + 数字白名单）→ 以 **col1（省市属名额）= Σ21 校区列** 强校验，不一致行用"渲染拼图 + Read 视觉 OCR 读真值 + 硬编码回写"逐轮收敛：377 → 65 → 48 → 5 → 1 → **0 不一致（498 校全过）**。
- 关键陷阱：页 25 存在前导列线多检（cols 偏移 +1）、col1 列窄易串列（视觉读真值更可靠）、区头行 21 列跨页不闭合（仅参考不参与校验）。

## 三、现有数据对模型的支持

用户模型：Q_j = Σ(名额分配 n_ji/m_j × H_i × α) + 自招通道 + 体育特长 + 艺术特长

| 模型输入 | 现状 |
|---|---|
| H_i（高中特控率） | ✅ 已有（KEY_FACTS，11 所 2025/2026 网传+官方口径） |
| 上岸分数（初中×高中） | ✅ `batch2_scores.json` 完整（20 校区×463 初中） |
| m_j（名额考生数） | ✅ `quota_matrix.json`（498 校全量） |
| n_ji（指标数） | ✅ `quota_matrix.json`（21 省市属校区 × 498 校） |
| 自招/特长名单 | ⏳ 未采集（附件链接已定位，特长生 post_10830310 两个附件） |

## 四、可选路径（需用户拍板）

1. **A. 官方 Excel/CSV 版**：招考办当前只发布 PDF；如后续发布表格版（中考服务平台导出版），可秒级解析。等待或用户提供。
2. **B. 逐页 Read 转录**：31 页 × 每页 ~480 数字，由我逐页 Read 后转录为 JSON。单窗口上下文不够一次完成，可分 3-4 轮会话做；工作量约 1-2 小时，准确率接近 100%。
3. **C. 先用上岸分数构建 Q_j v0（推荐）**：`batch2_scores.json` 已含"初中 j 在高中 i 是否有第二批次上岸 + 最低分"，可先以
   Q_j = Σ_i [I(j→i 上岸) × f(min_score) × H_i]
   落地一版（不依赖指标数），指标矩阵后续补齐再替换。
4. **D. 只补 m_j 与"省市属名额"两列**：这两列在每页左侧（名额考生 / 省市名额 / 区属名额），Read 转录量减到每行 3 个数字（31 页 ≈ 1500 数字），比全矩阵少 10 倍。

## 五、冲突红线（延续）

- 不写 `data/primary/`、`data/middle/`、`data/high/`、`apps/`、`data/combined.js`。
- 新产出只进 `data/linkage/` 与 `scripts/`（脚本均为独立新建）。
