# -*- coding: utf-8 -*-
"""说明书补一节：展示版的实时更新与「最近一次测速」的口径"""
import io, os

HERE = os.path.dirname(os.path.abspath(__file__))
SEC = ('\r\n\r\n【十二】展示版会自己变最新（实时更新）\r\n\r\n'
       '  · 展示版每 30 秒自动检查一次线上数据：队长一同步，别人已经开着的页面会在\r\n'
       '    半分钟内自己更新，并弹一句「数据已更新 · 09-15 08:12」。\r\n'
       '  · 页头显示「数据更新于 xx-xx xx:xx」，就是最近一次同步的时间。\r\n'
       '  · 总览的「最近一次测速」= 所有场次里日期最新的一场，**包括队长在线上新加的\r\n'
       '    比赛/测速**；如果那次成绩没写名次，就按成绩快慢排前 5。\r\n'
       '  · 想立刻看最新：下拉刷新即可（手机上）；页面切到后台时不会自动查，省流量。\r\n')

for fn in ('使用说明.txt', 'guide.txt'):
    p = os.path.join(HERE, fn)
    s = io.open(p, encoding='utf-8-sig').read()
    if '【十二】' in s:
        print(fn, '已有【十二】，跳过')
        continue
    s = s.rstrip('\r\n') + SEC
    io.open(p, 'w', encoding='utf-8-sig', newline='').write(s)
    print(fn, '已加【十二】，现 %d 行' % len(s.splitlines()))
