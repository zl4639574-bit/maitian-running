# -*- coding: utf-8 -*-
"""把今天这轮「名册身份改了不生效」的修复归档到 麦田_今日产出_2026-09-15\\，并追加说明"""
import io, os, shutil

PROJ = os.path.dirname(os.path.abspath(__file__))
DAY = r'E:\Desktop\麦田_今日产出_2026-09-15'
FILES = ['_名册身份自检.py', '_跑自检html.py', '_读草稿_全量.py', '_线上名册自检.py',
         '_说明书定稿.py', '_看_队员资料json.py']

os.makedirs(DAY, exist_ok=True)
for f in FILES:
    src = os.path.join(PROJ, f)
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(DAY, f))
for f in ['名册身份_修后.png', '线上名册_修后.png']:
    src = os.path.join(PROJ, '手机截图', f)
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(DAY, f))

NOTE = os.path.join(DAY, '00_说明（先看这个）.txt')
add = u"""

========================================================
【补】2026-09-15 傍晚：把原始身份「队员」的人改成「正式」，队员名册里却一直不出现（已修）
========================================================
现象（用户原话）：「我现在导入了队员的信息，为啥在队员名册里没反应呢」

取证（只读，没碰用户浏览器）：
  · 读 Edge 的 Local Storage（leveldb）里 mt_ov_local_v1 的每一次写入 —— 脚本 _读草稿_全量.py：
      17:18:38 写 #1  {"memberEdits":{"王金豪":{"photo":"images/avatars/mhmttw.jpg"}}}   ← 导入队员资料（头像已传上仓库）
      17:18:38 写 #2  {"memberEdits":{"王金豪":{"college":"林学院","major":"","grade":"2024",
                                "level":["正式"],"sex":"男"}}}                        ← 改身份那次保存（photo 字段被冲掉了）
      两次写入 = 两个标签页各自的内存草稿，后写的那条把先写的 photo 覆盖了（已知坑，已加固，见下）
  · 线上仓库 data/overrides.js 里已经有「王涛：队员 → 正式」（用户之前就试过一次），
    公开名册里同样一直没出现 → 说明不是他操作错，是代码的判定顺序错了。

真因（assets/app.js → rosterList()）：
    先按【原始名册里的身份】过滤，再套用【用户改过的身份】。
    原始身份是「队员」的人在第一道就被滤掉了，所以把身份改成「正式」永远不生效。
    → 改成：先套用改过的身份（含「改成空 = 不进公开名册」），再按正式/预备过滤。

改动（commit 875dc1d + d7e841f，已推送上线）：
  1. rosterList()：身份判定顺序修好 —— 队员改正式，保存后立刻进名册；
     身份留空 = 不进公开名册（与「队员数据表」说明书里写的一致）。
  2. 导入资料 / 导入收集表 / 收件箱接收：不再糊弄，明确区分三种情况
     （已在名册里 / 原始名册里有但身份是「队员」→ 要改身份 / 名册里完全没有 → 真加入名册），
     并在队员资料预览里加了一键「把他加入公开名册（身份=正式）」按钮。
     收集表导入时「名册里完全没有的人」现在会真的写进名册（以前只更新 memberEdits，提示却说"新增 N 人"）。
  3. mergeMemberEdits()：名册修改按【人+字段】合并（本机覆盖云端同名字段，云端独有的字段如头像保留），
     同步时也用它 —— 以后「另一个标签页改了身份」不会再冲掉已经上传的头像。
  4. 数据：把王金豪的 photo 字段补回线上 overrides.js（头像文件 images/avatars/mhmttw.jpg 本来就在仓库里，
     只是没被引用），配合第 3 条不会再被覆盖。
  5. 使用说明.txt / guide.txt / 使用说明.md：写清「公开名册只显示正式/预备」「改了没反应先查两件事」
     「别同时开两个标签页改数据」。

验证（脚本都在本文件夹）：
  · _名册身份自检.py    本地起站 + 临时 Edge + 写入和用户一模一样的本机草稿：
        旧代码 57 人、王金豪/王涛 ❌ 都没有；新代码 59 人、两人都在、王金豪头像来自云端合并 ✅
  · _跑自检html.py      跑 _自检.html 全部断言：异常项 0（名册删除/恢复、九个管理分区、成绩榜等都没坏）
  · _线上名册自检.py    只读查线上队长版：正式队员 59 人 · 预备 1 人，王金豪（含头像）+ 王涛 都在 ✅
  · 截图：名册身份_修后.png（本地）、线上名册_修后.png（线上）

顺带发现（数据小问题，没动）：王涛那行的年级写成了「2824 级」，应该是 2024，改的话在「队员数据表」里改。
"""
b = io.open(NOTE, encoding='utf-8-sig').read()
io.open(NOTE, 'w', encoding='utf-8-sig', newline='').write(b.rstrip('\r\n') + add.replace('\n', '\r\n'))
print('已归档：')
for f in sorted(os.listdir(DAY)):
    print('   %-34s %8.1f KB' % (f, os.path.getsize(os.path.join(DAY, f)) / 1024.0))
