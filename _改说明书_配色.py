# -*- coding: utf-8 -*-
"""说明书补一句：配色/背景怎么改"""
import io, os

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = u"""  ⚠ 浏览器缓存：本地双击打开时改了样式看不到变化就按 Ctrl+F5；"""
NEW = u"""  ■ 配色与背景（2026-09-15 按队徽改过）
     · 主色取自队徽：主绿 #14781F、麦金 #E9C821；背景是生成的麦田图 images/bg_field.svg
     · 想换背景：打开 assets/style.css，把 url('../images/bg_field.svg') 换成
       ../images/bg_night.svg（深绿夜版，文字颜色需要配套调整）或 ../images/bg_plain.svg（极简白）
     · 想微调配色：改 assets/style.css 最上面 :root 里的变量（--green / --wheat 等）即可，改完全站生效
     · 都改完记得：本地按 Ctrl+F5 刷新看；线上要提交/同步才会变

  ⚠ 浏览器缓存：本地双击打开时改了样式看不到变化就按 Ctrl+F5；"""

for fn in ('使用说明.txt', 'guide.txt'):
    p = os.path.join(HERE, fn)
    s = io.open(p, encoding='utf-8-sig').read()
    if u'配色与背景' in s:
        print(fn, '已写过，跳过')
        continue
    assert OLD in s, fn + ' 没找到锚点'
    io.open(p, 'w', encoding='utf-8-sig', newline='').write(s.replace(OLD, NEW, 1))
    print(fn, '已更新，现 %d 行' % len(s.replace(OLD, NEW, 1).splitlines()))
