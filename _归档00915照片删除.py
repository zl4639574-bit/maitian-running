# -*- coding: utf-8 -*-
"""把「照片墙删图」这轮的脚本/截图归档并追加说明"""
import io, os, shutil

PROJ = os.path.dirname(os.path.abspath(__file__))
DAY = r'E:\Desktop\麦田_今日产出_2026-09-15'
for f in ['_照片删除自检.py', '_线上照片自检.py']:
    shutil.copyfile(os.path.join(PROJ, f), os.path.join(DAY, f))
for f in ['线上照片管理_新增删除.png']:
    src = os.path.join(PROJ, '手机截图', f)
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(DAY, f))

NOTE = os.path.join(DAY, '00_说明（先看这个）.txt')
add = u"""

========================================================
【补】2026-09-15 傍晚（第二件）：照片墙的「删图片」（原来只有一半，已补全）
========================================================
原来：只有「还没同步的照片」能删（本机草稿里的），照片墙上已经有的（含页面上传的和原始资料里的）
      一个删除入口都没有 —— 用户问「照片墙有没有删图片功能」。

改法（commit c487a65，已上线）：
  · 新增 overrides 字段 hiddenPhotos（和成绩/名册的 hidden 一个套路：只记"删了哪些"，同步时带上云端）；
    另有 shownPhotos 记「本机恢复显示」，这样"云端删过的那张"也能在本机恢复；
  · ov() 里把 hiddenPhotos 从照片列表里滤掉 → 照片墙、总览计数、相册张数全都跟着变；
  · 队长版「数据管理 → 照片」新增两块：
      「照片墙上的照片（N 张）」每张右上角「删」→ 从照片墙移除（可删原始资料里的、也可删已上线的）；
      「已从照片墙移除（N 张）」每张「↺ 恢复」→ 回到照片墙；
  · 删/恢复都是本机草稿，点「同步我的修改到线上」才影响线上；待同步计数认得这两处改动。

验证（脚本在本文件夹）：
  · _照片删除自检.py   把站点拷到临时目录、在临时副本的 overrides.js 里塞一条「云端已删的照片」，
      六项全过：① 云端删过的不显示但可恢复 ② 照片墙张数 71→70 对 ③ ↺ 恢复后回到 71 且本机记住 shownPhotos
      ④ 点删 → 写进 hiddenPhotos、墙上少一张 ⑤ 待同步计数 +2 ⑥ 同步载荷里 hiddenPhotos/shownPhotos/照片清单都在
  · _线上照片自检.py   线上队长版只读实测：照片墙 71 张、71 个「删」按钮、相册合计一致 ✅
  · 截图：线上照片管理_新增删除.png

没做（等用户发话）：把图片文件本身从仓库删掉（现在只"不显示"，文件还占几百 KB）。要彻底删可以加；
原始资料（E:\\Desktop\\麦田 的照片文件夹）里的照片，网页删掉只是不显示，重跑 更新数据.bat 会回来。
"""
b = io.open(NOTE, encoding='utf-8-sig').read()
io.open(NOTE, 'w', encoding='utf-8-sig', newline='').write(b.rstrip('\r\n') + add.replace('\n', '\r\n'))
print('已归档：')
for f in sorted(os.listdir(DAY)):
    print('   %-34s %8.1f KB' % (f, os.path.getsize(os.path.join(DAY, f)) / 1024.0))
