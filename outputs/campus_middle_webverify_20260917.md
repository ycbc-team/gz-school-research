# 初中校区「是否真办学」联网核实报告（2026-09-17）

背景：用户长主线「广州学校数据管线确定性修复」之 B/C 类校区逐一联网核实。
B 类（荔湾/白云）官方校区级文件有记录但官方校区名≠实体名，需确认映射+办学；C 类（越秀/天河/海珠/黄埔）官方初中招生文件为法人级，需网查官方细则确认哪些校区办初中。
判定口径：**CONFIRMED_CAMPUS**（该校区确实办初中→挂白名单）／**NON_MIDDLE**（纯高中或初中不在该校区→删 middle 留 high）／**未确认**。
依据优先级：官方（区政府/区教育局官网招生细则·市招考办名额分配/自招/录取·学校官网官微·南方+/广州日报/市台等官方口径）＞百科兜底（抖音/百度百科学校简介，须注明年份时效）。家长论坛/自媒体口碑一律未采用。

**统计：43 所全部有网查结论 —— CONFIRMED_CAMPUS 21 所 / NON_MIDDLE 21 所 / 未确认 1 所（89中北区）。**
分科明细见 5 个子文件（含完整原文摘录）：
- `webverify_b_liwan.md`（荔湾 7）、`webverify_b_baiyun.md`（白云 9）
- `webverify_c_yuexiu_huangpu.md`（越秀 7+黄埔 1）、`webverify_c_tianhe.md`（天河 13）、`webverify_c_haizhu.md`（海珠 6）

---

## 一、B 类：荔湾（7 所）

| 实体名 | school_id | 判定 | 映射/关键说明 | 主要依据 URL |
|---|---|---|---|---|
| 广州市真光中学(本部校区) | `gz-440103-2b8081bc` | **NON_MIDDLE** | 实体 POI 培真路17号＝官方「真光中学高中部本部/校本部」；官方「初中部本部校区」在鹤洞路98号（另一 POI）。该实体是高中本部。 | http://www.lw.gov.cn/zwgkk/zdlyxxgk/jyxx/czjy/content/post_10365715.html ；https://gzzk.gz.gov.cn/attachment/7/7813/7813034/10257660.pdf |
| 广州市真光中学(广钢校区) | `gz-440103-04c54db8` | **NON_MIDDLE** | 崇文五路，2025 秋新办**纯高中**（校本部直管），首年招 6 班 300 人，不办初中。 | https://www.gz.gov.cn/zwfw/zxfw/jyfw7/content/post_10400772.html ；https://static.nfnews.com/content/202508/21/c11646841.html |
| 广州市真光中学(汾水校区) | `gz-440103-882931a0` | **NON_MIDDLE** | 芬芳街47号，**纯高中**（独立招生代码）。原汾水初中部 2017 年并入后演变为今芳花校区，不在汾水。 | https://gzzk.gz.gov.cn:443/attachment/8/8020/8020649/10806504.pdf |
| 广东实验中学荔湾学校(初中部一期) | `gz-440103-1d99218d` | **CONFIRMED** | 实体 POI 北文街2号＝官方**广钢新城校区**（非花地湾320号）。 | http://www.lw.gov.cn/zwgkk/zdlyxxgk/jyxx/czjy/content/post_10365715.html |
| 广州市西关培英中学(西校区) | `gz-440103-41cb6344` | **CONFIRMED** | ＝官方裸名「广州市西关培英中学」(010307，完全中学)；官方登记地多宝路67号(南校区)，西校区留庆新横街3号，2026 原址改扩建中。 | http://www.lw.gov.cn/zwgkk/zdlyxxgk/jyxx/czjy/content/post_10365715.html |
| 广州市第四中学(康园校区) | `gz-440103-4cda3f9e` | **CONFIRMED** | ＝官方「四中(初中康园校区)」(010324，康王中路113号)，系四中聚贤**民办**初中部，故不进公办派位名单；2023 名额分配独立成行。 | https://gzzk.gz.gov.cn/attachment/7/7293/7293862/8974521.pdf ；百科佐证 https://m.baike.com/wiki/广州市第四中学/2577300 （2021-03-05 口径：初中部津园/逸园/虬园/康园） |
| 广州市南海中学(初中部) | `gz-440103-8e11a7d3` | **CONFIRMED** | ＝官方裸名「广州市南海中学」(西华路460号＝初中部，完全中学)。 | http://www.lw.gov.cn/zwgkk/zdlyxxgk/jyxx/czjy/content/post_10365715.html |

## 二、B 类：白云（9 所）

| 实体名 | school_id | 判定 | 映射/关键说明 | 主要依据 URL |
|---|---|---|---|---|
| 广州市白云中学(南区) | `gz-440111-15fa03a9` | **NON_MIDDLE** | POI 藤业一路366号＝官方**高中部**（金沙洲）；初中在汇侨/棠景，与南/北区无关。 | https://guangzhoubaiyun.gz-cmc.com/pages/2026/06/01/1f424a31187e4cb78a582ce7c7786b22.html |
| 广州市白云中学(北区) | `gz-440111-5849b586` | **NON_MIDDLE** | POI 藤业一路365号，与南区同属金沙洲高中部校园南北两半。 | 同上 |
| 广州市白云中学（法人行） | `gz-440111-e74c2e1d` | **CONFIRMED** | 法人＝完全中学，初中承载于汇侨(plan7)+棠景(plan5)。 | https://www.by.gov.cn/zwgk/zdlyxxgkzl/jyxxgkzl/content/mpost_8787739.html |
| 广外实验中学(北校区) | `gz-440111-f751344d` | **CONFIRMED** | 沙亭东路，2023 启用含初一 10 班 474 人；**≠陈田西校区**（黄石街2026新开）。 | https://huacheng.gz-cmc.com/pages/2023/09/06/0cc7ce5b080a40b88987a325045a5081.html |
| 广州市第六十五中学(江高校区) | `gz-440111-218475ea` | **NON_MIDDLE** | 2024/2026 初中 plan 均无此行，仅在高中名额分配名单；江高片初中由**江府校区**承接。 | http://gzzk.gz.gov.cn/zwgk/zwdt/content/post_10809569.html |
| 广州市培英中学(云城校区) | `gz-440111-730c7404` | **NON_MIDDLE** | ＝官方「培英白云新城校区」(云城西路1151号)，公办普通高中 48 班；初中名单无此校区。 | https://gzzk.gz.gov.cn/attachment/8/8020/8020664/10805492.pdf |
| 广东实验中学(云城校区) | `gz-440111-3405d87e` | **NON_MIDDLE** | 官网：**云城校区＝小学部**(萧岗明珠北路45号)；办初中的是「白云校区(中学部)」(白云大道北570号)，两处不同。 | http://www.gdsyzx.edu.cn/index/ |
| 广州空港实验中学(建南校区) | `gz-440111-150715c8` | **CONFIRMED** | 78 班完全中学，2026 年 9 月启用，现开初中 19 班、高中 22 班（4 月 plan 因未启用未列）。 | https://www.by.gov.cn/ywdt/zwyw/content/post_10982129.html |
| 龙归学校(初中部) | `gz-440111-4c9a3eaa` | **CONFIRMED** | 九年一贯制，裸名龙归学校初中 plan10，对口龙归学校小学部。 | https://www.by.gov.cn/attachment/7/7806/7806792/10241258.pdf |

## 三、C 类：越秀（7 所）

| 实体名 | school_id | 判定 | 映射/关键说明 | 主要依据 URL |
|---|---|---|---|---|
| 省实越秀学校(盘福校区) | `gz-440104-089a2a5b` | **NON_MIDDLE** | 初中招生与名额分配均只列**天胜校区**；盘福＝高中（高三）部。 | http://www.yuexiu.gov.cn/gzyxjy/gkmlpt/content/10/10790/mpost_10790617.html ；https://gzzk.gz.gov.cn/attachment/7/7293/7293862/8974521.pdf |
| 市第十七中学(西校区) | `gz-440104-099a5868` | **CONFIRMED** ⚠️ | 西校区(原82中)自 2021 为十七中初中校区，2023 名额分配独立成行。**注意：2026 年 8 月起因瑶台改造由培正矿泉学校整体临迁使用**，挂载需留意办学主体变更。 | https://gzzk.gz.gov.cn/attachment/7/7293/7293862/8974521.pdf |
| 育才中学(东校区) | `gz-440104-191aaa35` | **CONFIRMED** | 东校区＝水均南街21号＝育才初中部（高中部在福今路2号）。 | http://www.yuexiu.gov.cn/ggfw/ztfw/jy/jyjgyl/zxjy/mindex.html |
| 市执信中学(水荫路校区) | `gz-440104-1e9bdce3` | **CONFIRMED** | 2017 年专为执信初中部改建；执信校长 2023 明确「执信路+水荫路作为初中部，二沙岛为高中国际合作」。 | https://ep.ycwb.com/epaper/ycwb/resfile/2023-10-11/A12/ycwb20231011A12.pdf |
| 市执信中学(二沙岛国际校区) | `gz-440104-63c59c98` | **NON_MIDDLE** | 高中国际合作办学（AP/A-Level），不办义务教育初中。 | http://gzzk.gz.gov.cn/zwgk/zwdt/content/post_10365139.html |
| 市第十三中学(禺山校区) | `gz-440104-9b88f912` | **CONFIRMED** | 禺山校区(禺山路14号)即十三中初中部（文德路83号为高中/北校）。 | http://www.yuexiu.gov.cn/ggfw/ztfw/jy/jyjgyl/zxjy/content/mpost_8722030.html |
| 市第七中学(麓湖校区) | `gz-440104-028e64d6` | **NON_MIDDLE** | 2026-08-31 刚揭牌，官方定性「优质公办高中新阵地」，首年招高一 540 人；七中初中部在本部东山。 | http://www.yuexiu.gov.cn/gzjg/qzf/qjyj/jyzl/xw/yjkx/content/post_10992833.html |

## 四、C 类：黄埔（1 所）

| 实体名 | school_id | 判定 | 映射/关键说明 | 主要依据 URL |
|---|---|---|---|---|
| 市第二中学(科学城校区) | `gz-440112-b56cfdce` | **NON_MIDDLE** | 二中初中部在越秀应元路21号；科学城校区(黄埔水西路11号)＝高中部。 | https://www.gdgzez.com.cn/xxgk/xxjj |

## 五、C 类：天河（13 所）

| 实体名 | school_id | 判定 | 映射/关键说明 | 主要依据 URL |
|---|---|---|---|---|
| 市第七十五中学(燕塘东校区) | `gz-440106-5b430017` | **NON_MIDDLE** | 官方表：燕塘东＝高中部（燕岭路151号）。**与原任务备注「纯初中」相反**。 | https://www.thnet.gov.cn/zwgk/ggqsydwxxgkzl/jyly/wqzx/content/post_8724046.html |
| 市第七十五中学(天平架校区) | `gz-440106-621b20d3` | **CONFIRMED** | 官方表：天平架＝初中部（广州大道北498号）。 | 同上 |
| 广州中学(名雅校区) | `gz-440106-a989804b` | **CONFIRMED** | 官方：名雅/五山/天润为初中部，凤凰全部为高中。 | https://www.thnet.gov.cn/thdt/mtjj/content/post_9096906.html |
| 广州中学(凤凰校区) | `gz-440106-3c8afb6a` | **NON_MIDDLE** | 官方明确凤凰全部为高中。 | 同上 |
| 市第一一三中学(东方校区) | `gz-440106-b049d65a` | **CONFIRMED** | 东方＝初中部；官方新花城 2020：「金融城校区作高中部，东方校区和金融城西校区作初中部」。 | https://huacheng.gz-cmc.com/pages/2020/09/02/487361b1e6d54a28991062543599c192.html |
| 市第一一三中学(金融城校区) | `gz-440106-5f78f6a9` | **NON_MIDDLE** | 高中部；2026 市招考办以金融城校区招高中 430 人。 | https://gzzk.gz.gov.cn/zwgk/zkyw/content/post_10809554.html |
| 市第一一三中学(元岗校区) | `gz-440106-ced6bbff` | **NON_MIDDLE** | 2026 年 9 月启用、面向高中阶段招 500 人。 | https://www.nfnews.com/content/46NdV5e8ym.html |
| 市天河中学(花城校区) | `gz-440106-dd16c13e` | **CONFIRMED** | 官方表：花城＝初中部（猎德大道27号）。 | https://www.thnet.gov.cn/zwgk/ggqsydwxxgkzl/jyly/wqzx/content/post_8724046.html |
| 市天河中学(珠江新城校区) | `gz-440106-93897236` | **NON_MIDDLE** | 官方表：珠江新城＝高中部（华成路7号）。 | 同上 |
| 清华附中湾区学校 | `gz-440106-e32237e4` | **CONFIRMED** | 2026 派位方案：智谷 8 班 336 人＋智慧城 8 班 336 人，均招初一。 | https://www.thnet.gov.cn/thdt/mtjj/content/post_10794907.html |
| 市第八十九中学(北区) | `gz-440106-f94ad54a` | **未确认** | 89 中整体办初中（2026 划片 18 班），但「北区」官方仅为 2021 年投用的宿舍/食堂/体育馆扩建，从未被单列为初中教学区。建议核查：北区是否只是本部的配套扩建、实体是否应并入本部。 | http://www.thnet.gov.cn/thdt/mtjj/content/post_7851369.html |
| 执信中学(天河校区) | `gz-440106-22fcbcd6` | **CONFIRMED** | 2026 派位方案：执信天河总计划 10 班 420 人。 | https://www.thnet.gov.cn/thdt/mtjj/content/post_10794907.html |
| 华南师范大学附属中学(石牌校区) | `gz-440106-d5983217` | **NON_MIDDLE** | 石牌＝纯高中（2026 自招简章面向中考应届生）；华附义务教育初中部在**五山校区**（2026 派位名单即「五山校区」）。 | https://gzzk.gz.gov.cn:443/attachment/8/8020/8020626/10805491.pdf ；https://www.hsfz.net.cn/list_83/6815.html |

## 六、C 类：海珠（6 所）

| 实体名 | school_id | 判定 | 映射/关键说明 | 主要依据 URL |
|---|---|---|---|---|
| 市第四十一中学(南校区) | `gz-440105-13585057` | **NON_MIDDLE** | 2026 官方初中校区表 41 中仅列校本部(工业大道北101号)一行，无南/东校区。 | https://www.haizhu.gov.cn/gzhzjy/gkmlpt/content/10/10799/mpost_10799155.html |
| 市第四十一中学(东校区) | `gz-440105-b210556b` | **NON_MIDDLE** | 2024 年表东校区尚承担初一、初二，**2026 年初中已全部集中到校本部**；东校区 2024-12 官方扩建(1.4亿)转高中部。**旧线索「东校区=初中部」已过时。** | https://www.haizhu.gov.cn/gzjg/qzf/hzqjyj/zsgz/content/mpost_9632057.html ；https://www.haizhu.gov.cn/gzhzjy/gkmlpt/content/10/10799/mpost_10799155.html |
| 市新滘中学(土华校区) | `gz-440105-2f31776e` | **CONFIRMED** | 华洲路698号，2026 官方初中表与贵荣校区并列。 | https://www.haizhu.gov.cn/gzhzjy/gkmlpt/content/10/10799/mpost_10799155.html |
| 市第五中学(金碧校区) | `gz-440105-aec34da3` | **NON_MIDDLE** | 金恒路66号，2022 秋起只招高一；2026 初中表五中仅列本部南村路32号。初中在本部，金碧纯高中。 | https://www.haizhu.gov.cn/gzhzjy/gkmlpt/content/10/10799/mpost_10799155.html ；https://ep.ycwb.com/epaper/xkb/h5/html5/2023-04/14/content_1511_567322.htm |
| 市南武中学(岭南画派纪念校区) | `gz-440105-dd2723fc` | **CONFIRMED** | ＝玫瑰二街12号（表中「岭南校区」），2026 承担初一、初三（兼高中）。 | https://www.haizhu.gov.cn/gzhzjy/gkmlpt/content/10/10799/mpost_10799155.html |
| 市第九十七中学(江南新苑校区) | `gz-440105-ed868139` | **CONFIRMED** | 晓港东横街12号，2026 承担初一、初二（兼高中）。 | https://www.haizhu.gov.cn/gzhzjy/gkmlpt/content/10/10799/mpost_10799155.html |

---

## 七、给落库的清单（供 MainAgent 决策）

**建议进 `CONFIRMED_CAMPUS` 白名单（21 所）：**
- 荔湾：省实荔湾(初中部一期) `1d99218d`、西关培英(西校区) `41cb6344`、四中(康园) `4cda3f9e`、南海(初中部) `8e11a7d3`
- 白云：白云中学(法人行) `e74c2e1d`、广外实验(北校区) `f751344d`、空港实验(建南) `150715c8`、龙归(初中部) `4c9a3eaa`
- 越秀：十七中(西校区) `099a5868`⚠️、育才(东校区) `191aaa35`、执信(水荫路) `1e9bdce3`、十三中(禺山) `9b88f912`
- 天河：75中(天平架) `621b20d3`、广州中学(名雅) `a989804b`、113中(东方) `b049d65a`、天河中学(花城) `dd16c13e`、清华附中湾区 `e32237e4`、执信(天河) `22fcbcd6`
- 海珠：新滘(土华) `2f31776e`、南武(岭南画派) `dd2723fc`、97中(江南新苑) `ed868139`

**建议进 `NON_MIDDLE_CAMPUS`（删 middle 留 high，21 所）：**
- 荔湾：真光(本部) `2b8081bc`、真光(广钢) `04c54db8`、真光(汾水) `882931a0`
- 白云：白云中学(南) `15fa03a9`、白云中学(北) `5849b586`、65中(江高) `218475ea`、培英(云城) `730c7404`、省实(云城) `3405d87e`
- 越秀：省实越秀(盘福) `089a2a5b`、执信(二沙岛国际) `63c59c98`、七中(麓湖) `028e64d6`
- 黄埔：二中(科学城) `b56cfdce`
- 天河：75中(燕塘东) `5b430017`、广州中学(凤凰) `3c8afb6a`、113中(金融城) `5f78f6a9`、113中(元岗) `ced6bbff`、天河中学(珠江新城) `93897236`、华附(石牌) `d5983217`
- 海珠：41中(南) `13585057`、41中(东) `b210556b`、5中(金碧) `aec34da3`

**未确认（1 所，建议人工）：**
- 89中(北区) `f94ad54a`：学校整体办初中，但「北区」仅为宿舍/食堂/体育馆配套扩建，无官方文件把它定为初中教学区 → 建议人工判定该实体是否应并入本部或删除。

## 八、需项目侧注意的纠偏点
1. **多处与原任务备注相反**：75中燕塘东（备注纯初中→实纯高中）、75中天平架（备注完中→实初中部）；真光「本部校区」实体＝培真路17号**高中本部**，官方「初中部本部校区」在鹤洞路98号（实体表应另立 POI）。
2. **省实(云城校区) 是小学部**（非中学部），办初中的是「白云校区」——实体名误导。
3. **四中康园**：用户提供的抖音百科(2021)「初中部(津园/逸园/虬园/康园)」与官方 2023 名额分配「010324 四中(初中康园校区)」互证，判 CONFIRMED；系民办聚贤校区故不进公办派位。
4. **十七中西校区** 2026-08 起整体临迁培正矿泉学校，虽仍为初中校区但办学主体临时变更，挂载白名单时留意。
5. **41 中初中 2026 已集中到校本部(工业大道北101号)**，东/南校区均转高中；而「校本部」在当前待确认实体清单中缺失，建议另立初中实体。
6. 所有依据 URL 均真实可溯源（区政府/教育局/市招考办/学校官网/官方媒体）；仅四中康园一处以抖音百科(2021)作兜底佐证且有官方名额分配文件直接佐证。
