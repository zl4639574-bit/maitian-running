# -*- coding: utf-8 -*-
"""说明书写上「单独添加个人最好成绩」（两份说明书同步）"""
import io, os

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = u'【五】队伍信息 / 荣誉 / 优秀队员 / 队员名册'
NEW = u"""【五】队伍信息 / 荣誉 / 优秀队员 / 队员名册

  · 单独添加个人最好成绩（不用编一场比赛）：
    数据管理 → 队员名册 → 「＋ 单独添加个人最好成绩」，
    填 姓名 / 项目（半马、全马、10 公里、3000 米…）/ 成绩（1:23:29 或 17:02 都行），
    可加日期和赛事备注 → 点「添加这条成绩」→ 再点「同步我的修改到线上」。
    · 会出现在「个人最好成绩」榜（只统计正式队员）和该队员的名册卡片上。
    · 批量导入：一行一条「姓名,项目,成绩[,日期,备注]」，点「解析并预览」确认后入库
      （可以从 Excel 直接复制粘贴）。
    · 删除：在「已录入的个人最好成绩」列表里点那条后面的 ✕（线上已上线的也能删），删完点同步。
    · 名册卡片按 5000 米 / 3000 米 / 10000 米 / 半马 / 全马 的顺序显示，最多 4 条。"""

for fn in ('使用说明.txt', 'guide.txt'):
    p = os.path.join(HERE, fn)
    s = io.open(p, encoding='utf-8-sig').read()
    if u'单独添加个人最好成绩' in s:
        print(fn, '已经写过，跳过')
        continue
    assert OLD in s, fn + ' 没找到锚点'
    s = s.replace(OLD, NEW, 1)
    io.open(p, 'w', encoding='utf-8-sig', newline='').write(s)
    print(fn, '已更新，现 %d 行' % len(s.splitlines()))
