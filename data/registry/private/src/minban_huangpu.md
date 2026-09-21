# 黄埔区（adcode=440112）民办中小学名单核实与实体匹配清单

> 生成时间：2026-09-14
> 数据基准：黄埔区教育局 2025 年义务教育招生计划、2024 年度民办中小学年检结论（2025-08 发布）、2026 年招生政策、广州市教育局批复文件
> 实体表：`data/registry/entity/dist/entities.json`（黄埔区共 191 条，本次从 1 所民办开始补齐）

## 核心结论

- **黄埔区 2025 年在招民办小学 8 所、民办初中 9 所**（另有民办高中 2 所：明珠高级中学、天健学校）。
- **确认民办且实体表已存在：11 条实体记录**（含跨 stage），需补标 `nature=民办`。
- **确认民办但实体表缺失：7 条**（天健学校初中/高中、新侨学校小学部/高中部、4 所九年制学校小学部），需先补实体再标记。
- **已排除（转公/停办）：7 所**，含万科城市花园小学（2025 转公）、二中苏元（2022 转公）、广附黄埔实验（2022 转公）、同仁学校（2025 场地到期停办）、利民艺体实验小学（2022 终止办学）、崇德实验/海地实验（停办）。
- **外籍人员子女学校**（广州美国人学校等）不参与义务教育民办摇号，单独标注。

---

## 一、确认民办且实体表已存在（新增 nature 标记）

| school_id | name | stage | 来源URL | 备注 |
|---|---|---|---|---|
| gz-440112-4517600f | 黄埔区洋城学校 | primary | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm ；https://www.nfnews.com/content/n614bG1d3P.html | 民办小学（仅小学部），2025 年招 5 个班；地址永和街桑田二路 4 号；2024 年度年检合格 |
| gz-440112-bffde68d | 广州新侨学校 | middle | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm ；http://jyj.gz.gov.cn/yw/tzgg/content/post_8682045.html | 民办十二年一贯制（小学+初中+高中），中新合作办学；地址知识城慈济路 2 号；非营利性；实体仅 middle 阶段，缺 primary 和 high（见第二节） |
| gz-440112-673fa2c9 | 中黄外国语实验学校丰巢快递柜 | middle | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm ；https://www.hp.gov.cn/hpqgzkfqzdlyzl/jyxx/gzdt/content/post_10903122.html | 民办九年一贯制；地址保税区保金路 36 号；2024 年度年检合格；**实体名含"丰巢快递柜"为 POI 误植，建议清理为"广州市黄埔区中黄外国语实验学校"**；缺 primary 阶段实体（见第二节） |
| gz-440112-ccdabd8f | 东晖学校 | middle | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm ；https://www.nfnews.com/content/n614bG1d3P.html | 民办九年一贯制；地址南岗沧联二路沧头；2024 年度年检合格；缺 primary 阶段实体（见第二节） |
| gz-440112-2132c84e | 东联学校 | middle | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm ；https://www.hp.gov.cn/zwgk/mszd/jy/content/post_10903028.html | 民办九年一贯制；地址云埔街沧联社区沙梨园二号；非营利性；2024 年度年检合格 |
| gz-440112-2132c84e | 东联学校 | primary | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm | 民办九年一贯制小学部，2025 年招 2 个班 |
| gz-440112-21d0cd90 | 广州市黄埔国光学校 | middle | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm ；http://www.hp.gov.cn/attachment/7/7800/7800159/10222500.pdf | 民办九年一贯制；地址鱼珠街茅岗区坑田；非营利性；2024 年度年检合格 |
| gz-440112-202efa5a | 黄埔国光小学 | primary | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm | 民办九年一贯制小学部，2025 年招 2 个班；与中学部同址 |
| gz-440112-93566bfa | 华外同文外国语学校 | middle | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm ；https://www.hp.gov.cn/xwzx/tzgg/qtgg/content/post_10244143.html | 民办九年一贯制（原华南师范大学附属外国语学校）；地址科学大道 2 号；非营利性；2024 年度年检基本合格；缺 primary 阶段实体（见第二节） |
| gz-440112-fb457bd7 | 南方中英文学校 | middle | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm ；https://www.nfnews.com/content/n614bG1d3P.html | 民办九年一贯制；地址长岭路 83 号；2024 年度年检基本合格；缺 primary 阶段实体（见第二节） |
| gz-440112-4ed867c7 | 广州市黄埔区华实学校 | middle | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm ；https://www.hp.gov.cn/qmtjjczwgk/26sdly/ywjyly/content/post_10713528.html | 民办初中（原"广州市黄埔华南师范大学附属初级中学"→2021 年更名"华实初级中学"→2026 年更名"华实学校"）；地址长洲街金洲北路 516 号；非营利性；2024 年度年检合格 |
| gz-440112-705844f8 | 广州市明珠高级中学 | high | https://ep.ycwb.com/epaper/ycwb/h5/html5/2025-05/20/content_2976_707337.htm | 民办高中，已标记；2025 年新增招收公费班 |

> 说明：以上 12 条实体记录的 `nature` 字段当前为空（match_school.py 显示"公办(未标)"为缺省态），应统一补标为 `民办`。

---

## 二、确认民办但实体表不存在（需先补实体再标记）

| 官方校名 | 学段 | 来源URL | 建议实体name | 备注 |
|---|---|---|---|---|
| 广州市天健学校 | middle | https://jyj.gz.gov.cn/gk/zfxxgkml/bmwj/qtwj/content/post_10258036.html ；https://ep.ycwb.com/epaper/ycwb/h5/html5/2025-05/20/content_2976_707337.htm | 广州市天健学校(初中部) | 原"广州市黄埔区天健学校"（原名玉岩天健实验学校），2025 年 5 月经市教育局批复变更为完全中学并更名"广州市天健学校"；地址长贤路 101、103、105 号；非营利性；2025 年民办初中招 6 个班；2026 年招 300 人（含跨区 147 人） |
| 广州市天健学校 | high | https://jyj.gz.gov.cn/gk/zfxxgkml/bmwj/qtwj/content/post_10258036.html ；https://ep.ycwb.com/epaper/ycwb/h5/html5/2025-05/20/content_2976_707337.htm | 广州市天健学校(高中部) | 2025 年新增高中部，与明珠高级中学并称黄埔区两所民办高中招收公费班 |
| 广州新侨学校 | primary | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm ；http://jyj.gz.gov.cn/yw/tzgg/content/post_8682045.html | 广州新侨学校(小学部) | 中新合作十二年一贯制民办学校小学部；2025 年民办小学招 4 个班；实体已有 middle（gz-440112-bffde68d），需新增 primary 阶段 |
| 广州新侨学校 | high | http://jyj.gz.gov.cn/yw/tzgg/content/post_8682045.html ；https://www.scagz.com/about/introduction.html | 广州新侨学校(高中部) | 十二年一贯制民办学校高中部（国际高中）；需新增 high 阶段实体 |
| 广州市黄埔区中黄外国语实验学校 | primary | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm | 广州市黄埔区中黄外国语实验学校(小学部) | 九年一贯制民办学校小学部；2025 年民办小学招 2 个班；实体已有 middle（gz-440112-673fa2c9，但名称含"丰巢快递柜"误植），需新增 primary 阶段 |
| 广州市黄埔东晖学校 | primary | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm | 广州市黄埔东晖学校(小学部) | 九年一贯制民办学校小学部；2025 年民办小学招 2 个班；实体已有 middle（gz-440112-ccdabd8f），需新增 primary 阶段 |
| 广州市黄埔区华外同文外国语学校 | primary | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm | 广州市黄埔区华外同文外国语学校(小学部) | 九年一贯制民办学校小学部；2025 年民办小学招 5 个班；实体已有 middle（gz-440112-93566bfa），需新增 primary 阶段 |
| 广州市黄埔区南方中英文学校 | primary | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm | 广州市黄埔区南方中英文学校(小学部) | 九年一贯制民办学校小学部；2025 年民办小学招 2 个班；实体已有 middle（gz-440112-fb457bd7），需新增 primary 阶段 |

---

## 三、待核实

| 校名 | 来源URL | 待核实原因 |
|---|---|---|
| 广州美国人外籍人员子女学校(中学部)（gz-440112-b26d917f, middle） | https://www.qcc.com/cassets/s221324f7e7f8a0049edd7c801dcc974.html ；https://www.hp.gov.cn/2021gb/zz/zwyw/content/post_10882461.html | 该校为"外籍人员子女学校"，注册为民办非企业单位，但仅招收外籍/港澳台学生，不参与广州市义务教育民办学校招生摇号，也不在区教育局民办中小学年检名单内。是否纳入 `nature=民办` 需项目 owner 决定（若纳入，同属外籍人员子女学校的广州日本人学校、贝赛思、爱莎、奥伊斯嘉等也需一并梳理，但这些学校在实体表中暂无记录） |
| 黄埔海地实验学校（gz-440112-d83b7142, primary） | http://m.toutiao.com/group/7036348665619251748/ | 原民办九年一贯制学校，2012 年更名"黄埔崇德实验学校"并迁至夏园村；2021 年因学位超规模、场地等问题面临停办；2024 年度年检名单及 2025/2026 招生计划均无该校，疑似已停办但未见正式终止办学批复。待核实是否仍在办学，若确认停办则从实体表清理 |

---

## 四、已排除（公办或已民转公/停办）

| 校名 | 排除原因 | 来源URL |
|---|---|---|
| 广州市黄埔万科城市花园小学 | 2025 年因场地租赁到期转公，现为广州石化小学（西校区），2025 年起列入公办小学招生计划 | https://huacheng.gz-cmc.com/pages/2025/04/11/SF13662566f432bbaef76743a3a5c927.html |
| 广州市黄埔区同仁学校 | 办学场地（庙头北路 13 号）租赁合同 2025 年 7 月 10 日期满，区教育局收回场地不再续签；2024 年招生计划已标注"场地到期、办学许可届满"；2025/2026 年招生计划无该校 | http://www.hp.gov.cn/attachment/7/7747/7747956/10070091.pdf ；https://m.gz.bendibao.com/edu/349939.html |
| 广州市黄埔利民艺体实验小学（gz-440112-6b2e0e75, primary） | 2022 年 1 月经黄埔区教育局批准终止办学，已交回办学许可证；实体表仍存该条，建议后续清理 | https://www.hp.gov.cn/gzhpjy/gkmlpt/content/8/8040/mpost_8040222.html |
| 广州市第二中学苏元实验学校（苏元学校，gz-440112-8bf29a28 high / gz-440112-a0244635 middle 西校区） | 2022 年"公参民"脱钩中转公，现为黄埔区属公办学校；2025/2026 年公办初中招生计划表明确列"苏元学校（西校区）""苏元学校（东校区）" | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm ；https://new.qq.com/rain/a/20220429A0EWIY00 |
| 广州市黄埔广附实验学校（广大附中黄埔实验学校，gz-440112-87756a6d middle 西校区 / gz-440112-705c66e3 middle 东校区等） | 2022 年"公参民"脱钩中转公，现为广大附中黄埔实验学校（公办）；2025 年公办初中招生计划表列"广大附中黄埔实验学校（西校区）（东校区）" | https://huacheng.gz-cmc.com/pages/2021/11/18/8ba1dc2550bc41a39d6c63843dc797bb.html ；https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm |
| 华峰学校（gz-440112-0aa66950 primary+middle） | 公办学校；2025 年公办小学招生计划表列"华峰学校（小学部）"，公办初中招生计划表列"华峰学校" | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm |
| 华南师范大学附属黄埔实验学校（gz-440112-6d1ac70b） | 公办学校；2025 年公办小学招生计划表列"华南师范大学附属黄埔实验学校（小学部）"，公办初中招生计划表列"华南师范大学附属黄埔实验学校" | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm |
| 广州市黄埔区会元学校（gz-440112-e3190fa2 / gz-440112-48db116a 小学部 / gz-440112-84bb98f2 初中部） | 公办学校（二中会元学校）；2025 年公办小学/初中招生计划表均列"会元学校" | https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm |
| 黄埔崇德实验学校（原海地实验学校） | 原民办九年一贯制，2021 年面临停办，近年未出现在年检名单和招生计划中，疑似已停办 | http://m.toutiao.com/group/7036348665619251748/ |

---

## 附：核实依据与方法

1. **一手官方来源**（优先级最高）：
   - 黄埔区教育局《2025 年黄埔区义务教育学校招生工作实施细则》（含公办/民办小学、初中招生计划表）：https://news.dayoo.com/gzrbrmt/202504/29/170639_54819585.htm
   - 黄埔区 2024 年度民办中小学年检结论公告（11 所，含许可证号/办学层次/地址/校长）：https://www.nfnews.com/content/n614bG1d3P.html
   - 黄埔区 2025 年民办初中电脑派位结果（6 所摇号学校名单）：https://www.hp.gov.cn/zwgk/mszd/jy/content/post_10326496.html
   - 黄埔区 2026 年民办初中电脑派位结果（3 所摇号学校名单）：https://www.hp.gov.cn/zwgk/mszd/jy/content/post_10872515.html
   - 广州市教育局关于天健学校变更为完全中学并更名的批复：https://jyj.gz.gov.cn/gk/zfxxgkml/bmwj/qtwj/content/post_10258036.html
   - 广州市教育局关于新侨学校变更为十二年制学校并更名的批复：http://jyj.gz.gov.cn/yw/tzgg/content/post_8682045.html
   - 黄埔区教育局关于华实初级中学办学许可续期批复（非营利性民办）：https://www.hp.gov.cn/qmtjjczwgk/26sdly/ywjyly/content/post_10713528.html
   - 黄埔区教育局关于东联学校办学许可续期批复（非营利性民办）：https://www.hp.gov.cn/zwgk/mszd/jy/content/post_10903028.html
   - 黄埔区教育局关于华外同文外国语学校办学许可续期批复（非营利性民办）：https://www.hp.gov.cn/xwzx/tzgg/qtgg/content/post_10244143.html
   - 黄埔区教育局关于国光学校办学许可续期批复（非营利性民办）：http://www.hp.gov.cn/attachment/7/7800/7800159/10222500.pdf
   - 黄埔区教育局关于万科城市花园小学转公公告：https://huacheng.gz-cmc.com/pages/2025/04/11/SF13662566f432bbaef76743a3a5c927.html
   - 黄埔区教育局关于同仁学校场地到期收回公告：http://www.hp.gov.cn/attachment/7/7747/7747956/10070091.pdf
   - 黄埔区教育局关于利民艺体实验小学终止办学批复：https://www.hp.gov.cn/gzhpjy/gkmlpt/content/8/8040/mpost_8040222.html
   - 羊城晚报关于黄埔区新增 2 所民办高中的报道：https://ep.ycwb.com/epaper/ycwb/h5/html5/2025-05/20/content_2976_707337.htm

2. **实体匹配方式**：对每所确认民办校使用 `python3 scripts/registry/match_school.py 440112 "<校名>"`，跨 stage 均查询，并辅以在 `entities.json` 中按关键词 grep 校验别名。

## 待办（给项目 owner）

- [ ] 将第一节 12 条实体记录的 `nature` 字段补标为 `民办`。
- [ ] 第二节新增 8 条实体（天健学校初中/高中、新侨学校小学/高中、中黄/东晖/华外同文/南方中英文的小学部）。
- [ ] 修正 gz-440112-673fa2c9 实体名（去除"丰巢快递柜"POI 误植后缀）。
- [ ] 第三节待核实项：广州美国人学校是否纳入 `nature=民办`；海地实验/崇德实验是否已正式停办并清理实体。
- [ ] 第四节已排除项中，gz-440112-6b2e0e75（利民艺体实验小学，已终止办学）建议从实体表清理。
