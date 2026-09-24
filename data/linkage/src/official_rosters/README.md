# 官方学校名录（区级全量基线）

用途：对所在区**所有中学**做全量校验（不只孤儿待办清单），识别实体表缺失/错配。
采集自官方政府/教育局公开页面，每份带 source_url 与发布时间；后续如更新以最新版替换并注明。

| 文件 | 覆盖 | 官方来源 |
|---|---|---|
| `tianhe_wqzx_2022.json` | 天河区完全中学 10 所（2022 表，2023-02-20 发布） | https://www.thnet.gov.cn/zwgk/ggqsydwxxgkzl/jyly/wqzx/content/post_8724046.html |
| `liwan_gongban_cz_2025.json` | 荔湾区公办初中 20 序号（2025-07-22 发布） | http://www.lw.gov.cn/zwgkk/zdlyxxgk/jyxx/czjy/content/post_10365715.html |

说明：
- 天河表为**完全中学**（非全区初中全量），学段标注优先取官方地址内注明（如「初中部天河东」），
  未注明的按 2026-09-17 联网核实结论补 `stage_verified` 字段（来源见 outputs/campus_middle_webverify_20260917.md）。
- 荔湾表为**公办初中**（民办初中不在内，如四中康园=民办聚贤初中部，属正常缺席）。
