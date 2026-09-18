#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 UI 稿按「移动端可读宽度」逐块渲染成 PNG，并同步到画廊目录。

用法（在项目内任意位置运行均可）：
    python docs/design/scripts/render_mobile.py                 # 渲染全部 11 块
    BLOCKS="05_screen,09_spec_table" python docs/design/scripts/render_mobile.py  # 只渲染指定块

说明：
    - 中间产物（每块 html/png、chrome prof_*）写在 OUT（默认 /tmp/proto/m，可自动重建）。
    - 最终画廊用图同步到 docs/design/ui-mockup-web/images/，文件名已由 GALLERY 映射为
      英文短名，对应 ui-mockup-web/index.html 里的 images/*.png 引用。
    - 这些 images/*.png 是「构建产物」，已在 docs/design/.gitignore 中排除，不进 git。
"""
import os, re, subprocess, sys, shutil, json
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGN = os.path.dirname(HERE)                        # .../docs/design
SRC = os.path.join(DESIGN, 'school-search-ui-spec.html')
IMAGES = os.path.join(DESIGN, 'ui-mockup-web', 'images')
OUT = os.environ.get('RENDER_OUT', '/tmp/proto/m')    # 中间产物目录（可重建）
os.makedirs(OUT, exist_ok=True)
os.makedirs(IMAGES, exist_ok=True)

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

# 块名(脚本自动生成) -> 画廊引用名(英文短名，对应 index.html 的 images/*.png)
# 注意：块名由 spec.html 里的 frame 标题推导，若改动标题需同步更新此处键名。
GALLERY = {
    '01_cover': 'cover',
    '02_base_color': 'base_color',
    '03_base_button': 'base_button',
    '04_base_tag': 'base_tag',
    '05_screen_01_首页_地图层_': 'screen01_home_map',
    '05_screen_02_搜索页_默认态': 'screen02_search_default',
    '05_screen_03_搜索页_联想词态': 'screen03_search_suggest',
    '05_screen_04_筛选栏半窗_状态_A': 'screen04_filter_A',
    '05_screen_05_筛选栏半窗_状态_B': 'screen05_filter_B',
    '05_screen_06_地图层': 'screen06_map',
    '09_spec_table': 'spec_table',
}

html = open(SRC, encoding='utf-8').read()
head = html[:html.index('<body')]
body = html[html.index('<body'):]

OVERRIDE = """
<style>
/* ===== 移动端渲染覆盖（仅用于出图，不改源文件） ===== */
html,body{background:#fff !important}
body{width:480px !important;margin:0 !important;padding:18px 16px !important;font-size:14px}
.wrap{max-width:none !important;padding:0 !important}
section{padding:0 !important;margin:0 !important}
.hero{background:#fff !important;border:none !important;padding:0 !important}
#screens .frames{display:block !important}
.frame{margin:0 0 26px !important}
.frame .cap,.frame .anno{width:100% !important;max-width:430px;margin-left:auto;margin-right:auto}
.grid2{display:block !important}
.card{margin-bottom:14px}
.card{padding:16px !important}
/* 规范表 → 移动端卡片式堆叠 */
table{display:block;width:100%}
thead{display:none}
tbody{display:block}
tr{display:block;padding:12px 14px;border-bottom:1px solid var(--line)}
tr:last-child{border-bottom:none}
td{display:block;border:none !important;padding:0 !important}
td:nth-child(1){font-size:13px;font-weight:700;color:var(--ib-600);margin-bottom:4px}
td:nth-child(2){font-size:12px;color:var(--ink-700);margin-bottom:7px;line-height:1.65}
td:nth-child(3){font-size:12px;color:var(--ink-500);line-height:1.7;background:var(--bg);border-radius:8px;padding:8px 10px}
/* 色例图例行：移动端允许换行，避免单字被压成竖排 */
.colrow{flex-wrap:wrap !important;gap:8px 14px !important;align-items:center !important}
.colrow span{display:inline-flex;align-items:center;gap:5px;white-space:nowrap}
.colrow span:last-child{flex-basis:100%;white-space:normal;line-height:1.7;margin-top:2px}
</style>
</head>"""


def extract(html_str, start):
    """从 start（指向一个 '<div' 或 '<header'）返回配平的整块。"""
    m = re.match(r'<(\w+)', html_str[start:])
    tag = m.group(1)
    depth = 0
    i = start
    pat = re.compile(r'</?%s\b[^>]*>' % tag)
    for mm in pat.finditer(html_str, start):
        if mm.group(0).startswith('</'):
            depth -= 1
            if depth == 0:
                return html_str[start:mm.end()]
        else:
            depth += 1
    raise ValueError('unbalanced: ' + html_str[start:start + 60])


def find_all(s, needle):
    return [m.start() for m in re.finditer(re.escape(needle), s)]


blocks = []  # (name, caption, html)

# 1 封面
hero = body.index('<header class="hero">')
blocks.append(('01_cover', '封面', extract(body, hero)))

# 2 设计基础三张卡
sec1 = body[body.index('<section class="wrap">'):body.index('id="screens"')]
cards = [extract(sec1, p) for p in find_all(sec1, '<div class="card"')]
names = ['02_base_color', '03_base_button', '04_base_tag']
caps = ['设计基础 · 主题色阶（知性蓝）', '设计基础 · 小程序按钮与控件体系', '设计基础 · 通用标签样式（Tag）']
for n, c, card in zip(names, caps, cards):
    blocks.append((n, c, card))
print('基础卡数量:', len(cards))

# 3 六屏
sec_screens = body[body.index('id="screens"'):]
sec_screens = sec_screens[:sec_screens.index('</section>')]
frames = [extract(sec_screens, p) for p in find_all(sec_screens, '<div class="frame">')]
for f in frames:
    cap = re.search(r'<div class="cap"><b>(.*?)</b>', f)
    label = re.sub(r'<[^>]+>', '', cap.group(1)) if cap else '?'
    name = re.sub(r'[^\w]+', '_', label)[:28]
    blocks.append(('05_screen_' + name, label, f))
print('屏数量:', len(frames))

# 4 规范表
sec_spec = body[body.rindex('<section class="wrap">'):]
sec_spec = sec_spec[:sec_spec.rindex('</section>') + len('</section>')]
blocks.append(('09_spec_table', '组件与交互规范', sec_spec))

doc_head = head.replace('</head>', OVERRIDE)
manifest = []
for name, caption, blk in blocks:
    p = os.path.join(OUT, name + '.html')
    open(p, 'w', encoding='utf-8').write(doc_head + '\n<body>\n' + blk + '\n</body>\n</html>\n')
    manifest.append((name, caption, p))
print('生成 html:', len(manifest))

# 渲染
import signal
os.system('rm -rf ' + os.path.join(OUT, 'chrome-profile'))
ONLY = [s for s in os.environ.get('BLOCKS', '').split(',') if s]
results = []
for name, caption, p in manifest:
    png = os.path.join(OUT, name + '.png')
    if ONLY and not any(o in name for o in ONLY):
        # 跳过：沿用已有图，保留尺寸信息
        if os.path.exists(png):
            results.append((name, caption, png, Image.open(png).size))
        continue
    if os.path.exists(png):
        os.remove(png)
    profile = os.path.join(OUT, 'prof_' + name)
    os.makedirs(profile, exist_ok=True)
    proc = subprocess.Popen([CHROME, '--headless=old', '--no-sandbox', '--disable-gpu',
                             '--hide-scrollbars', '--disable-dev-shm-usage', '--no-first-run',
                             '--no-default-browser-check', '--user-data-dir=' + profile,
                             '--force-device-scale-factor=2', '--window-size=520,3600',
                             '--default-background-color=FFFFFFFF',
                             '--screenshot=' + png, '--virtual-time-budget=3000',
                             'file://' + p],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        # 强杀整个进程组，避免 chrome 子进程堆积
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            proc.kill()
        print('TIMEOUT_KILLED', name)

    if not os.path.exists(png):
        print('FAIL', name)
        continue
    im = Image.open(png).convert('RGB')
    W, H = im.size
    # 找出内容底边（非白行）
    px = im.load()
    last = 0
    for y in range(H - 1, -1, -1):
        row_nonwhite = False
        for x in range(0, W, 4):
            r, g, b = px[x, y]
            if r < 250 or g < 250 or b < 250:
                row_nonwhite = True
                break
        if row_nonwhite:
            last = y
            break
    im = im.crop((0, 0, W, min(H, last + 30)))
    im.save(png)
    results.append((name, caption, png, im.size))
    print(f'{name:28} {im.size}')

json.dump([{'name': n, 'caption': c, 'png': p, 'size': list(s)} for n, c, p, s in results],
          open(os.path.join(OUT, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)

# 同步到画廊目录（映射为英文短名）
synced = 0
for name, gname in GALLERY.items():
    src = os.path.join(OUT, name + '.png')
    if os.path.exists(src):
        shutil.copy(src, os.path.join(IMAGES, gname + '.png'))
        synced += 1
print('SYNC images:', synced)
print('DONE', len(results))
