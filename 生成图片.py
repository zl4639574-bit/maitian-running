# -*- coding: utf-8 -*-
"""
麦田守望长跑队 · 数据中心 —— 图片压缩整理
把队里的照片压成网页能用的尺寸，输出到 images/，并生成 images/photos.js

用法：
  C:\\Users\\15749\\.venvs\\bib\\Scripts\\python.exe 生成图片.py
"""
import os, re, json, glob, shutil
from PIL import Image, ImageOps

HERE   = os.path.dirname(os.path.abspath(__file__))
ROOT   = os.path.dirname(HERE)
IMGDIR = os.path.join(HERE, "images")
MAXW, QUALITY = 1500, 78


def save(src, out_name, maxw=MAXW, quality=QUALITY):
    out = os.path.join(IMGDIR, out_name)
    try:
        im = Image.open(src)
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        w, h = im.size
        if w > maxw:
            im = im.resize((maxw, int(h * maxw / w)), Image.LANCZOS)
        im.save(out, "JPEG", quality=quality, optimize=True, progressive=True)
        return out_name
    except Exception as e:
        print("  跳过", os.path.basename(src), "->", e)
        return None


def add_group(files, cat, cap_fn, limit=None, step=None):
    if step:
        files = files[::step]
    if limit:
        files = files[:limit]
    n = 0
    for i, f in enumerate(files, 1):
        fn = save(f, "%s_%02d.jpg" % (cat, i))
        if fn:
            n += 1
            a = ALBUM.get(cat, (cat, ""))
            photos.append({"file": fn, "cat": cat, "caption": cap_fn(f),
                           "album": a[0], "albumDate": a[1]})
    print("  %-10s %2d 张" % (cat, n))
    return n


# 清掉旧的自动生成图片（保留子目录）
for f in glob.glob(os.path.join(IMGDIR, "*.jpg")):
    os.remove(f)

photos = []

# 相册：一个赛事/活动 = 一个照片集（cat -> (相册名, 日期)）
ALBUM = {
    "校运会":   ("2025 校运会", "2025.04.18"),
    "活动":     ("2025.11 12km 马拉松体验赛", "2025.11.20"),
    "测速":     ("2025.09 秋训测速", "2025.09.26"),
    "高百":     ("2024.10 高校百英里", "2024.10.06"),
    "高校联谊": ("2023.06 高校联谊", "2023.06.18"),
    "社团活动": ("队伍合影与日常训练", ""),
}

print("整理照片：")
# ① 社团活动照片（合影/活动照，文件名本身有信息）
d = os.path.join(ROOT, r"后稷跑步协会活动照片")
def cap1(f):
    n = os.path.splitext(os.path.basename(f))[0]
    n = n.replace("后稷跑步协会", "").replace("麦田守望长跑队", "").strip()
    return n or "活动合影"
add_group(sorted(glob.glob(os.path.join(d, "*.jpg"))), "社团活动", cap1)

# ② 2025 校运会（原图很多，等间隔取）
d = os.path.join(ROOT, r"25年校运会照片")
fs = sorted(glob.glob(os.path.join(d, "*.JPG")))
add_group(fs, "校运会", lambda f: "2025 校运会", limit=12,
          step=max(1, len(fs) // 12))

# ③ 2024 高百
d = os.path.join(ROOT, r"2024.10.6高百图片")
add_group(sorted(glob.glob(os.path.join(d, "*.jpg"))), "高百", lambda f: "2024.10 高校百英里")

# ④ 2025.9.26 测速
d = os.path.join(ROOT, r"后稷跑协\2025.9.26测速活动")
add_group(sorted(glob.glob(os.path.join(d, "*.jpg"))), "测速", lambda f: "2025.09 秋训测速")

# ⑤ 2025.11.20 马拉松体验赛
d = os.path.join(ROOT, r"后稷跑协\2025.11.20马拉松体验赛活动")
add_group(sorted(glob.glob(os.path.join(d, "*.jpeg"))), "活动", lambda f: "2025.11 12km 马拉松体验赛")

# ⑥ 2023.6.18 高校联谊：同一时间戳的多张只留一张
d = os.path.join(ROOT, r"23年6.18高校联谊各资料")
seen, picked = set(), []
for f in sorted(glob.glob(os.path.join(d, "微信图片_*.jpg"))):
    stem = os.path.splitext(os.path.basename(f))[0]
    key = re.sub(r"\d$", "", stem)          # 去掉末尾重复序号
    if key in seen:
        continue
    seen.add(key)
    picked.append(f)
print("  （高校联谊候选 %d 张）" % len(picked))
add_group(picked, "高校联谊", lambda f: "2023.06 高校联谊", limit=10)

# ⑦ 队徽 / 海报 / 队伍介绍长图
extra = {}
for key, rel, maxw, q in [("logo", r"资料\队伍资料信息\队徽.jpg", 420, 88),
                          ("poster", r"资料\麦田守望长跑队海报.png", 1200, 82),
                          ("intro", r"队伍介绍.png", 1400, 80)]:
    src = os.path.join(ROOT, rel)
    extra[key] = save(src, key + ".jpg", maxw=maxw, quality=q) if os.path.exists(src) else None

with open(os.path.join(IMGDIR, "photos.js"), "w", encoding="utf-8") as f:
    f.write("/* 本文件由「生成图片.py」自动生成 */\n")
    f.write("window.TEAM_PHOTOS = ")
    json.dump({"photos": photos, "logo": extra.get("logo"),
               "poster": extra.get("poster"), "intro": extra.get("intro")},
              f, ensure_ascii=False, indent=1)
    f.write(";\n")

total = sum(os.path.getsize(os.path.join(IMGDIR, p["file"])) for p in photos)
print("照片 %d 张，压缩后 %.1f MB" % (len(photos), total / 1048576))
print("队徽/海报/介绍图:", extra)
