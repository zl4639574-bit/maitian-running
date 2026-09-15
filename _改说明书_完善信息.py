# -*- coding: utf-8 -*-
"""说明书【五】补「完善队员信息」用法（顺手记：原来的保存名册修改不保存性别）"""
import io, os

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = u"""    · 名册卡片按 5000 米 / 3000 米 / 10000 米 / 半马 / 全马 的顺序显示，最多 4 条。"""
NEW = u"""    · 名册卡片按 5000 米 / 3000 米 / 10000 米 / 半马 / 全马 的顺序显示，最多 4 条。

  · 完善队员信息（当初没填全的，在这里补）：
    数据管理 → 队员名册 → 「＋ 完善队员信息」。
    · 上面会写「名册现在 N 人，其中 M 人信息不全（缺性别 X 人）」；
    · 点「列出信息不全的 M 人」→ 表格里直接补 性别 / 学院 / 专业 / 年级 → 点「保存这些修改」
      （也可以点「列出名册全部 N 人」挨个核对）；
    · 批量补全：一行一条「姓名,性别,学院,专业,年级」，不补的列空着就行
      （也可以带表头，会自动按列名认列；从 Excel 复制粘贴即可）→「解析并预览」→ 确认；
    · 预览里如果某人显示「不在名册里」，说明名字对不上，不会被写入；
    · 补完点「同步我的修改到线上」发布。
    · 名册列表（下方每个人那行）现在也能直接改性别了。"""

for fn in ('使用说明.txt', 'guide.txt'):
    p = os.path.join(HERE, fn)
    s = io.open(p, encoding='utf-8-sig').read()
    if u'完善队员信息' in s:
        print(fn, '已写过，跳过')
        continue
    assert OLD in s, fn + ' 没找到锚点'
    io.open(p, 'w', encoding='utf-8-sig', newline='').write(s.replace(OLD, NEW, 1))
    print(fn, '已更新，现 %d 行' % len(s.replace(OLD, NEW, 1).splitlines()))
