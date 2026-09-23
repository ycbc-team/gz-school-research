# 小升初（xiaoshengchu）升学路线业务数据

> 更新：2026-09-21（数据归位 `data/primary/transition/`，按 `raw / parsed / src / scripts / dist / docs` 规整，业务级 README）。
> 目的：记录广州 7 区全量小学构建 xiaoshengchu 的官方数据源、解析产物与已知缺口。
> 构建规则见 `data/linkage/README.md` 第五节"xiaoshengchu 数据约束规则"。

## 目录结构

| 目录 | 内容 |
| --- | --- |
| `raw/` | **仅政府官方原文件**（xlsx/pdf/docx/png/xls），不混入任何转录产物 |
| `parsed/_transcripts/` | A 层转录产物：各区官方文件的 Read 直读/Vision OCR/脚本解析 json（`<区>_2026*.json` + `haizhu_zone_reference.json` 参照），全部由 `scripts/` 下脚本复现 |
| `parsed/` | B 层解析唯一真源 `2026-<区>.json`（小学招生/地段表，供构建消费） |
| `src/` | 手工维护源文件（`_anchors.json` 官方校名→school_id 锚点；初中录取备注 `middle_enroll_notes.json` 已于 2026-09-23 迁 `data/middle/enrollment/src/`） |
| `scripts/` | 生产脚本：解析（build_district_enrollment/build_baiyun_2026/build_huangpu）、构建（build_xiaoshengchu_all + xs_resolver）、升级（upgrade_xiaoshengchu.mjs）、回填（backfill_xiaoshengchu_missing）、快照（build/check_middle_feed_snapshot） |
| `dist/` | 最终运行时产物：`xiaoshengchu_<区>.json`、`xiaoshengchu_all.json`、`xiaoshengchu_2026.json`、`middle_feed_snapshot.json`、`schools-backfill.json` |
| `docs/` | 业务文档（`xiaoshengchu_unmatched_fix_20260914.md`、`对口初中名匹配缺口清单.md`） |

## 构建链路

数据链路（A/B/C/D 四层，全程可重跑）：
- **A 层（raw 原文件 → parsed/_transcripts/*.json）**：复现脚本见下表，均用 `git show HEAD:data/primary/transition/raw/<名>.json` 导出迁移前基线做全量对比（0 真差异或仅修复旧版错漏）
- **B 层（transcripts → parsed/2026-<区>.json）**：build_district_enrollment.py / build_baiyun_2026.py / build_huangpu.py / build_middle_enrollment.py
- **C 层（parsed → dist/xiaoshengchu_<区>.json + xiaoshengchu_all.json）**：build_xiaoshengchu_all.py（+ xs_resolver）
- **D 层（→ dist/xiaoshengchu_2026.json 运行时真源）**：upgrade_xiaoshengchu.mjs

```bash
# A 层复现（按区，输出 parsed/_transcripts/）
python3 data/primary/transition/scripts/parse_yuexiu_diduan.py    # 越秀 51 校（doc→txt→json，补 4 校）
python3 data/primary/transition/scripts/parse_haizhu_diduan.py    # 海珠 78 校（png Vision OCR+POI+参照）
python3 data/primary/transition/scripts/build_huangpu.py --transcript  # 见下
# 白云/荔湾初中转录（baiyun_2026_juniors / liwan_2026_groups）已随初中招生业务迁出：
python3 data/middle/enrollment/scripts/parse_baiyun_juniors.py    # 白云 59 初中（读共享官方 xlsx）
python3 data/middle/enrollment/scripts/parse_liwan_groups.py      # 荔湾派位组 15 行（docx→json，全等）
python3 data/primary/transition/scripts/parse_panyu_official.py   # 番禺 4 sheets（xls→json，0 真差异；初中 sheet 归 middle/enrollment 消费）
# 天河/黄埔：Read 直读官网 PDF → scripts/read_transcripts/*.py → 生成 json（见下表）
python3 data/primary/transition/scripts/build_district_enrollment.py <区>   # B 层：transcripts → parsed/2026-<区>.json
python3 data/primary/transition/scripts/build_xiaoshengchu_all.py all_done  # C 层
node    data/primary/transition/scripts/upgrade_xiaoshengchu.mjs           # D 层
```

check 链（`data/registry/group/scripts/check_groups_drift.py` 的 `_check_xiaoshengchu`）自动重跑
build + upgrade 并与入库比对，防脚本改动未重跑产物/产物被手改。

## A 层转录复现清单（raw → parsed/_transcripts）

| 区 | raw 原文件 | 转录 json | 复现方式 | 与旧版基线对比 |
|---|---|---|---|---|
| 白云 | baiyun_2026_official.xlsx | baiyun_2026_juniors.json（初中，已迁 `data/middle/enrollment/parsed/_transcripts/`） | parse_baiyun_juniors.py（openpyxl 读「公办初中」sheet，脚本已迁 `data/middle/enrollment/scripts/`） | 59 条，1 处真差异=修复（seq4 三元里中学 plan ''→'0'，官方写 0 且注"涉拆迁停招"） |
| 荔湾 | liwan_2026_groups_official.docx | liwan_2026_groups.json（初中派位组，已迁 `data/middle/enrollment/parsed/_transcripts/`） | parse_liwan_groups.py（python-docx 按行读派位分组表，脚本已迁 `data/middle/enrollment/scripts/`） | 15 行全等 |
| 番禺 | panyu_2026_official.xls | panyu_2026_official.json | parse_panyu_official.py（xlrd 读 4 sheets） | 0 真差异（仅格式 8.0→8） |
| 越秀 | yuexiu_2026_official.doc | yuexiu_2026.json | parse_yuexiu_diduan.py（textutil 转 txt → 按块切 51 校） | 修复旧版 4 所校地段/班数全缺失（八一实验小学部 6、桂花岗 4、七中实验小学部 3、知用小学部 5） |
| 海珠 | haizhu_2026_official.png | haizhu_2026.json | parse_haizhu_diduan.py（macOS Vision OCR + POI 校名校正 + 参照融合 78 条 zone） | 79→78：基道→基立道修复、补星悦小学、校区拆开；zone 仅 2 校细节差异（以原图直读为准） |
| 天河 | tianhe_2026_official.pdf（附件5 第35-42页） | tianhe_2026.json | Read 多模态直读官网 PDF → scripts/read_transcripts/tianhe_2026_part{1,2}.py → 生成 | 76 条全对齐，修复 4 处旧版校名错漏（华阳天河东校区/棠德南/华颖外国语/南国学校/均和小学） |
| 黄埔 | huangpu_2026_official.pdf（附件4 第19-26页+附件6 第30-35页） | huangpu_2026.json | Read 多模态直读 → scripts/read_transcripts/huangpu_2026_{zone,plan}.py → 合并 | 95 条全对齐，修复旧版 2 处 plan（开元学校补 12、九龙二 7 含大坦校区） |

> 交叉验证方法（用户指定，2026-09-21 确立）：Read 直读官网图片/PDF 页（多模态）为主源，
> 与 macOS Vision OCR（scripts/ocr/vision_ocr.py）、POI 实体名（data/poi/dist/primary_poi.json）三方互证；
> 校名以官方原图/原 PDF 直读为准，POI 佐证错字但 POI 缺失时保留官方名。
> 天河/黄埔 PDF 均为无文字层扫描件（pdftotext 全页产物仅 66/46 字节），必须走 Read 直读/Vision OCR。

check 链（`data/registry/group/scripts/check_groups_drift.py` 的 `_check_xiaoshengchu`）自动重跑
build + upgrade 并与入库比对，防脚本改动未重跑产物/产物被手改。

## 就绪状态总览（构建完成）

| 区 | 官方数据源（2026） | 解析产物（本次保留） | 机制 | 覆盖 POI | 官方有而 POI 缺失 |
|---|---|---|---|---|---|
| 越秀 | 2026 细则 post_10790590 + 2022 分组表 post_8301356 | `parsed/_transcripts/yuexiu_2026.json`（2022 表，51 校） | 11 组电脑派位（每组 10 初中） | 74 | 桂花岗小学（高德两轮未命中，待核） |
| 荔湾 | 2026 公办初中招生方案 post_10791678 附件3 | `raw/liwan_2026_a3.docx` → `parsed/_transcripts/liwan_2026_groups.json`（15 行派位分组） | 14 组电脑派位 | 72 | 无（协和/如意坊/沙涌/双桥/花地湾已补全或映射） |
| 海珠 | 2026 初中招生问答 mpost_10799155 附件1 + 计划表 mpost_10788494 | HZ_GROUPS（10 组）/HZ_DIRECT（14 条）固化于脚本 | 10 组电脑派位 + 部分对口直升 | 97 | 大塘小学、北山小学（高德两轮未命中，待核） |
| 天河 | 2026 招生细则 PDF（附件6 初中划片 22 所 + 附件7 企事业办 + 附件8 民办 + 附件10 电脑派位 8 校） | `raw/tianhe_2026_official.pdf`（66 页扫描件，附件5 第35-42页 Read 直读转录） | 单校划片对口直升 + 九年制直升 + 附件10 自主报名电脑派位 | 104 | 无（汇景/华颖/猎德/奥中智谷已补全） |
| 白云 | 2026 招生计划 post_10791741 附表2 公办初中 | `raw/baiyun_2026_official.xlsx` → `parsed/_transcripts/baiyun_2026_juniors.json`（59 初中） | 单校划片为主 + 多校分片/摇号 | 164 | 花城实验学校、江高镇中心小学、星悦实验学校小学部（高德两轮未命中，待核） |
| 黄埔 | 2026 招生细则 PDF 附件5（电脑派位 7 组 + 对口直升 22 组） | `raw/huangpu_2026_official.pdf`（46 页扫描件，附件4/附件6 Read 直读转录） | 多校划片电脑派位 7 组 + 对口直升 22 组并行 | 93 | 铁铮学校（2026 新校）、九龙第一小学、凤尾小学（高德两轮未命中，待核）；沙步小学/知识城南暂定名（2026 口径跳过） |
| 番禺 | 2026《招生计划、招生地段及条件》官方 xls | `raw/panyu_2026_official.xls` → `parsed/_transcripts/panyu_2026_official.json`（小学地段 160 行/初中 62 行/民办 44 行/电话 12 行） | 逐校地段↔初中范围人工判定 + 市桥城区电脑派位 | 153 | 化龙镇中心小学、石碁镇永善小学、新桥小学（高德两轮未命中，待核） |

合计 954 条记录（schools-gz 960 所中的小学类 POI，含校区拆分与民办/特教/待核条目；L3 南沙/增城/花都/从化明确不做）。

## POI 高德补全（2026-09-10，backfill_xiaoshengchu_missing.py）

官方 2026 文件有、POI 库无 46 所的处理：
- **高德新增 17 所**：exact 命中（八一实验南校区/知用/七中实验/一中双桥/广外实验陈田西/庆丰/平沙培英/广铁八小/执信琶洲/华颖/猎德/华峰/华南师大黄埔实验南校区/广大附中西校区/广外科学城/广外黄埔/广大附中高新区南校区）。
- **中学层复用 12 所**：九年制/完中同法人坐标复用（协和小学部/省实花地湾小学部/白云中学棠景小学部/云湖实验小学部/广外实验小学部/新和小学部/番禺中学实验/绿翠小学部/汇景小学部/奥中智谷小学部/开元东校区小学部/颐和实验小学）。
- **映射建议 5 所**：不新增 POI，MAP 映射到既有 POI（如意坊校区→西关培正小学、沙涌校区→芳村小学、长岭居西校区→长岭居小学、颐和实验小学→POI 与中学层一致、凤尾小学→高德仅"凤尾学校"不映射）。
- **跳过 2 所**：沙步小学（2026 并入铁铮学校，无独立招生）、知识城南安置区二期小学（2026 新校暂定名）。
- **待核 9 所**：桂花岗小学、花城实验学校、江高镇中心小学、星悦实验学校小学部、化龙镇中心小学、石碁镇永善小学、大塘小学、北山小学、铁铮学校、九龙第一小学（高德两轮+变体未命中，多为新校/更名/撤并；北山/新桥/凤尾高德仅有"XX学校"更名猜测，未自动写盘）。

教训（已固化脚本）：① norm() 去括号会把"(公交站)"等后缀删掉导致排除词失效，非学校实体判断必须查原始名（化龙镇中心小学曾误配公交站，已清理）；② 更名猜测（学校↔小学）不再自动写盘；③ 新 POI 的 adcode 必须为字符串与历史数据一致（曾写 int 导致构建过滤）。

## 各文件来源 URL

- 越秀细则：https://www.yuexiu.gov.cn/gzjg/qzf/qjyj/jyzl/gk/jyjwj/content/post_10790590.html
- 越秀 2022 分组表（2026 结构基准）：http://www.yuexiu.gov.cn/gzjg/qzf/qjyj/jyzl/gk/zswd/content/post_8301356.html
- 荔湾方案：https://www.lw.gov.cn/zwgkk/zdlyxxgk/jyxx/czjy/content/post_10791678.html（附件 docx 8015557）
- 海珠问答：https://www.haizhu.gov.cn/gzhzjy/gkmlpt/content/10/10799/mpost_10799155.html；海珠初中计划表：https://www.haizhu.gov.cn/bmml/jyj/content/mpost_10788494.html
- 天河细则 PDF：http://www.thnet.gov.cn/attachment/8/8016/8016210/10791180.pdf
- 白云计划：https://www.by.gov.cn/zwfw/zdfw/xwsq/zcwj/content/post_10791741.html（附件 xlsx 8015798）
- 黄埔细则 PDF：http://www.hp.gov.cn/attachment/8/8016/8016631/10791836.pdf
- 番禺招生计划及地段：https://www.panyu.gov.cn/jgzy/qzfbm/fzqjyj/jyjgkml/qt/tzgg/content/post_10794082.html（附件 xls 8018386）

## 已保留解析产物（勿删）

`raw/` 下：liwan_2026_a3.docx、liwan_2026_a1/a2/a4/a5.docx、baiyun_2026_official.xlsx（小学+初中共享，权威源已归 `data/primary/enrollment/raw/`）、panyu_2026_official.xls、tianhe_2026_official.pdf、huangpu_2026_official.pdf。
另：初中专属转录/官方源（baiyun_2026_juniors.json、liwan_2026_groups.json、liwan_2026_groups_official.docx）已随初中招生业务迁 `data/middle/enrollment/`（2026-09-23）。
另有历史小学地段产物 `parsed/2026-tianhe.json`、`parsed/2026-huangpu.json`（仅小学地段表，初中无历史产物，本次已重新解析）。

## 已知缺口（待核清单）

1. 天河"天河智慧城第一小学"：2026 官方划片表未单列对口初中（2022 年开办、2026 年首届毕业生），可自主报名附件10 电脑派位，待区教育局补充。
2. 黄埔"凤尾学校"POI vs 官方"凤尾小学"：名称不一致（更名猜测未自动写盘），待核是否同校。
3. 黄埔 POI"华中师范大学黄埔实验学校"：2026-09 新启用公办十二年制，未在 4 月细则单列，首届 2026 年 9 月入学（暂无小升初）。
4. 黄埔 POI"玉岩中学附属开发区实验学校/广州市玉岩中学附属科学城实验学校/黄埔实验学校小学部/黄埔海地实验学校/福洞小学/佛塱学校/西村小学/埔心学校/黄埔利民艺体实验学校/嘉洲小学"：官方 2026 文件未单列，待核（疑似撤并/停招/更名/民办）。
5. 天河 POI"志才小学"：官方 2026 民办名单未单列，待核。
6. 天河/黄埔部分新校（知识城第二小学、萝峰小学东校区、沙步并入铁铮学校等）已按官方 2026 口径处理，注释见脚本。

## 与 tier1 口碑学校交集验证（2026-09-10）

tier1 59 所全部可定位到 xiaoshengchu 记录（52 所直接命中；协和学校小学部（POI 已补全，直升不派位，tier1 保留原值）、民航学校/南阳里/怡园/东荟花园为别名或全角括号差异、沙步小学官方已并入铁铮学校）。
