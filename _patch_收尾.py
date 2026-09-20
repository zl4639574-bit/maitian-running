# -*- coding: utf-8 -*-
"""收尾小改：导出的 Excel「公开显示」列（名册显示所有人后，只要没被移除就是「是」）+ 说明书里「添加新队员」那行身份说明"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

APP = [("""      const pub = (lv.indexOf('正式') >= 0 || lv.indexOf('预备') >= 0) && !m._hidden;""",
        """      const pub = !m._hidden;      // 名册显示所有身份（2026-09-20 起）：只要没被「移除」就是「是」""")]

DOCS = [("""＋ 添加新队员：填姓名/性别/学院/专业/年级/身份（正式·预备），一个一个加""",
         """＋ 添加新队员：填姓名/性别/学院/专业/年级/身份（正式 / 预备 / 普通），一个一个加"""),
        ("""＋ 批量添加队员：从 Excel 复制几行直接粘进去（列顺序：姓名 学院 专业 年级 性别 身份，""",
         """＋ 批量添加队员：从 Excel 复制几行直接粘进去（列顺序：姓名 学院 专业 年级 性别 身份，""")]


def patch(path, pairs, expect_all=True):
    raw = open(path, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    txt = raw.decode('utf-8-sig')
    crlf = '\r\n' in txt
    txt = txt.replace('\r\n', '\n')
    fails = []
    for i, (old, new) in enumerate(pairs):
        if old == new:
            continue
        n = txt.count(old)
        if n != 1:
            fails.append((i, n, old[:50]))
            continue
        txt = txt.replace(old, new, 1)
    if fails:
        print('❌ %s：' % os.path.basename(path))
        for i, n, s in fails:
            print('   #%d 出现 %d 次: %s' % (i, n, s))
        return False
    out = txt.replace('\n', '\r\n') if crlf else txt
    open(path, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + out.encode('utf-8'))
    print('✅ %s：%d 处' % (os.path.basename(path), len([p for p in pairs if p[0] != p[1]])))
    return True


ok = patch(os.path.join(HERE, 'assets', 'app.js'), APP)
for f in ['使用说明.md', '使用说明.txt', 'guide.txt']:
    ok &= patch(os.path.join(HERE, f), DOCS)
sys.exit(0 if ok else 1)
