# -*- coding: utf-8 -*-
"""① 删掉自检上传的测试图（只删这一张）② 让 HEIC 走「打不开」分支给出正确处理提示"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
TESTFILE = "up_1789389061921_0.jpg"

# ── ① 从 overrides.js 清单里摘掉自检照片 ──
ovp = os.path.join(HERE, "data", "overrides.js")
t = io.open(ovp, encoding="utf-8", newline="").read()
head, body = t.split("=", 1)
obj = json.loads(body.strip().rstrip(";"))
before = obj.get("photos") or []
obj["photos"] = [p for p in before if p.get("file") != TESTFILE]
io.open(ovp, "w", encoding="utf-8", newline="\n").write(
    head + "= " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n")
print("清单: 照片 %d -> %d 条（摘掉自检图 %s）" % (len(before), len(obj["photos"]), TESTFILE))

# ── ② 删掉仓库里的自检图片文件 ──
f = os.path.join(HERE, "images", TESTFILE)
if os.path.exists(f):
    os.remove(f)
    print("已删除图片文件 images/%s" % TESTFILE)
else:
    print("图片文件不在本地（git 会处理）")

# ── ③ HEIC 走「打不开」分支（给出"怎么转 JPG"的提示，而不是"不是图片"）──
ap = os.path.join(HERE, "assets", "app.js")
s = io.open(ap, encoding="utf-8", newline="").read().replace("\r\n", "\n")
old = r"if (!/^image\//.test(f.type) && !/\.(jpe?g|png|webp|gif|bmp)$/i.test(f.name))"
new = r"if (!/^image\//.test(f.type) && !/\.(jpe?g|png|webp|gif|bmp|heic|heif)$/i.test(f.name))"
assert s.count(old) == 1, "锚点未命中"
io.open(ap, "w", encoding="utf-8", newline="\r\n").write(s.replace(old, new))
print("已让 HEIC/HEIF 走图片解码分支（失败时提示怎么转 JPG）")
