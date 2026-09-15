# -*- coding: utf-8 -*-
"""造一张测试用 HEIC 照片：左半红、右半蓝、左上角一小块绿方块（方便验像素）。"""
import os, sys
from PIL import Image, ImageDraw

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception as e:
    print('没有 pillow_heif：', e); sys.exit(1)

W, H = 1200, 900
im = Image.new('RGB', (W, H), (255, 0, 0))
d = ImageDraw.Draw(im)
d.rectangle([W // 2, 0, W, H], fill=(0, 0, 255))
d.rectangle([0, 0, 160, 160], fill=(0, 255, 0))

p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_测_HEIC_左红右蓝.heic')
im.save(p, format='HEIF', quality=85)
print('OK', p, os.path.getsize(p), 'bytes')
