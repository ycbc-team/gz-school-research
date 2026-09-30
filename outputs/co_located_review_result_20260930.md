# 同段同址冗余候选全量 Review 结果（2026-09-30）

仓库：`gz_school_research3`；基线 git HEAD=`9b5aec4`；数据真源约束：只改构建脚本/输入，禁止手改 dist 产物；改脚本后重跑并提交。

## 方法与判定标准

- 候选来源：`data/registry/entity/test/snapshots/co_located_snapshot.json`（同学段+同区+haversine ≤200m，共 **55 组**，检测逻辑 `scripts/data_quality_test.py` 第[12]项）。
- 判定流程：7 个区（越秀/海珠/天河/白云/黄埔/荔湾/番禺）分别联网核实，依据 = 地址相同 + 名称互为别名 / 官方更名记录 / 第三方学校库别名 / 历史招生文件等可追溯来源（证据 URL 见下）。
- 仅归并「确凿同一学校/同一校园被拆成两个实体」的组；正常兄弟校区（独立校址、官方并列）与公/民办相邻独立校保留；不能确凿核实的组列入待人工确认，不动数据。
- 修复机制（与 commit a15ff9d 同款三件套）：`data/registry/entity/scripts/build_entities.py` 的 `DROP_CAMPUS` 列表（按 `学段|POI名` 删除冗余 POI）+ `REMOVED_POI_ALIAS` 字典（被删名挂为保留实体别名）+ 必要的 `POI_NAME_FIX`/`PRIMARY_CAMPUS_ALIAS`/`RESOLVE_OVERRIDE` 修正，重跑全部派生产物。

**结论总览：12 组归并 / 42 组保留 / 1 组待人工确认（55 组全覆盖）。**

---

## 一、归并组（12 组）

| # | 区 | 学段 | 被删冗余实体（POI） | 保留实体 | 距离 | 判定依据 | 证据 URL |
|---|---|---|---|---|---|---|---|
| 1 | 白云 | 小学 | 人和镇第四小学 `gz-440111-369dffe8` | 广州市第七十三中学·小学部 `gz-440111-9f1c9750` | 26.1m | 官方一览表载73中为九年一贯制，小学部地址即人和街2号，与四小完全同址；2018年该地段（人和村/高增村）由四小招生（电话86450302），2021年改为73中小学部且沿用同一电话，2023年四小不再单列——系四小重组/更名纳入九年一贯73中，同一校园拆分 | https://www.by.gov.cn/gzbyjy/gkmlpt/content/8/8787/mpost_8787737.html；https://www.by.gov.cn/attachment/7/7288/7288507/8957533.pdf；https://www.by.gov.cn/attachment/6/6787/6787386/7264529.pdf |
| 2 | 白云 | 高中 | 广州市白云中学(南区) `gz-440111-15fa03a9` | 广州市白云中学 `gz-440111-e74c2e1d` | 53.4m | 官方：白云中学为十二年制，高中部地处金沙洲、校址藤业一路366号；"一校三区"=高中部(金沙洲)+汇侨(初中)+棠景(九年一贯)，无官方南区校区；南区 POI 即官方高中部校址，与法人行 53m，系高中部校园冗余 POI | https://guangzhoubaiyun.gz-cmc.com/pages/2026/06/01/1f424a31187e4cb78a582ce7c7786b22.html |
| 3 | 白云 | 初中 | 广州云雅实验学校 `gz-440111-7d12a21e` | 广州云雅实验学校初中部 `gz-440111-6782d2c7` | 67.7m | 官方登记为同一民办法人、九年一贯（金碧西路19、20号，2021年由初中变更为九年一贯）；两 POI 相距68m 即 19、20号同一校园，招生系统仅列一家；保留已被招生俗称锚定的初中部实体 | https://www.by.gov.cn/gzbyjy/gkmlpt/content/8/8787/mpost_8787737.html；https://www.by.gov.cn/shzz/Pubbase/xxgsShzzPage/kj0b100412 |
| 4 | 白云 | 初中 | 华赋学校北校区初中部 `gz-440111-81f3c313` | 广州市白云区华赋学校(北校区) `gz-440111-43437f78` | 103.1m | 官方：华赋学校为同一民办法人、九年一贯，北校区即大源中路3-6号（南校区在大源南路92号才是官方并列校区）；两 POI 同处北校区校园内，"北校区初中部"系校内初中分部冗余 POI | https://www.by.gov.cn/gzbyjy/gkmlpt/content/8/8787/post_8787737.html；https://guangzhoubaiyun.gz-cmc.com/pages/2024/03/19/7a249dc1a7d84223932d5ed5c1d64386.html |
| 5 | 白云 | 高中 | 广州市白云中学(北区) `gz-440111-5849b586` | 广州市白云中学 `gz-440111-e74c2e1d` | 156.6m | 同组2：官方高中部仅金沙洲一处（藤业一路366号），无官方北区校区；北区 POI(365号)与南区(366号)一路之隔、同属高中部校园南北两半，系同一校园北半侧冗余 POI | https://guangzhoubaiyun.gz-cmc.com/pages/2026/06/01/1f424a31187e4cb78a582ce7c7786b22.html |
| 6 | 海珠 | 初中 | 广州市第七十八中学 `gz-440105-455eaa08` | 广州市五中滨江学校(远安校区) `gz-440105-06994d39` | 66.9m | 78中老地址=远安路80号=五中滨江远安校区（2025招聘公告/2021发改委复函同址）；五中滨江2015年以78中为基础成立、远安校区创办于1968年（即78中创办年）；2026官方初中招生名单仅列"五中滨江学校"，78中为历史旧名 | https://www.haizhu.gov.cn/gzhzjy/attachment/7/7846/7846231/10357966.pdf；http://www.haizhu.gov.cn/zwgk/zdlyxxgk/zdjsxmsphss/content/mpost_7227715.html；https://ipaper.oeeee.com/ipaper/A/html/2024-03/14/content_4151.htm；https://www.nfnews.com/content/A6EBmK7xoK.html；http://ebook.gdjy.cn/gdjyzhb/resfile/2016-03-05/44/44.pdf |
| 7 | 海珠 | 小学 | 海珠区滨江西路第一小学 `gz-440105-bf39b5bb` | 同福中路第一小学(西校区) `gz-440105-a72d7648` | 0m | 两 POI 坐标相同且同指鳌洲正街15号；滨江西路一小 2016/2017 起停招、地段由同福中一小接收，2024 官方名单与教育集团成员均已无此校，旧址即同福中一小西校区，系陈旧 POI | http://zs.gzeducms.cn/u/cms/www/201705/04105506xoed.pdf；https://m.gz.bendibao.com/life/213947.html；https://www.haizhu.gov.cn/hzdt/hzyw/hzzc/content/mpost_10167355.html |
| 8 | 黄埔 | 初中 | 镇龙第二中学 `gz-440112-ccf82991` | 广州市黄埔区玉岩实验学校 `gz-440112-f3817fbe` | 31.4m | 企查查曾用名链"广州市萝岗区镇龙第二中学→镇龙中学→玉岩实验学校"；同处迳头路1号（公交站仍名镇龙二中），现代招生仅玉岩实验学校——历史校名→现名同一学校 | https://m.qcc.com/firm/gce34521b59cff6c3ef4ae440f8be53e.html；https://huacheng.gz-cmc.com/pages/2020/07/01/a50900b107f64c52a4b725bba0d4fb8f.html |
| 9 | 黄埔 | 初中 | 玉泉学校-中学部 `gz-440112-0946f5ef` | 玉泉学校 `gz-440112-12b0184b` | 139.1m | 玉泉学校法人本部=云埔五路38号；entity 距 139m 仍在本部校园内（东/北校区均数百米外），初中部无独立分校址，"中学部"系本部初中部的冗余 POI 拆分 | https://www.hp.gov.cn/zwgk/zbtb/content/post_10709786.html；https://www.tianyancha.com/company/3096966758/sifa；https://huacheng.gz-cmc.com/pages/2024/01/18/3ba0fa2e86f04e3e93e1b77eb66064d8.html |
| 10 | 黄埔 | 初中 | 铁铮学校（裸名） `gz-440112-11ed4c6c` | 广铁一中铁铮学校(西校区) `gz-440112-7127244c` | 0m | 两实体坐标完全相同，均落在沙步铁铮学校西校区校园；官方无独立本部（2023 首开即西校区，另有东/南校区），裸名"铁铮学校"即西校区校园的通用/聚合 POI 别名；小学部由 primary 行承载 | https://www.hp.gov.cn/xwzx/zwyw/tpyw/content/post_9182450.html；https://news.southcn.com/node_54a44f01a2/d305b3250e.shtml；https://static.nfapp.southcn.com/content/202308/28/c8038753.html |
| 11 | 黄埔 | 小学 | 长岭居小学（裸名） `gz-440112-e0419ae0` | 长岭居小学南校区 `gz-440112-70e86492` | 78m | 2021 年"长岭居小学"=长岭路38号；2022 年开北校区后原址改称"南校区"——裸名 POI 与南校区同处长岭路38号校园（同址拆分）。**注：原裸名实体误挂别名"长岭居小学西校区"系错误关联（真西校区在水西车辆段、距 3.4km，仓库无独立 POI），本次一并消除，官方西校区名转未匹配缺口（见"数据缺口待补点"）** | https://www.hp.gov.cn/gzhpjy/gkmlpt/content/7/7264/mpost_7264742.html；http://www.hp.gov.cn/attachment/7/7401/7401053/8220843.pdf |
| 12 | 黄埔 | 初中 | 广州市第八十六中学分校 `gz-440112-06029745` | 广州市第八十六中学初中部 `gz-440112-43108516` | 28.1m | **用户确认**：两实体地址完全相同（黄埔区丰乐北路泰景花园泰景中街121号）、电话相同（020-82277650）；第三方学校库（房天下）将"八十六中分校/86中分校"列为初中部别名；2014 年分校特长生简章地点即泰景中街121号。校本部（大沙地西路5号，`gz-440112-0cb5a402`）为独立校区，保留不动 | 用户提供映射 + 第三方学校库交叉核对 |

## 二、保留组（42 组，正常兄弟校区或独立学校相邻，不予归并）

- **越秀（10 组，全部 keep）**：三中↔名德实验学校（公办完中 vs 独立民办初中，旧部前56号独立摇号）；满族小学大德↔象牙校区（大德路203号 vs 象牙街48号，官方并列校区）；红火炬东↔启智学校白云路（普通小学 vs 公办特教）；小北路小学天香街↔小北校区（官方"4校区"按年级分流）；东川路小学↔南校区（东川路47号 vs 元运街12号）；东风东路小学广场↔天伦校区（官方"一门四校区"）；永曜北小学↔红火炬西（永曜北2024/2025 仍独立办学，未撤并）；海珠中路小学七株榕↔海珠中（2021 合并后三校区并列）；红火炬东↔红火炬西（同校东西校区）；云山小学↔雄鹰学校小学部（公办 vs 民办）。
- **海珠（10 组，全部 keep）**：新民六街小学北↔南校区、南武第二实验学校北↔南校区、梅园西路小学北↔南校区（官方并列校区）；凤江↔康乐、赤岗东↔龙涛、东风↔东风第二、华怡↔赤岗（公办 vs 民办相邻）；基立道长安↔海珠实验富基、石溪劬劳↔金碧一小西（独立公办小学不同址）；启能学校↔江南大道中小学（特教 vs 普校）。
- **白云（3 组 keep）**：华师白云学校↔黄边小学黄边校区（旧改配建新校 vs 省一级公办一校四区，地段/法人独立）；新正小学↔金沙小学（民办 vs 公办）；广云外国语↔龙德学校（两所不同民办）。
- **天河（6 组 keep）**：龙口西天阳↔穗园校区、五山小学西↔东校区、昌乐小学↔旭日校区（同法人官方并列校区）；吉山↔同仁学校、侨乐北↔同仁天兴、同仁实验↔棠东（公办 vs 民办相邻）。
- **荔湾（6 组，全部 keep）**：乐贤坊荔枝湾↔宝源学校（集团兄弟校区、独立编班招生）；培英鹤洞↔真光初中部本部（两所百年名校相邻）；广雅小学↔环市西路绿森林（独立公办小学）；省实荔湾第三小学部↔东沙博雅（公办 vs 民办）；一中初中部↔姜中宏校区（黄沙大道54号 vs 蓬莱路3-5号，名额分配代码独立 010301/010323，2022 原一中外国语转制公办更名，官方招生分列两个独立办学点——**非同址拆分**）；一中初中部↔西关培英西校区（不同公办中学相邻）。
- **番禺（7 组，全部 keep）**：香江实验学校↔锦绣香江小学/学校（民办原香江育才实验 vs 公办九年一贯，一民一公）；先锋小学↔南阳里东校区；大石中心小学↔大石小学（岗东路2号 vs 22号，独立法人）；铁英学校东↔西校区（官方"一校两区"）；南村中心↔雅居乐小学（独立公办）；另 2 组为快照拼接异常行（组7 自引用 id1==id2、组6 与原始快照行错位），未动数据仅标 keep。

> 各区判定明细（含距离、证据 URL 全集）见子代理产物 `agents/<id>/artifacts/co_located_review_<区>.json`（440103/440104/440105/440106/440111/440112/440113 共 7 份）。

## 三、待人工确认（1 组，不动数据）

| 区 | 学段 | 实体 A | 实体 B | 距离 | 说明 |
|---|---|---|---|---|---|
| 天河 | 初中 | 天荣中学 `gz-440106-90c47ff5` | 广州市第十二中学 `gz-440106-458838f7` | 152.5m | 天荣中学确凿为独立公办初中（天荣路3号，2024 年独立预算/决算）；但"广州市第十二中学"在天河无任何官方办学记录（历史广州十二中在荔湾、2007 年已改制为西关外国语学校），该 POI（天强路/天荣路口）来源不明，无法确凿判定同校园拆分或独立机构——建议人工核图后再定 |

## 四、修复机制与联动产物

- 构建脚本（真源修改，非手改产物）：
  - `data/registry/entity/scripts/build_entities.py`：`DROP_CAMPUS` +11 条（含学段限定）、`REMOVED_POI_ALIAS` +11 条；移除 `PRIMARY_CAMPUS_ALIAS` 中"长岭居小学（西校区）"错误关联条目；POI_NAME_FIX/注释同步。
  - `data/registry/entity/scripts/school_match.py`：长岭居聚合锚点移除已删裸名实体；新增 `RESOLVE_OVERRIDE` 3 条（广州大学附属中学校本部/番禺校区、广州中学凤凰校区——修复 awards 重建时跨学段解析丢失，实体身份映射为人工确认的显式关系）。
  - 输入层：`data/registry/group/src/groups_anchors.json`（云雅锚点去已删实体）、`data/middle/tier1_schools_all.json`（去已删实体）。
- 重跑派生产物：entities.json（1519 实体）、primary/middle/high POI×3、linkage 全家（quota_matrix/outcome/ranking + canonical + 快照）、awards 全家（六竞赛 + detailed_records）、middle_enrollment、org_sort、xiaoshengchu 全家、education_groups、non_group_multi_campuses、specialty_schools、civilized_campuses、minban、compact。

## 五、快照变化说明（均为显式更新基线，禁止手改）

| 快照 | 变化 | 理由 |
|---|---|---|
| 同址候选 `co_located_snapshot.json` | 55 → **43 组** | 12 组归并后不再构成冗余对 |
| 孤儿 `orphans_snapshot.json` | 64 → **54 所** | 12 个被删 POI 别名承继到保留实体，不再孤儿 |
| 实体 `entities_snapshot.json` | 1519 实体（快照刷新） | 12 实体删除 + 别名承继（含长岭居西校区错误别名消除） |
| 民办 `minban_snapshot.json` | 230（刷新） | 云雅/华赋等民办实体引用重映射 |
| 小学招生 `enrollment_snapshot.json` | 7 区 781 条 | 删除实体对应的官方记录随实体消失：86中分校（→初中部，校区展开）、长岭居裸名记录移除；"长岭居小学（西校区）"官方记录（水西车辆段、1班）因无实体转 **unmatched 缺口**（数据缺口待补点，见下） |
| 小升初 `xiaoshengchu_snapshot.json` | 935 条 / 163 组 | 被删 3 所小学记录正确合并到保留实体（同福中一小西校区 15 个 feed、73中 小学部 1 个、长岭居南校区 7 个，均无数据丢失）；本轮修正南校区记录从第4组归位第5组（西校区生源校因无实体转未解析缺口） |
| 初中生源小学 `middle_feed_snapshot.json` | 436 初中 POI（282 有生源小学） | 移除 7 个被删初中 POI 的 feed 条目 |
| 初中招生 `middle_snapshot.json` | 7 区 293 条 | 86中行主键=0cb5a402+43108516、铁铮学校行=7127244c+东校区等实体引用重映射 |
| awards 测试摘要 | 六竞赛 digest 更新 | awards 产物确定性重算（含广大附中/广州中学 RESOLVE_OVERRIDE 修复） |
| civilized formal review | 88 → 87 条 | "广州市第八十六中学分校"条目合并入初中部（advanced 89 条无变化） |
| linkage canonical 快照 | 刷新 | 云雅/86中分校等 school_ids 外键重映射 |

## 六、回归结果汇总（全部通过）

| 检查 | 结果 |
|---|---|
| `npm test`（shared 单测） | ✓ 52/52 |
| typecheck（web） | ✓ |
| `scripts/data_quality_test.py` | ✓（孤儿 54 / 同址 43 / 民办 230） |
| `data/poi/test/test_match_poi.py` + `test_stage_filter.py` | ✓ |
| `data/registry/entity/test/check_entities_snapshot.py` | ✓（1519 实体） |
| `data/registry/group/test/check_groups_drift.py` | ✓（业务快照/产物一致性/民办官方源校验，以提交后 HEAD 为基线复验） |
| `data/primary/transition/test/check_xiaoshengchu_snapshot.py` | ✓（935/163） |
| `data/primary/transition/test/check_middle_feed_snapshot.py` | ✓ |
| `data/primary/enrollment/test/check_enrollment_snapshot.py` | ✓（7 区 781 条） |
| `data/middle/enrollment/test/check_middle_snapshot.py` | ✓（7 区 293 条） |
| `data/awards/test/test_awards_build.py` | ✓（六竞赛 digest 全等） |
| `data/civilized_campuses/test/test_build.py` | ✓（national/provincial/municipal/advanced） |
| `data/linkage/test/`（check_dist_snapshots + check_special_matrix_snapshot） | ✓ |
| `data/high/cutoff_score/test/check_scores_snapshot.py` | ✓ |
| `scripts/data/compact.mjs` | ✓（compact 产物刷新，不入库） |

## 七、数据缺口待补点

- **长岭居小学（西校区）**：官方 2026 黄埔招生计划/派位 4 组单列（水西车辆段住宅项目地段、1 班），真校区距长岭路 38 号（南校区）3.4km，仓库无独立 POI。本轮消除其错误别名后，官方记录在小学招生层转 unmatched、小升初层转未解析，均已可见可审计。**待补独立点位后归位**（勿误判西校区在南校区）。
- **天荣中学 ↔ 广州市第十二中学（天河，152m）**：见第三节，待人工核图。

## 附：本次提交内容

- 修改文件 74 个（构建脚本 2 + 输入 2 + 全部派生产物 + 各快照基线），新增 review 结果本文件及候选数据包 `outputs/co_located_review_pack.json`。
