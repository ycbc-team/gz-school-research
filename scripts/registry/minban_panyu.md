# 番禺区（adcode=440113）民办中小学名单核实与实体匹配清单

> 生成时间：2026-09-14
> 数据基准：番禺区教育局《2025年度番禺区民办学校年检结论》（2026-07-22 公示，36 所民办中小学全部"合格"）；2025/2026 年广州市中考第四/三批次民办高中录取名单；2025 年番禺区积分制入学学位计划（标注"民办"）
> 实体表：`data/registry/entities.json`（番禺区共 312 条：primary 200 / middle 93 / high 19，255 个唯一 school_id）
> 现状：已标 `nature=民办` 共 68 行 / 41 个唯一 school_id。本次为查漏补缺，不重复确认已标校。

## 核心结论

- **义务教育阶段民办校 36 所**（番禺区教育局 2025 年度年检权威名单，与羊城晚报"番禺区 36 所民办小学"口径一致）。
- **民办高中 5 所**：南方学院番禺附属中学、衡美高级中学、星执学校、祈福英语实验学校、博萃德学校（2025 年首年招高一，为第 5 所，原仅统计 4 所）。
- **本次新增 nature 标记 8 行 / 7 个 school_id**，均为"官方名单确认民办、实体表已存在但当前未标"的跨学段/重复实体（4 所九年一贯制学校的中学部此前只标了小学部，另含 2 个重复实体 + 加拿达中学部）。
- **需补实体 2 处**：博萃德高中部（high stage）、剑桥郡加拿达外国语学校小学部（primary stage）。
- **重点排除**：华师附中番禺学校（华附番禺）已转公/公办；锦绣香江学校、市桥金山谷学校均为公办小区配套校；广州市香江中学实为增城区学校。

---

## 一、确认民办且实体表已存在（新增 nature 标记，即当前未标的）

| school_id | name | stage | 来源URL | 备注 |
|---|---|---|---|---|
| gz-440113-6426397c | 番禺区洛浦厦滘学校中学部 | middle | https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10911/mpost_10911898.html ；http://news.dayoo.com/gzrbrmt/202607/23/170639_54982964.htm | 年检名单第 6 所"洛浦厦滘学校"；同一校小学部 gz-440113-1b3be909 已标民办，中学部此前漏标。九年一贯制民办 |
| gz-440113-0670cc0e | 番禺区金华学校 | middle | https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10911/mpost_10911898.html ；http://www.panyu.gov.cn/attachment/7/7835/7835118/10323988.pdf | 年检名单第 9 所"金华学校"；积分入学计划明确标注"金华学校(民办)"。小学部 gz-440113-82bf431a 已标民办，中学部此前漏标 |
| gz-440113-62cbe194 | 大博学校 | middle | https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10911/mpost_10911898.html ；http://www.panyu.gov.cn/attachment/7/7835/7835118/10323988.pdf | 年检名单第 12 所"化龙镇大博学校"；积分入学计划标注"大博学校(民办)"。小学部 gz-440113-a6aa9fb0（化龙大博学校小学部）已标民办，中学部此前漏标；aliases 含"番禺区化龙镇大博学校" |
| gz-440113-db326e94 | 华南碧桂园学校(中学部) | middle | https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10911/mpost_10911898.html ；http://news.dayoo.com/gzrbrmt/202607/23/170639_54982964.htm | 年检名单第 21 所"华南碧桂园学校"；小学部 gz-440113-a45e4a1a 已标民办，中学部此前漏标 |
| gz-440113-7b2b848a | 加拿达外国语学校(剑桥郡校区) | middle | https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10911/mpost_10911898.html ；http://www.panyu.gov.cn/attachment/7/7836/7836414/10334887.pdf | 年检名单第 26 所"剑桥郡加拿达外国语学校"；积分入学补填计划标注"剑桥郡加拿达外国语学校（民办）"。aliases 含"番禺区剑桥郡加拿达外国语学校"。**此前完全未标**（新发现民办校）；注意与 gz-440113-611fa8ce 公办"番禺区剑桥郡小学"非同一所 |
| gz-440113-b33076d3 | 金海岸学校 | primary | http://www.panyu.gov.cn/jgzy/qzfbm/fzqjyj/jyjgkml/qt/tzgg/content/post_8334907.html ；https://www.peopleapp.com/rmharticle/30030176924 | **公办**（2026-09-18 更正）：番禺区教育局 2022 年批复开办的公办九年一贯制学校（42 班），石碁片区第一所公办九年一贯制；官方公办小学/初中招生 sheet 均有"金海岸学校"（地段/派位）。**与民办"金海岸实验学校"（gz-440113-d7e3e576）是两所不同学校，非同名简称，不得合并、不得标民办** |
| gz-440113-b33076d3 | 金海岸学校 | middle | http://www.panyu.gov.cn/jgzy/qzfbm/fzqjyj/jyjgkml/qt/tzgg/content/post_8334907.html | 公办（同上），middle 阶段行同判；官方公办初中 sheet 有"金海岸学校"（2 班，金海岸花园户籍派位） |
| gz-440113-cf01b95f | 广州博萃德学校小学部 | primary | https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10911/mpost_10911898.html ；https://jyj.gz.gov.cn/gk/zfxxgkml/bmwj/qtwj/content/post_10541662.html | 年检名单第 35 所"博萃德学校"；与已标 gz-440113-3d006240（primary,middle）为同校异名实体。市教育局 2025 年审批遗留问题通知确认其为九年一贯制民办。建议补标民办并后续与 3d006240 合并 |

> 说明：以上 8 行实体记录的 `nature` 字段当前为空（match_school.py 显示"公办(未标)"为缺省态），应统一补标为 `民办`。其中前 5 行为九年一贯制学校的中学部漏标；加拿达为全新发现的民办校；后 3 行为同校重复实体补标。

---

## 二、确认民办但实体表不存在（需先补实体再标记）

| 官方校名 | 学段 | 来源URL | 建议实体name | 备注 |
|---|---|---|---|---|
| 广州市番禺区博萃德学校（高中部） | high | https://jyj.gz.gov.cn/yw/jyyw/content/post_10271257.html ；https://ep.ycwb.com/epaper/xkb/html/2025-05/20/content_1503_707312.htm | 广州博萃德学校(高中部) | 2025 年首年招高一，48 个计划，为番禺区第 5 所民办高中；现有实体 gz-440113-3d006240 仅 primary+middle，需新增 high 阶段行（建议沿用同一 school_id 或续编新 id，aliases 含"博萃德学校高中部"） |
| 广州市番禺区剑桥郡加拿达外国语学校（小学部） | primary | http://www.panyu.gov.cn/attachment/7/7835/7835118/10334886.pdf ；http://www.panyu.gov.cn/attachment/7/7836/7836414/10334887.pdf | 番禺区剑桥郡加拿达外国语学校(小学部) | 积分入学计划列其小学一年级招生（民办），现有实体 gz-440113-7b2b848a 仅 middle，需补 primary 阶段实体（九年一贯制） |

---

## 三、待核实（性质不确定或名称无法匹配）

| 校名 | 来源URL | 待核实原因 |
|---|---|---|
| 广州市香江中学（gz-440113-30628a8d, middle，aliases：番禺区香江中学、香江中学） | http://gz.bendibao.com/edu/guojixuexiaolist/minban/ ；https://jyj.gz.gov.cn/gkmlpt/content/7/7789/post_7789142.html | 经核实，"广州市香江中学"为**增城区**老牌民办完中（市教育局 2021 年非营利性民办复函对象），校址在增城；番禺区年检 36 所名单中无此名。番禺区民办"香江"为已标的 gz-440113-ad8632f5 香江实验学校（原育才实验番禺香江校区）。此实体挂在番禺 adcode 下疑似**误植/历史别名**，暂不标民办，待 owner 确认是否清理 |
| 长颈马初中部（gz-440113-f76c8e69, middle） | https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10911/mpost_10911898.html | 不在番禺区 36 所民办中小学年检名单内，名称疑似培训机构/民间称呼，非全日制学历制学校，待核实是否应保留实体 |
| 吉毅教育初中部（gz-440113-74650d0c, middle） | https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10911/mpost_10911898.html | 同上，不在年检名单，名称含"教育"疑似培训机构/数据噪声，待核实 |

---

## 四、已排除（经查实为公办或已民转公）

| 校名 | 排除原因 | 来源URL |
|---|---|---|
| 华师附中番禺小学（gz-440113-de874f8a, primary） | 市教育局 2024 年义务教育标准化学校认定明确列为**公办**小学；著名"华师附中番禺学校"已在公参民治理中转公，不再是民办。**agent-hint 重点关注校，确认排除** | https://jyj.gz.gov.cn/gk/zfxxgkml/bmwj/qtwj/content/post_9798933.html |
| 番禺区锦绣香江学校（gz-440113-8a0b2cb9, primary+middle） | 官方明确为小区配套**公办九年一贯制**学校（非民办）；不在 36 所民办年检名单 | https://huacheng.gz-cmc.com/pages/2022/08/09/f3f889b287764bb1909d130ae117b452.html |
| 市桥金山谷学校（gz-440113-f890218e, primary+middle） | 招商金山谷小区配套**公办九年一贯制**学校，列入番禺区公办小学招生地段计划；不在 36 所民办名单 | https://www.shangnaxue.net/school/1392713346504998914.html ；https://m.gz.bendibao.com/edu/349872.html |
| 南雅学校（gz-440113-f4a10736, primary+middle） | 不在番禺区 36 所民办中小学年检名单内，按公办处理 | https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10911/mpost_10911898.html |
| 明德实验小学（gz-440113-bb3711d6, primary） | 不在 36 所民办名单；注意与已标民办 gz-440113-7997c707"明德广地实验学校"非同一所，此所为公办 | https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10911/mpost_10911898.html |
| 海鸥学校（gz-440113-cdfe162a, middle） | 石楼镇公办学校，不在 36 所民办名单 | https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10911/mpost_10911898.html |
| 番禺中学实验学校（gz-440113-95be9ccc, middle） | 广东番禺中学附属公办，不在 36 所民办名单 | https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10911/mpost_10911898.html |
| 广州市番禺区番雅实验学校（gz-440113-a5f31e18, middle） | 不在 36 所民办年检名单，按公办处理 | https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10911/mpost_10911898.html |
| 广州番禺区毓贤学校（gz-440113-7cdbe028, primary+middle）／祈福毓贤学校初中部（gz-440113-c07e3ddb, middle） | 祈福配套公办，不在 36 所民办名单 | https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10911/mpost_10911898.html |
| 番禺区剑桥郡小学（gz-440113-611fa8ce, primary） | 公办小学，与已确认民办"剑桥郡加拿达外国语学校"（gz-440113-7b2b848a）为同小区不同校，勿混淆 | http://www.panyu.gov.cn/attachment/7/7353/7353189/9051745.pdf |
| 仲元实验学校／石北中学系列／大石系列公办校（大石中学、石北中学、石碁中学等） | 均为区属公办完全中学，出现在高中招生公办批次，非民办 | http://gzzk.gz.gov.cn/zwgk/zwdt/content/post_10910342.html |

---

## 五、已标民办确认无遗漏（当前 41 所，官方名单中均有对应）

以下 41 个已标 `nature=民办` 的 school_id，经与番禺区 2025 年度年检 36 所民办中小学名单及中考民办高中名单逐一比对，**全部在官方名单中有对应，无需补标、无遗漏**：

| # | school_id | 名称 | stage | 官方对应 |
|---|---|---|---|---|
| 1 | gz-440113-000bd12e | 万翔学校 | primary,middle | 年检 #31 万翔学校 |
| 2 | gz-440113-0b94ed9c | 广州执鸿学校 | primary | 年检 #36 执鸿学校（九年一贯制） |
| 3 | gz-440113-166b5b5c | 新君豪中英文学校 | primary,middle | 年检 #19 |
| 4 | gz-440113-1963cc5e | 祈福新邨学校 | primary | 年检 #27 祈福新邨学校 |
| 5 | gz-440113-1b3be909 | 厦滘学校(小学部) | primary | 年检 #6 洛浦厦滘学校 |
| 6 | gz-440113-23835acf | 华阳学校 | primary,middle | 年检 #11 沙湾华阳学校 |
| 7 | gz-440113-28a853f8 | 新英才中英文学校 | primary,middle | 年检 #32 |
| 8 | gz-440113-2a299f65 | 番禺名智小学 | primary | 年检 #30 名智小学 |
| 9 | gz-440113-2b7d85fc | 嘉诚学校 | primary,middle | 年检 #20 |
| 10 | gz-440113-2ca37b61 | 大山学校 | primary,middle | 年检 #16 大石大山学校 |
| 11 | gz-440113-337c0524 | 广州南方学院番禺附属中学 | primary,middle,high | 年检 #25 附属小学 + 民办高中录取名单 |
| 12 | gz-440113-39879bc6 | 番禺鸿翔学校 | primary,middle | 年检 #34 鸿翔学校 |
| 13 | gz-440113-3b338135 | 天星学校 | primary,middle | 年检 #10 |
| 14 | gz-440113-3b63e590 | 广州番外外国语学校 | primary,middle | 年检 #1 番外外国语学校 |
| 15 | gz-440113-3cc636b8 | 诺德安达学校 | primary,middle | 年检 #7 |
| 16 | gz-440113-3d006240 | 广州博萃德学校 | primary,middle | 年检 #35 博萃德学校 |
| 17 | gz-440113-6bf19a4c | 广州南方学院番禺附属小学 | primary | 年检 #25 |
| 18 | gz-440113-70ea7542 | 大岭学校 | primary,middle | 年检 #24 |
| 19 | gz-440113-757ae826 | 新英豪中英文学校 | primary,middle | 年检 #13 |
| 20 | gz-440113-7997c707 | 明德广地实验学校 | primary,middle | 年检 #23 |
| 21 | gz-440113-7b27f226 | 金星学校 | primary | 年检 #14 |
| 22 | gz-440113-827f636b | 广博学校 | primary,middle | 年检 #29 |
| 23 | gz-440113-82bf431a | 金华学校 | primary | 年检 #9 |
| 24 | gz-440113-86cfc8c7 | 广州市衡美高级中学 | high | 民办高中录取名单（2025 公费班） |
| 25 | gz-440113-89b309cd | 番禺同心小学 | primary | 年检 #28 同心小学 |
| 26 | gz-440113-8ef59a4c | 祈福新邨 | middle | 年检 #27 祈福新邨学校中学部 |
| 27 | gz-440113-8efab2cd | 正声小学 | primary | 年检 #2 |
| 28 | gz-440113-999fb9c0 | 广州市星执学校 | middle,high | 民办高中录取名单（2025 首招高一） |
| 29 | gz-440113-a36980e5 | 广州市星执学校小学招生处 | primary | 星执学校小学部（与 #28 同集团） |
| 30 | gz-440113-a45e4a1a | 华南碧桂园学校(小学部) | primary | 年检 #21 华南碧桂园学校 |
| 31 | gz-440113-a6aa9fb0 | 化龙大博学校(小学部) | primary | 年检 #12 化龙镇大博学校 |
| 32 | gz-440113-a6ae517b | 星执外国语小学 | primary | 年检 #5 星执外国语小学 |
| 33 | gz-440113-a93513f2 | 番禺区北新正华学校 | primary,middle | 年检 #18 北新正华学校（北大新世纪正华） |
| 34 | gz-440113-ad8632f5 | 番禺区香江实验学校 | primary,middle | 年检 #8 香江实验学校 |
| 35 | gz-440113-c181d193 | 祈福英语实验学校 | primary,middle,high | 年检 #17 实验小学 + 民办高中（国内/港澳台班） |
| 36 | gz-440113-c40a06e1 | 京师奥园南奥实验学校 | primary,middle | 年检 #3 |
| 37 | gz-440113-c5dec315 | 华立学校 | primary,middle | 年检 #22 南村华立小学 |
| 38 | gz-440113-c9f8740e | 恒润实验学校 | primary,middle | 年检 #15 |
| 39 | gz-440113-d4aecd66 | 祈福英语实验小学 | primary | 年检 #17 |
| 40 | gz-440113-d7e3e576 | 番禺区金海岸实验学校 | primary,middle | 年检 #33 金海岸实验学校 |
| 41 | gz-440113-e946f7f3 | 会江实验学校 | primary,middle | 年检 #4 大石会江学校 |

---

## 附：核实依据与方法

1. **一手官方来源（优先级最高）**：
   - 番禺区教育局《关于公示2025年度番禺区民办学校年检情况的通知》（2026-07-22，36 所民办中小学全合格，含完整名单）：https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10911/mpost_10911898.html
   - 大洋网转载的 36 所中小学年检结论完整名单（图片 OCR）：http://news.dayoo.com/gzrbrmt/202607/23/170639_54982964.htm
   - 番禺区 2025 年积分制入学统筹学位计划（逐条标注"(民办)"，含大博/金华/嘉诚/万翔/加拿达等）：http://www.panyu.gov.cn/attachment/7/7835/7835118/10323988.pdf ；补填分数线 http://www.panyu.gov.cn/attachment/7/7836/7836414/10334887.pdf
   - 广州市教育局关于博萃德、执鸿等九年一贯制民办校审批遗留问题通知：https://jyj.gz.gov.cn/gk/zfxxgkml/bmwj/qtwj/content/post_10541662.html
   - 2025/2026 年广州市中考第四/三批次民办高中录取名单（确认 5 所民办高中性质）：http://gzzk.gz.gov.cn/zwgk/zwdt/content/post_10910342.html ；https://gzzk.gz.gov.cn/zkzz/zkxx/lnfs/content/post_10365138.html
   - 市教育局认定华师附中番禺小学等为公办义务教育标准化学校：https://jyj.gz.gov.cn/gk/zfxxgkml/bmwj/qtwj/content/post_9798933.html

2. **交叉验证来源**：
   - 羊城晚报·隽言教育《广州民办小学招生再创新低》（2025-06-18，"番禺区 36 所学校 6663 个学位"）：https://edu.ycwb.com/2025-06/18/content_53477677.htm
   - 市教育局《2025 广州普高招生计划》（番禺新增星执、博萃德两所民办高中）：https://jyj.gz.gov.cn/yw/jyyw/content/post_10271257.html
   - 南方+（番禺 9 所民办校收费批复，含金海岸实验学校）：https://www.nfnews.com/content/EynGWWGM3Z.html
   - 新花城《锦绣香江学校为小区配套公办九年一贯制》：https://huacheng.gz-cmc.com/pages/2022/08/09/f3f889b287764bb1909d130ae117b452.html

3. **实体匹配方式**：对每所确认民办校执行 `python3 scripts/registry/match_school.py 440113 "<校名>"`，并在 entities.json 中按 school_id / aliases grep 校验跨学段一致性。

## 待办（给项目 owner）

- [ ] 将第一节 8 行实体（厦滘中学部、金华中学、大博中学、华南碧桂园中学部、加拿达中学部、金海岸学校 primary+middle、博萃德小学部）的 `nature` 补标为 `民办`。
- [ ] 第二节补实体：博萃德学校 high 阶段；剑桥郡加拿达外国语学校 primary 阶段。
- [ ] 第三节待核实：gz-440113-30628a8d 香江中学（疑增城校误植）、长颈马初中部、吉毅教育初中部 是否清理。
- [ ] 后续实体合并：~~金海岸学校(b33076d3)↔金海岸实验学校(d7e3e576)~~（2026-09-18 撤销：公办≠民办，两所学校不合并）；博萃德小学部(cf01b95f)↔博萃德学校(3d006240)。
