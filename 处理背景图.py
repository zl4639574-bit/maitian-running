# -*- coding: utf-8 -*-
"""处理即梦生成的背景图：
   ① 精确定位右下角「即梦AI」水印并裁掉（在图形成品范围内取裁切线）
   ② 缩到宽 1080、出「原强度」+「柔化 45%」两版
   ③ 按"最饱和"取图里真正的绿与金，并推导出：深墨绿/中绿/淡绿/深金/亮金 + 各自白底对比度
"""
import colorsys, io, os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else r'E:\Edge Downloads\jimeng-2026-09-15-9093-极简线条插画的网页背景，纯白底，       用极细的线条勾勒：一圈圆形跑道的弧....png'
im = Image.open(SRC).convert('RGB')
W, H = im.size
print('原图 %dx%d  %.2f MB' % (W, H, os.path.getsize(SRC) / 1048576.0))
px = im.load()


def is_ink(x, y):
    r, g, b = px[x, y]
    return not (r > 238 and g > 238 and b > 238)


# ① 图形主体最下沿（只看左 70% 宽，避开右下角水印）
art_bottom = 0
for y in range(H - 1, 0, -2):
    if any(is_ink(x, y) for x in range(0, int(W * 0.70), 3)):
        art_bottom = y
        break
# 水印上沿（右下角 20% 宽 × 底部 15% 高）
wm_top = None
for y in range(int(H * 0.85), H, 1):
    if any(is_ink(x, y) for x in range(int(W * 0.80), W, 2)):
        wm_top = y
        break
print('图形最下沿 y=%d（%.1f%%）｜右下角水印上沿 y=%s' % (art_bottom, 100.0 * art_bottom / H, wm_top))

cut = art_bottom + 36                      # 图形下方留一点呼吸空间
if wm_top is not None:
    cut = min(cut, wm_top - 6)             # 但一定切在水印之上
cut = max(cut, int(H * 0.5))
im1 = im.crop((0, 0, W, cut))
print('裁切线 y=%d → 裁掉底部 %d 像素（含水印），新尺寸 %dx%d' % (cut, H - cut, im1.size[0], im1.size[1]))

if im1.size[0] > 1080:
    im1 = im1.resize((1080, int(im1.size[1] * 1080.0 / im1.size[0])), Image.LANCZOS)
p_full = os.path.join(HERE, 'images', 'bg_ai.jpg')
im1.save(p_full, 'JPEG', quality=88, optimize=True, progressive=True)
print('原强度 → images/bg_ai.jpg  %dx%d  %.0f KB' % (im1.size[0], im1.size[1], os.path.getsize(p_full) / 1024.0))

white = Image.new('RGB', im1.size, (255, 255, 255))
Image.blend(im1, white, 0.45).save(os.path.join(HERE, 'images', 'bg_ai_soft.jpg'),
                                   'JPEG', quality=88, optimize=True, progressive=True)
print('柔化版 → images/bg_ai_soft.jpg  %.0f KB' % (os.path.getsize(os.path.join(HERE, 'images', 'bg_ai_soft.jpg')) / 1024.0))

# ③ 取线条的"核心色"：按色相聚成绿/金两组，各取最暗 35% 像素的平均（避开抗锯齿边缘）
greens, golds = [], []
for y in range(0, im1.size[1], 2):
    for x in range(0, im1.size[0], 2):
        r, g, b = im1.getpixel((x, y))
        hh, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        deg = hh * 360
        if s < 0.30 or v < 0.12:
            continue
        if 80 <= deg <= 165:
            greens.append(((r, g, b), v))
        elif 33 <= deg <= 78:
            golds.append(((r, g, b), v))


def core(lst, frac=0.35):
    if not lst:
        return None
    lst.sort(key=lambda t: t[1])
    k = max(1, int(len(lst) * frac))
    sel = [c for c, _ in lst[:k]]
    return tuple(int(round(sum(c[i] for c in sel) / float(len(sel)))) for i in range(3))


best_g = (core(greens), 0)
best_y = (core(golds), 0)


def hx(c):
    return '#%02X%02X%02X' % c


def lum(c):
    def f(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def contrast(c, bg=(255, 255, 255)):
    l1, l2 = lum(c), lum(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def shade(c, sat=None, val=None):
    hh, s, v = colorsys.rgb_to_hsv(*[x / 255.0 for x in c])
    if sat is not None:
        s = sat / 100.0
    if val is not None:
        v = val / 100.0
    r, g, b = colorsys.hsv_to_rgb(hh, s, v)
    return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))


print('\n图里最饱和的绿 = %s（H=%.0f° S=%.0f%% V=%.0f%%）｜最饱和的金 = %s（H=%.0f° S=%.0f%% V=%.0f%%）'
      % (hx(best_g[0]), colorsys.rgb_to_hsv(*[x / 255.0 for x in best_g[0]])[0] * 360,
         best_g[1] * 100, colorsys.rgb_to_hsv(*[x / 255.0 for x in best_g[0]])[2] * 100,
         hx(best_y[0]), colorsys.rgb_to_hsv(*[x / 255.0 for x in best_y[0]])[0] * 360,
         best_y[1] * 100, colorsys.rgb_to_hsv(*[x / 255.0 for x in best_y[0]])[2] * 100))

print('\n从图色推导出的主题色（含白底对比度，≥4.5 才算达标）：')
for name, cand in (
        ('深墨绿（正文/按钮/数字）', shade(best_g[0], sat=46, val=33)),
        ('主绿（次级标题/描边）', shade(best_g[0], sat=42, val=46)),
        ('中绿（图里线色）', best_g[0]),
        ('淡绿（浅底/徽章）', shade(best_g[0], sat=24, val=88)),
        ('深金（金色文字）', shade(best_y[0], sat=62, val=42)),
        ('亮金（奖牌/强调底）', shade(best_y[0], sat=55, val=86)),
):
    print('   %-22s %s  对比度 %.2f %s' % (name, hx(cand), contrast(cand), '✅' if contrast(cand) >= 4.5 else '（偏低，仅用于装饰/大字）'))
