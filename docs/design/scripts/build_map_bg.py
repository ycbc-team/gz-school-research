#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 UI 稿「真实广州地图底图」：下载 OSM 瓦片拼接为 750x1624(@2x, 对应 375x812 画框)。

用法：
    python docs/design/scripts/build_map_bg.py

产出：
    - docs/design/assets/map_yuexiu_z16.jpg   底图（再由 inject_map_bg.py 以 base64 内联进 spec html）
    - 终端打印各学校点位的 CSS 偏移（相对 375x812 画框左上角，单位 css px）

地图中心锚点 = 广州市育才中学（东校区），OSM 学校面要素中心 23.13207, 113.30058。
瓦片来源 OpenStreetMap 标准瓦片（© OpenStreetMap contributors），仅用于设计稿示意。
"""
import math, os, io, json, urllib.request
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_JPG = os.path.join(os.path.dirname(HERE), 'assets', 'map_yuexiu_z16.jpg')

Z = 16
N = 2 ** Z
CROP_W, CROP_H = 750, 1624          # 设备像素(@2x)，对应画框 375x812 css
ANCHOR_CSS = (187.5, 340)           # 锚点在画框内的位置（css px），略高于中线给底部详情卡留位

LAT0, LON0 = 23.13207, 113.30058    # 育才中学（东校区）

UA = {'User-Agent': 'gz-school-research-ui-mockup/1.0 (local design asset)'}


def world_px(lat, lon):
    """zoom Z 下经纬度 -> 全球瓦片像素坐标。"""
    fx = (lon + 180.0) / 360.0 * N * 256
    la = math.radians(lat)
    fy = (1.0 - math.log(math.tan(la) + 1 / math.cos(la)) / math.pi) / 2.0 * N * 256
    return fx, fy


def css_offset(lat, lon):
    """学校经纬度 -> 相对锚点的画框 css 偏移 (dx, dy)，dy 向下为正。"""
    fx, fy = world_px(lat, lon)
    ax, ay = world_px(LAT0, LON0)
    return round((fx - ax) / 2, 1), round((fy - ay) / 2, 1)


# ---- 点位清单（OSM 学校面要素中心 / 官方地址核对的坐标） ----
SCHOOLS = [
    # (名称, 学段 s/m/h, 纬度, 经度)
    ('广州市育才中学（东校区）',   'h', 23.13207, 113.30058),
    ('广州市育才中学（西校区）',   'h', 23.12913, 113.29795),
    ('广州市铁一中学（越秀校区）', 'h', 23.12666, 113.30535),
    ('广州市培正中学',            'h', 23.12225, 113.29375),
    ('东风东路小学（本部）',       's', 23.13361, 113.29670),
    ('越秀区育才学校',            's', 23.13340, 113.29964),
    ('东风东路小学（锦城校区）',   's', 23.13270, 113.30618),
    ('广州市铁一小学',            's', 23.12719, 113.30002),
    ('广州市东风实验学校（初中）', 'm', 23.13539, 113.30189),
]

# ---- 计算需要的瓦片范围 ----
ax, ay = world_px(LAT0, LON0)
tl_x, tl_y = ax - ANCHOR_CSS[0] * 2, ay - ANCHOR_CSS[1] * 2
tx0, ty0 = int(tl_x // 256), int(tl_y // 256)
tx1, ty1 = int((tl_x + CROP_W) // 256), int((tl_y + CROP_H) // 256)
print(f'锚点世界像素: ({ax:.1f}, {ay:.1f})  瓦片范围 x{tx0}-{tx1} y{ty0}-{ty1}')

# ---- 下载并拼接 ----
canvas = Image.new('RGB', ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256), '#eeeeee')
missed = 0
for tx in range(tx0, tx1 + 1):
    for ty in range(ty0, ty1 + 1):
        url = f'https://tile.openstreetmap.org/{Z}/{tx}/{ty}.png'
        try:
            req = urllib.request.Request(url, headers=UA)
            data = urllib.request.urlopen(req, timeout=20).read()
            tile = Image.open(io.BytesIO(data)).convert('RGB')
        except Exception as e:
            missed += 1
            print('MISS', url, e)
            continue
        canvas.paste(tile, ((tx - tx0) * 256, (ty - ty0) * 256))
print('missed tiles:', missed)

left, top = tl_x - tx0 * 256, tl_y - ty0 * 256
crop = canvas.crop((round(left), round(top), round(left) + CROP_W, round(top) + CROP_H))
os.makedirs(os.path.dirname(OUT_JPG), exist_ok=True)
crop.save(OUT_JPG, 'JPEG', quality=82, optimize=True)
print('saved:', OUT_JPG, crop.size, f'{os.path.getsize(OUT_JPG) / 1024:.0f} KB')

# ---- 打印点位 css 偏移（供 spec html 使用） ----
print('\n--- 点位 CSS 偏移 (dx, dy)，相对画框左上角 ---')
dots = []
for name, st, la, lo in SCHOOLS:
    dx, dy = css_offset(la, lo)
    # 换算成画框内绝对位置（锚点在 ANCHOR_CSS）
    px, py = round(ANCHOR_CSS[0] + dx, 1), round(ANCHOR_CSS[1] + dy, 1)
    dots.append({'name': name, 'stage': st, 'dx': dx, 'dy': dy, 'px': px, 'py': py})
    print(f'{name:22} {st}  css=({px},{py})  offset=({dx},{dy})')
json.dump(dots, open(os.path.join(os.path.dirname(HERE), 'assets', 'map_dots.json'), 'w'),
          ensure_ascii=False, indent=1)
