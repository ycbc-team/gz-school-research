# 越秀区（adcode=440104）民办中小学名单核实与实体匹配清单

> 生成时间：2026-09-14
> 数据基准：越秀区教育局 2025 年、2026 年义务教育学校招生计划（越教字〔2025〕25号、越教字〔2026〕26号）
> 实体表：`data/registry/entity/dist/entities.json`（越秀区共 145 条，本次从 0 所民办开始补齐）

## 核心结论

- 越秀区**民办初中 4 所**：名德实验、海印实验、汇泉学校（中学部）、雄鹰学校（中学部）。
- 越秀区**民办小学 2 所**：雄鹰学校（小学部）、汇泉学校（小学部）。
- 越秀区**无民办高中**（市教育局明确：越秀区是全市唯一没有民办高中的区，5050 个普高学位全部公办）。
- 历史知名民办校（育才实验、二中应元）均已于 2022 年"公参民"脱钩中**转公**；四中聚贤、真光实验、香江中学等均不在越秀区辖内。

---

## 一、确认民办且实体表已存在（新增 nature 标记）

| school_id | name | stage | 来源URL | 备注 |
|---|---|---|---|---|
| gz-440104-cc4aa5b8 | 广州市越秀区名德实验学校 | middle | https://www.yuexiu.gov.cn/attachment/7/7805/7805489/10237601.pdf ；http://www.yuexiu.gov.cn/gzyxjy/gkmlpt/content/10/10790/mpost_10790617.html | 民办初中，2025/2026 年招 6 个班；地址越秀区一德路旧部前街56号之三；越秀区政府网站标"九年一贯制"，但近年民办小学招生计划中无该校小学部，实际仅以初中招生 |
| gz-440104-4d39b625 | 广州海印实验学校 | middle | https://www.yuexiu.gov.cn/attachment/7/7805/7805489/10237601.pdf ；http://www.yuexiu.gov.cn/gzyxjy/gkmlpt/content/10/10790/mpost_10790617.html | 民办初中（原广州培道实验学校），2025/2026 年招 4 个班；地址越秀区回龙路4-2号；非营利全日制全寄宿初级中学，**无小学部** |
| gz-440104-1f2d5df9 | 越秀区汇泉学校 | middle | https://www.yuexiu.gov.cn/attachment/7/7805/7805489/10237601.pdf ；http://www.yuexiu.gov.cn/gzyxjy/gkmlpt/content/10/10790/mpost_10790617.html | 民办九年一贯制学校中学部，2025/2026 年招 4 个班；地址越秀区矿泉街北站路144号（御景花园对面）；2017 年起由广州十六中托管 |
| gz-440104-1f2d5df9 | 越秀区汇泉学校 | primary | https://www.yuexiu.gov.cn/attachment/7/7805/7805489/10237601.pdf ；http://www.yuexiu.gov.cn/gzyxjy/gkmlpt/content/10/10790/mpost_10790617.html | 民办九年一贯制学校小学部，2025/2026 年招 4 个班 |
| gz-440104-db01d10e | 雄鹰学校 | middle | https://www.yuexiu.gov.cn/attachment/7/7805/7805489/10237601.pdf ；http://www.yuexiu.gov.cn/gzyxjy/gkmlpt/content/10/10790/mpost_10790617.html | 民办九年一贯制学校中学部，2025/2026 年招 2 个班；地址越秀区广园路云泉路163号大院；主要招收随迁子女 |
| gz-440104-714a8af4 | 广州至灵学校 | primary | 学校章程 https://www.zlschool.com.cn/?page_id=608 ；广东省残联特殊教育学校一览 https://www.gddpf.org.cn/ywzc/jyjy/jy/content/post_595450.html | 民办非营利特殊教育康复机构（1985 年创办，小学部/初中部/职高班），面向 6-18 岁智障/孤独症儿童，非普通小学地段招生；2026-09-22 越秀 POI 未匹配核实补标（官方民办小学计划未含，特教渠道报名） |

> 说明：以上 5 条实体记录的 `nature` 字段当前为空（match_school.py 显示"公办(未标)"为缺省态），应统一补标为 `民办`。

---

## 二、确认民办但实体表不存在（需先补实体再标记）

| 官方校名 | 学段 | 来源URL | 建议实体name | 备注（含地址/坐标线索如有） |
|---|---|---|---|---|
| 广州市越秀区雄鹰学校（小学部） | primary | https://www.yuexiu.gov.cn/attachment/7/7805/7805489/10237601.pdf ；http://www.yuexiu.gov.cn/ggfw/ztfw/jy/jyjgyl/zxjy/content/post_8739325.html | 广州市越秀区雄鹰学校(小学部) | 与中学部共用同一校址：越秀区广园路云泉路163号大院（高德坐标约 113.2987,23.1582）；2025/2026 年小学部招 4 个班；实体表现有 gz-440104-db01d10e 仅为 middle 阶段，需新增 primary 阶段实体（建议 school_id 续编为 gz-440104-<新8位hex>，aliases 含"越秀区雄鹰学校小学部""雄鹰学校小学部"） |

---

## 三、待核实（性质不确定或名称无法匹配）

| 校名 | 来源URL | 待核实原因 |
|---|---|---|
| 广州海印实验学校（primary 阶段实体 gz-440104-4d39b625） | https://jiaoshi.com.cn/school/cmmz7j4st106pgs8sa7mq7cmh ；http://zs.gzeducms.cn//u/cms/www/file/mbcz/2024/1.pdf | 实体表中同一 school_id 下挂了 primary + middle 两个 stage，但海印实验官方明确为"非营利民办全日制全寄宿**初级中学**"，2022-2026 年民办小学招生计划中均无该校。该 primary 阶段实体疑似历史误植，建议后续从实体表清理或在 nature 标注时备注"仅认 middle 为民办"，**本次未在第一节列出该 primary 行**，待项目 owner 决定是否删除该误植实体 |
| 广州市越秀区名德实验学校（小学部） | http://www.yuexiu.gov.cn/ggfw/ztfw/jy/jyjgyl/xxjy/mindex.html ；http://www.gzmdsy.com/gzmdsy/html/2/c21.htm | 越秀区政府网站将名德实验列在"小学教育"栏目并称"九年一贯制"，但 2025/2026 年官方民办小学招生计划中无名德实验小学部，学校官网近年招生公告也以初中/插班生为主。疑似曾有小学部但近年停招小一，**实体表中也无 primary 阶段实体**，暂不新增，待核实是否仍在办小学 |

---

## 四、已排除（经查实为公办或已民转公）

| 校名 | 排除原因 | 来源URL |
|---|---|---|
| 广州市越秀区育才实验学校（gz-440104-ff8d7e05, middle） | 2022 年"公参民"脱钩中转公，现为越秀区属公办寄宿制初级中学，列入 2025/2026 年公办初中招生计划第 21 位 | https://static.nfapp.southcn.com/content/202207/08/c6667024.html?enterColumnId=94 ；https://www.yuexiu.gov.cn/attachment/7/7805/7805489/10237601.pdf |
| 广州市越秀区二中应元学校 | 2022 年转公并入广州二中初中部，2022 年起不再以"二中应元"名义招生；原场地 2023 年改为小北路小学应元校区（实体表 gz-440104-1b6d4b9c 已记为公办小学） | https://ep.ycwb.com/epaper/ycwb/html/2022-08/30/content_3_521180.htm ；https://static.nfapp.southcn.com/content/202207/08/c6667024.html?enterColumnId=94 |
| 广州市第四中学聚贤中学 | 位于**荔湾区**（非越秀区辖），2022 年转公为广州市第四中学初中雁园校区 | http://news.ycwb.com/2022-08/30/content_41012399.htm |
| 广州市真光实验学校 | 位于**荔湾区**（非越秀区辖），2022 年转公为广州市真光中学初中部实验校区 | http://news.ycwb.com/2022-08/30/content_41012399.htm ；https://static.nfapp.southcn.com/content/202310/19/c8211284.html?enterColumnId=38 |
| 广州市香江中学 | 位于**增城区**翡翠绿洲小区（非越秀区辖），虽历史上由越秀区育才实验学校托管至 2022 年，但校址不在越秀区 | https://shangnaxue.net/school/1267794205588176897.html ；https://m.k12zx.com/new/41344.html |
| 越秀区民办高中（任何校名） | 越秀区是全市唯一没有民办高中的区，2025 年 5050 个普高学位全部为公办性质 | https://jyj.gz.gov.cn/gk/zfxxgkml/gzdt/content/post_10271256.html |

---

## 附：核实依据与方法

1. **一手官方来源**（优先级最高）：
   - 越秀区教育局《2025 年越秀区义务教育学校招生计划》（越教字〔2025〕25号）：https://www.yuexiu.gov.cn/attachment/7/7805/7805489/10237601.pdf
   - 越秀区教育局《2026 年越秀区义务教育学校招生计划》（越教字〔2026〕26号）：http://www.yuexiu.gov.cn/gzyxjy/gkmlpt/content/10/10790/mpost_10790617.html
   - 越秀区 2025 年民办初中电脑摇号结果（明确"越秀区民办学校共 4 所"）：http://www.yuexiu.gov.cn/gzjg/qzf/qjyj/jyzl/gk/zxjyxx/content/post_10539270.html
   - 越秀区 2025 年度局管民办学校年检结论（4 所民办中小学，与招生计划名单完全吻合）：http://news.dayoo.com/gzrbrmt/202607/23/170639_54982963.htm
   - 广州市教育局关于越秀区无民办高中的表述：https://jyj.gz.gov.cn/gk/zfxxgkml/gzdt/content/post_10271256.html

2. **辅助可信来源**：
   - 广州市义务教育学校招生报名系统民办初中/小学报名数据：https://zs.gzeducms.cn/u/cms/www/file/mbcz/2025/C34752DA039423DE2E063C81CA8C01E5A.pdf
   - 越秀区教育局民办学校教师从教津贴公示（雄鹰、汇泉均被官方认定为"义务教育阶段九年一贯制民办学校"）：http://www.yuexiu.gov.cn/gzjg/qzf/qjyj/jyzl/gk/xxtg/content/post_10436009.html

3. **实体匹配方式**：对每所确认民办校使用 `python3 scripts/registry/match_school.py 440104 "<校名>"`，并辅以在 `entities.json` 中按关键词 grep 校验别名。

## 待办（给项目 owner）

- [ ] 将第一节 5 条实体记录的 `nature` 字段补标为 `民办`。
- [ ] 第二节新增"雄鹰学校小学部" primary 阶段实体（地址：云泉路163号大院）。
- [ ] 第三节两个待核实项：海印实验 primary 误植实体是否清理；名德实验小学部是否仍在办。
