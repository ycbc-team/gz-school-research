# src/ — 人工维护的源数据

本目录放置**人工维护、不可由脚本重新推导**的源数据与口径说明（如有）。

当前状态：广工 2024 名单来自官方 PDF（`raw/gdut_2024_enrollment.pdf`），由
`scripts/parse_gdut_pdf.py` 自动解析，无需人工源；43 所区属示范名单取自
`apps/web/src/data/compact/high/level/src/levels.js`，不复制到本目录（保持单源）。

若后续新增人工录入数据（如逐校喜报原文摘录、媒体报道 URL 归档），应放在此处，并在
`README.md` 中登记。
