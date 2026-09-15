# -*- coding: utf-8 -*-
"""说明书更新：配色与背景改成 AI 线条画版"""
import io, os

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = u"""  ■ 配色与背景（2026-09-15 按队徽改过）
     · 主色取自队徽：主绿 #14781F、麦金 #E9C821；背景是生成的麦田图 images/bg_field.svg
     · 想换背景：打开 assets/style.css，把 url('../images/bg_field.svg') 换成
       ../images/bg_night.svg（深绿夜版，文字颜色需要配套调整）或 ../images/bg_plain.svg（极简白）
     · 想微调配色：改 assets/style.css 最上面 :root 里的变量（--green / --wheat 等）即可，改完全站生效
     · 都改完记得：本地按 Ctrl+F5 刷新看；线上要提交/同步才会变"""
NEW = u"""  ■ 配色与背景（2026-09-15：按即梦生成的队徽线条画重做）
     · 背景图 = images/bg_ai_soft.jpg（即梦生成的线条画，线条柔化 45%，原强度版是 bg_ai.jpg）
       · 想更清晰：打开 assets/style.css，把 bg_ai_soft.jpg 改成 bg_ai.jpg
       · 想换回麦田矢量图：改成 ../images/bg_field.svg，并把 background-size 改回 cover
       · 手机上是"铺满"，电脑上是"整幅居中"（宽屏不会把圆环裁掉）—— 在 style.css 的 body::before 里
     · 配色也按这张图取：主绿 #2F6B39、金 #8A7314（古金）、底色暖白 #FAFAF7
       改色只需改 assets/style.css 最上面 :root 里的变量（--green / --wheat / --bg 等），改完全站生效
     · 原图 1080x1920 右下角带「即梦AI」水印，上传前已裁掉（裁法见 处理背景图.py）
     · 都改完记得：本地按 Ctrl+F5 刷新看；线上要提交/同步才会变"""

for fn in ('使用说明.txt', 'guide.txt'):
    p = os.path.join(HERE, fn)
    s = io.open(p, encoding='utf-8-sig').read()
    if u'bg_ai_soft.jpg' in s:
        print(fn, '已写过，跳过')
        continue
    assert OLD in s, fn + ' 没找到锚点'
    io.open(p, 'w', encoding='utf-8-sig', newline='').write(s.replace(OLD, NEW, 1))
    print(fn, '已更新')
