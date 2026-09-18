#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性原子应用本轮全部 UI 稿改动（避免多编辑互相覆盖）。"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(os.path.dirname(HERE), 'school-search-ui-spec.html')  # docs/design/school-search-ui-spec.html
s = open(P, encoding='utf-8').read()

BACK = ('<span class="back"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M15 5l-7 7 7 7"></path></svg></span>')

R = []

# ============ CSS ============
R.append(('CSS · filterrow 等宽铺满',
    '.filterrow{display:flex;gap:8px;overflow:hidden}',
    '/* 筛选栏：3 个胶囊等宽铺满，左右边缘与搜索框严格对齐 */\n'
    '.filterrow{display:flex;gap:8px}\n'
    '.filterrow .chip{flex:1;min-width:0;justify-content:center;padding:0 8px}', 1))

R.append(('CSS · searchhead 返回按钮 40×40',
    '.searchhead{height:52px;flex:none;display:flex;align-items:center;gap:10px;padding:0 14px;border-bottom:1px solid var(--line-2)}\n'
    '.searchhead .back{font-size:22px;color:var(--ink-700);line-height:1;flex:none;font-weight:300}',
    '.searchhead{height:56px;flex:none;display:flex;align-items:center;gap:9px;padding:0 12px;border-bottom:1px solid var(--line-2)}\n'
    '.searchhead .back{width:40px;height:40px;border-radius:50%;background:var(--bg);border:1px solid var(--line);display:flex;align-items:center;justify-content:center;color:var(--ink-900);flex:none}', 1))

R.append(('CSS · 历史记录胶囊平铺',
    '.sug .srow .nm{font-size:14px}',
    '.sug .srow .nm{font-size:14px}\n'
    '/* 历史记录：胶囊平铺（一个圈一个圈），不再一行一条 */\n'
    '.pillwrap{display:flex;flex-wrap:wrap;gap:8px}\n'
    '.pill{display:inline-flex;align-items:center;max-width:100%;height:32px;padding:0 12px;border-radius:999px;background:var(--bg);border:1px solid var(--line);font-size:12.5px;color:var(--ink-700);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}', 1))

R.append(('CSS · 半窗返回按钮 40×40',
    '.sheet .sheettop{display:flex;align-items:center;gap:10px;padding:0 14px 12px}\n'
    '.sheet .sheettop .back{font-size:22px;line-height:1;color:var(--ink-700);font-weight:300;flex:none}',
    '.sheet .sheettop{display:flex;align-items:center;gap:9px;padding:0 14px 12px}\n'
    '.sheet .sheettop .back{width:40px;height:40px;border-radius:50%;background:var(--bg);border:1px solid var(--line);display:flex;align-items:center;justify-content:center;color:var(--ink-900);flex:none}', 1))

R.append(('CSS · 半窗维度胶囊等宽（与搜索栏同边距）',
    '.sheet .dims{display:flex;gap:8px;padding:0 16px 12px;border-bottom:1px solid var(--line-2);overflow:hidden}',
    '/* 半窗内的维度胶囊：与上方搜索栏同一左右边距 → 等宽对齐 */\n'
    '.sheet .dims{display:flex;gap:8px;padding:0 14px 12px;border-bottom:1px solid var(--line-2)}\n'
    '.sheet .dims .chip{flex:1;min-width:0;justify-content:center;padding:0 8px}', 1))

R.append(('CSS · 选项分组竖排 optgrp',
    '.sheet .opts{display:flex;flex-wrap:wrap;gap:9px}',
    '.sheet .opts{display:flex;flex-wrap:wrap;gap:9px}\n'
    '/* 选项分组竖排：每组一个标题，组内选项平铺（学段维度用） */\n'
    '.sheet .optgrp{margin-bottom:16px}\n'
    '.sheet .optgrp:last-child{margin-bottom:0}\n'
    '.sheet .optgrp .ghd{font-size:13px;font-weight:600;color:var(--ink-700);margin-bottom:8px}', 1))

# ============ HTML ============
R.append(('HTML · 4 个返回按钮换 40×40 圆形 SVG',
    '<span class="back">&#8249;</span>', BACK, 4))

R.append(('HTML · 历史记录 → 胶囊平铺',
    '            <div class="shd"><b>历史记录</b><span class="clr">清空</span></div>\n'
    '            <div class="slist">\n'
    '              <div class="srow"><span class="nm">广州市第六中学（海珠校区）</span></div>\n'
    '              <div class="srow"><span class="nm">广州市第六中学（海珠校区）</span></div>\n'
    '              <div class="srow"><span class="nm">广州市第六中学（海珠校区）</span></div>\n'
    '            </div>',
    '            <div class="shd"><b>历史记录</b><span class="clr">清空</span></div>\n'
    '            <div class="pillwrap">\n'
    '              <span class="pill">广州市第六中学（海珠校区）</span>\n'
    '              <span class="pill">东风东路小学（东风广场校区）</span>\n'
    '              <span class="pill">广州市东风东教育集团番禺小学</span>\n'
    '              <span class="pill">东风东路小学</span>\n'
    '              <span class="pill">东风东教育集团（核心校）</span>\n'
    '              <span class="pill">东风东路小学（锦城校区）</span>\n'
    '            </div>', 1))

R.append(('HTML · 学段选项 → 分组竖排',
    '          <div class="optwrap">\n'
    '            <div class="opts">\n'
    '              <span class="opt on">小学</span>\n'
    '              <span class="opt on">初中</span>\n'
    '              <span class="opt on">高中</span>\n'
    '            </div>\n'
    '          </div>',
    '          <div class="optwrap">\n'
    '            <div class="optgrp">\n'
    '              <div class="ghd">小学</div>\n'
    '              <div class="opts"><span class="opt on">小学</span></div>\n'
    '            </div>\n'
    '            <div class="optgrp">\n'
    '              <div class="ghd">初中</div>\n'
    '              <div class="opts"><span class="opt on">初中</span></div>\n'
    '            </div>\n'
    '            <div class="optgrp">\n'
    '              <div class="ghd">高中</div>\n'
    '              <div class="opts">\n'
    '                <span class="opt on">省市属示范</span>\n'
    '                <span class="opt on">区属示范</span>\n'
    '                <span class="opt on">其他学校</span>\n'
    '              </div>\n'
    '            </div>\n'
    '          </div>', 1))

R.append(('HTML · 地图层详情卡盖住导航 tab（换顺序）',
    '        <div class="bottomdock">\n'
    '          <div class="cardbot">\n'
    '            <div class="handle"></div>\n'
    '            <div class="cbtop">\n'
    '              <span class="nm">广州市第六中学（海珠校区）</span>\n'
    '            </div>\n'
    '            <div class="cbtags">\n'
    '              <span class="tag m tag-dist">海珠区</span>\n'
    '              <span class="tag m tag-stage">高中</span>\n'
    '              <span class="tag m tag-demo">示范性高中</span>\n'
    '              <span class="tag m tag-nature">公办</span>\n'
    '            </div>\n'
    '            <div class="cbrow">\n'
    '              <span>点击点位查看，选中点位高亮</span>\n'
    '              <span class="cbmore">展开详情</span>\n'
    '            </div>\n'
    '          </div>\n'
    '          <div class="navdock inline">\n'
    '            <span class="np on">首页</span><span class="np">政策</span>\n'
    '          </div>\n'
    '        </div>',
    '        <div class="bottomdock">\n'
    '          <div class="navdock inline">\n'
    '            <span class="np on">首页</span><span class="np">政策</span>\n'
    '          </div>\n'
    '          <div class="cardbot">\n'
    '            <div class="handle"></div>\n'
    '            <div class="cbtop">\n'
    '              <span class="nm">广州市第六中学（海珠校区）</span>\n'
    '            </div>\n'
    '            <div class="cbtags">\n'
    '              <span class="tag m tag-dist">海珠区</span>\n'
    '              <span class="tag m tag-stage">高中</span>\n'
    '              <span class="tag m tag-demo">示范性高中</span>\n'
    '              <span class="tag m tag-nature">公办</span>\n'
    '            </div>\n'
    '            <div class="cbrow">\n'
    '              <span>点击点位查看，选中点位高亮</span>\n'
    '              <span class="cbmore">展开详情</span>\n'
    '            </div>\n'
    '          </div>\n'
    '        </div>', 1))

# ============ 说明 / 规范文案 ============
R.append(('文案 · 搜索页 anno',
    '          · 搜索栏：返回按钮、默认搜索词（支持广州小初高学校搜索）、搜索按钮；<em>无输入时搜索按钮置灰不可点</em>。<br>\n'
    '          · 历史记录区：有搜索词条时才展示；按搜索时间由近及远；右侧「清空」点击后弹窗确认。<br>',
    '          · 搜索栏：返回按钮、默认搜索词（支持广州小初高学校搜索）、搜索按钮；<em>无输入时搜索按钮置灰不可点</em>。<br>\n'
    '          · <em>返回按钮</em>为 40×40 圆形控件（浅底 + 描边 + 20 线性箭头），点击区 ≥ 40。<br>\n'
    '          · 历史记录区：有搜索词条时才展示；按搜索时间由近及远；<em>以胶囊平铺、自动换行的方式呈现</em>（一条一个圈），不再是整行一条的列表；右侧「清空」点击后弹窗确认。<br>', 1))

R.append(('文案 · 学段 anno',
    '          · 点「学段」chips：该 chips 变为<em>展开中</em>态，下方<em>行政区选项整组替换为学段选项</em>（小学／初中／高中）。<br>',
    '          · 点「学段」chips：该 chips 变为<em>展开中</em>态，下方<em>行政区选项整组替换为学段选项</em>。<br>\n'
    '          · 学段选项按交互稿<em>分组竖排</em>：每组一个标题、组内选项平铺 —— 小学 → [小学]；初中 → [初中]；高中 → [省市属示范][区属示范][其他学校]。<br>', 1))

R.append(('文案 · 地图层 anno',
    '          · 左下角为<em>学校类型图例</em>；点击具体学校，<em>底部展示学校详情卡</em>，选中点位有选中态。',
    '          · 左下角为<em>学校类型图例</em>；点击具体学校，<em>底部展示学校详情卡</em>，选中点位有选中态。<br>\n'
    '          · <em>详情卡为最上层</em>：整层盖住底部区域，<em>底部导航 tab 被遮挡在卡片之下</em>（收起卡片后才露出）。', 1))

R.append(('文案 · 规范表 筛选栏入口',
    '<tr><td>筛选栏入口</td><td>首页 / 地图层搜索框下方，共 3 个，同为悬浮层</td><td>胶囊 高 32；维度顺序 <b>行政区／学段／办学性质</b>；多选显示维度名，单选显示选中内容；展开中为浅蓝底 #F2F6FE；白底 94% + 投影</td></tr>',
    '<tr><td>筛选栏入口</td><td>首页 / 地图层搜索框下方，共 3 个，同为悬浮层</td><td>胶囊 高 32；维度顺序 <b>行政区／学段／办学性质</b>；<b>3 个胶囊等宽铺满一行，左右边缘与搜索框严格对齐</b>（半窗内与搜索栏同边距）；多选显示维度名，单选显示选中内容；展开中为浅蓝底 #F2F6FE；白底 94% + 投影</td></tr>', 1))

R.append(('文案 · 规范表 筛选选项',
    '<tr><td>筛选选项</td><td>半窗内，默认全选</td><td>胶囊 高 34；选中 #F2F6FE 底 + #98B6EC 描边 + #254BAE 字并加粗；未选白底描边</td></tr>',
    '<tr><td>筛选选项</td><td>半窗内，默认全选</td><td>胶囊 高 34；选中 #F2F6FE 底 + #98B6EC 描边 + #254BAE 字并加粗；未选白底描边。学段维度按交互稿<b>分组竖排</b>：组标题 13/600 + 组内胶囊平铺（小学／初中各 1 项；高中组含 省市属示范・区属示范・其他学校）</td></tr>', 1))

R.append(('文案 · 规范表 新增返回按钮/历史记录行',
    '<tr><td>搜索按钮</td><td>搜索栏右侧</td><td>无输入置灰 #DCE2EC/#98A2B6 不可点；有输入变知性蓝主按钮 #2F5CD6</td></tr>',
    '<tr><td>搜索按钮</td><td>搜索栏右侧</td><td>无输入置灰 #DCE2EC/#98A2B6 不可点；有输入变知性蓝主按钮 #2F5CD6</td></tr>\n'
    '        <tr><td>返回按钮</td><td>搜索页 / 筛选半窗左上角</td><td><b>40×40 圆形</b>控件：浅底 #F5F7FB + 1px #E3E8F0 描边，内置 20×20 线性箭头（描边 2.4），点击区 ≥ 40</td></tr>\n'
    '        <tr><td>历史记录</td><td>搜索页 · 默认态</td><td><b>胶囊平铺</b>（<span class="mono">flex-wrap</span> 自动换行，一条一个圈），不再整行一条；胶囊 高 32、r=999、#F5F7FB 底 + #E3E8F0 描边、12.5px；超长名称单行省略</td></tr>', 1))

R.append(('文案 · 规范表 学校卡层级',
    '<tr><td>学校卡</td><td>地图层底部（点选点位后）</td><td>白底 + 上投影、上圆角 18，顶部带拖拽 handle；校名 16/600；标签行用中标签；底部分隔线 + 「展开详情」浅蓝胶囊</td></tr>',
    '<tr><td>学校卡</td><td>地图层底部（点选点位后）</td><td>白底 + 上投影、上圆角 18，顶部带拖拽 handle；校名 16/600；标签行用中标签；底部分隔线 + 「展开详情」浅蓝胶囊。<b>层级为最上层</b>：整层盖住底部区域，<b>底部导航栏被压在卡片之下</b></td></tr>', 1))

# ---------- 执行 ----------
fails = []
for label, old, new, want in R:
    got = s.count(old)
    if got == 0 and s.count(new) >= 1:
        print(f'  跳过（已是新内容）: {label}')
        continue
    if got != want:
        fails.append(f'{label}: 期望 {want} 处，实际 {got} 处')
        continue
    s = s.replace(old, new)

if fails:
    print('=== 有替换未命中，已中止，不写盘 ===')
    for f in fails:
        print(' ', f)
    sys.exit(1)

open(P, 'w', encoding='utf-8').write(s)
print(f'全部 {len(R)} 组替换成功，已写盘。')
for k in ['.filterrow .chip{flex:1', 'pillwrap', 'optgrp', 'class="back"><svg',
          'bottomdock .navdock.inline', '被压在卡片之下', '40×40 圆形控件']:
    print(f'  校验 {k:34} {s.count(k)}')
