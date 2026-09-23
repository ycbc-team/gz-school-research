# 文明校园称号采集（data/civilized_campuses/）

全国、广东省、广州市文明校园及其创建培育名单的原始资料与后续解析产物。
本目录独立于 `specialty_schools`：文明校园是覆盖立德树人、师德、校园文化、环境与治理的
综合荣誉，不归入单项特色学校称号。

## 当前阶段：原始资料优先，正式名单试解析

本阶段先将所有可获得的原件及其来源说明落入 `raw/`。候选、公示、推荐等**只留 raw，不进入
parsed**；已确认的正式名单可做最小化原文摘录，以观察不同届次、不同级别实际提供的字段。
“创建广州市文明校园先进学校”是独立的创建储备称号：可收录原文，但不得写作正式“广州市文明
校园”。最终真源格式仍待后续各专项资料补齐；全国名单已先生成候选 dist 供运行时试用。

首轮已落盘：全国第一至三届正式名单、第一届广东省正式名单，以及第二届广东省候选/往届复查
公示、广州“创建文明校园先进学校”名单。广东候选/复查公示仅作来源留底，必须待取得对应的
最终表彰或复查确认文件后才可进入解析范围；广州先进学校名单是已测评确定的独立创建储备称号，
后续可单列解析，但不与市级正式文明校园混合。

已对全国三届名单完成第一轮原文摘录：`parsed/national_civilized_campuses.json` 共有 115 条
广东省原文记录（第一届 30、第二届 37、第三届 48）。这只是为观察名单能够稳定提供的字段，
未筛选广州、未判断学段或校区归属，也未声明称号当前仍有效。

广州已完整落地的名单为：第二届“广州市文明校园”49 所，以及 2021—2023 年创建广州市文明
校园先进学校 63 所，见 `parsed/guangzhou_civilized_campuses.json`。前者与后者分别编译为两个
纯 `school_id` 的 dist 文件，并由 `test/test_guangzhou_build.py` 固定匹配审阅快照。第一届市级正式
名单目前仅有“65 所”的数量口径，尚未取得完整名单，故不以 65 或 115 凑造记录。

首批范围：

1. 第一至第三届全国文明校园正式名单（中国文明网）；
2. 广东省文明校园的正式表彰/复查名单；
3. 广州市文明校园及“创建广州市文明校园先进学校”等名单（后者须与正式认定明确区分）。

### 称号层级与采集顺序

面向项目中小学，按下列层级分别采集；上级评选通常从下级创建成果中择优推荐，但**不是自动晋级**，
也不能仅凭下级称号推断拥有上级称号。

普通学校
→ 创建广州市文明校园先进学校（创建储备，2021—2023 年已确定 63 所）
→ 广州市文明校园（市级正式荣誉）
→ 广东省文明校园（省级正式荣誉）
→ 全国文明校园（国家级正式荣誉）

广州正式荣誉已查到两届公开口径：第一届 65 所、第二届 49 所，因此目前可验证的合计是 **114 所**，
不是 115 所。第一届完整原始名单和第二届发布原件尚待补存；在找到“补命名/勘误/第三批”等权威
材料前，不把 115 所作为断言或目标数量。采集优先级为：先收齐两届市级正式名单并逐项匹配，再收集
广东省各届正式命名与复查确认名单，最后再单列 63 所先进学校。

## 目录约定（先建分层，不代表已有数据）

| 目录 | 当前用途 |
| --- | --- |
| `raw/` | 原始网页、附件、下载记录与来源索引；正式与非正式来源均保留 |
| `parsed/` | 正式名单的最小化原文摘录；当前仅有全国三届试解析产物，尚非最终真源格式 |
| `src/` | 人工校对、别名或补充真源；当前含全国名单的审阅黑名单 |
| `scripts/` | 下载、解析、构建脚本；当前含全国正式名单的试解析与 dist 编译脚本 |
| `dist/` | 运行时编译产物；当前为全国文明校园 `school_id` 索引 |
| `test/` | 解析和完整性断言；当前校验 dist 的匹配结果和列表形状 |

## 原始资料判定规则

- 优先保存签发/发布机关的正式“决定、公布、表彰、复查确认”页及附件；公示、推荐单独留存，
  不能写作正式文明校园。“创建先进学校”即使已测评确定，也仅写作该独立称号，不能写作正式
  文明校园。
- 每个原件必须有来源 URL、抓取日期和文件说明，放在同目录 `SOURCES.md`。
- 全国文明校园每届期满需复查；后续设计数据时必须能表达届次与“新命名/复查保留/撤销或未知”，
  不能把历史名单直接当作永久有效状态。
- 名单出现校区、部别或集团时保留原文，待解析阶段再通过 `SchoolMatcher` 判定可否关联学校实体。

### 学部/校区归属限制（全国名单已核实）

全国三届页面均按“省份 → 学校名称”发布，不提供独立的学段、校区、法人或统一信用代码字段。
第三届个别学校在名称内写明“校本部”“高中部”等，第一、二届和绝大多数第三届记录没有这类
信息。因此，完全中学、九年一贯制学校和教育集团不得因项目 POI 有小学/初中/高中多个实体，
就把称号自动复制到每个学部。

- 原文明确校区或部别：保留原文范围，后续仅尝试匹配该范围对应实体；
- 原文仅为学校名：先视为“学校层级、学部未指明”，保留在组织层待人工或更细颗粒度官方文件
  核实；不挂接具体小学/初中/高中 `school_id`；
- 无论何种情况，名称括号、校区和部别都必须原样保留，不可在解析期抹平。

## 当前脚本

```bash
# 全国三届正式名单：提取广东省原文段；先执行数量断言，再写 parsed
python3 data/civilized_campuses/scripts/parse_national.py --check
python3 data/civilized_campuses/scripts/parse_national.py

# 全国正式名单 parsed → 运行时 school_id 索引；先校验，后写 dist
python3 data/civilized_campuses/scripts/build_dist.py --check
python3 data/civilized_campuses/scripts/build_dist.py
# 输出供人工核验的「官方原文名 → SchoolMatcher 实体名 → school_id 列表」
python3 data/civilized_campuses/scripts/build_dist.py --review
# 将同一审阅结果写入 test 产物（测试命令也会自动执行此步）
python3 data/civilized_campuses/scripts/build_dist.py --review-output data/civilized_campuses/test/national_civilized_campus_match_review.json
python3 data/civilized_campuses/test/test_build_dist.py
```

脚本不依赖第三方 Python 包，并对三届广东省段分别断言 30、37、48 条。顿号出现在括号内的
校区/部别表达不会被拆成多所学校。

`dist/civilized_campus_school_ids.json` 是统一运行时产物：键为 `national`、`provincial`、`municipal`
和 `advanced`，每个值均为**只含 `school_id` 的字符串数组**。称号、届次、原文校名和来源均留在
parsed；省级当前仅解析第一届正式名单（61 条原文），后续届次待取得最终表彰或复查文件后追加。
构建时不传学段：原文明确校区/部别时仅命中该范围；未明确校区时由 `SchoolMatcher` 展开全部
可命中的同法人校区。构建不维护人工“广州范围”表，而是将 parsed 的全部官方转录名送入
`SchoolMatcher`；`--review` 与测试命令输出逐项 `{src_name, entity_name, schoolid}`，供人工检查
跨市同名误匹配及需清洗的原文名。未经该审阅确认前，dist 只是候选运行时索引。

已审阅确认的非项目学校不改写 `raw` 或 `parsed`，而写入
`src/national_civilized_campuses_blacklist.json`：支持精确原文名及名称前缀规则。当前排除华南
理工大学、深圳大学和所有以“深圳市”开头的原文名；每次构建和测试都会应用并校验该规则。

审阅输出中每个对象都严格为：

```json
{"src_name": "官方文档转录名", "entity_name": "SchoolMatcher 实体名或 null", "schoolid": ["gz-..."]}
```

同一官方名命中多个实体（例如未写校区而被展开）时会拆成多行；这样每个 `entity_name` 与
`schoolid` 的对应关系可单独核验。

广州两类名单的审阅快照分别为 `test/guangzhou_civilized_campuses_formal_match_review.json`（第二届
市级正式）和 `test/guangzhou_civilized_campuses_advanced_match_review.json`（创建先进学校），不得
合并为同一快照。

## 已知官方入口

- [全国文明校园名单总入口](https://www.wenming.cn/wmsjk/cjdx_53740/qgwmxymd/)（第一、二、三届）；
- [第三届全国文明校园名单](https://www.wenming.cn/wmzthc/20250522/49dda5aa663948a9830ba2e7b9890e0b/c.html)；
- [广东文明网公告](https://gd.wenming.cn/announcement/index_3.shtml)（含省级候选及往届复查公告索引）；
- [广州文明网·文明校园](https://gdgz.wenming.cn/2020index/wmcj/cjhd/index_2.html)。
