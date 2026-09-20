# 人工校正层（src/）

唯一允许人工修改的层。用于修正脚本解析/匹配的误差。

## 文件

- `overrides.json`：黑白名单校正。
  - `blacklist`：脚本误收 → 从 compiled 移除。每条 `{school_id, reason, evidence_url}`
  - `whitelist`：脚本漏收 → 补入。每条 `{school_id, metric, value, year, reason, evidence_url}`

## 纪律

- 每条校正必须附 `reason`（为什么脚本错了）和 `evidence_url`（政府/学校官网依据）
- CR 时逐条过；无依据的校正不合并
- 脚本升级后应回归：能解析的不再走人工
