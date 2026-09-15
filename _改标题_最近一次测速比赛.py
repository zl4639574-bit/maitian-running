# -*- coding: utf-8 -*-
"""把总览卡片标题改成「最近一次测速 / 比赛」（app.js + 两份说明书）"""
import io, os

HERE = os.path.dirname(os.path.abspath(__file__))

EDITS = [
    ('assets/app.js', u'<h2>最近一次测速 · ${esc(latestLabel)}</h2>',
     u'<h2>最近一次测速 / 比赛 · ${esc(latestLabel)}</h2>'),
    ('assets/app.js', u'// 最近一次测速：取"所有场次"里日期最新的一场（含队长在线上新加的比赛/测速，不只是本机资料）',
     u'// 最近一次测速 / 比赛：取"所有场次"里日期最新的一场（含队长在线上新加的比赛/测速，不只是本机资料）'),
    ('使用说明.txt', u'总览的「最近一次测速」= 所有场次里日期最新的一场',
     u'总览的「最近一次测速 / 比赛」= 所有场次里日期最新的一场'),
    ('guide.txt', u'总览的「最近一次测速」= 所有场次里日期最新的一场',
     u'总览的「最近一次测速 / 比赛」= 所有场次里日期最新的一场'),
]

for fn, old, new in EDITS:
    p = os.path.join(HERE, fn)
    enc = 'utf-8-sig' if fn.endswith('.txt') else 'utf-8'
    s = io.open(p, encoding=enc).read()
    if old not in s:
        print('✗ 没找到：%s ← %s' % (fn, old[:40]))
        continue
    s = s.replace(old, new, 1)
    io.open(p, 'w', encoding=enc, newline=('' if fn.endswith('.txt') else None)).write(s)
    print('✓ %s 已改' % fn)

# 复核
for fn in ('assets/app.js', '使用说明.txt', 'guide.txt'):
    p = os.path.join(HERE, fn)
    enc = 'utf-8-sig' if fn.endswith('.txt') else 'utf-8'
    s = io.open(p, encoding=enc).read()
    print('%-16s 「最近一次测速 / 比赛」出现 %d 次；旧的「最近一次测速 ·」出现 %d 次'
          % (fn, s.count(u'最近一次测速 / 比赛'), s.count(u'最近一次测速 ·')))
