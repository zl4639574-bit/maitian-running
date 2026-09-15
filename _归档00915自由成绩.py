# -*- coding: utf-8 -*-
"""归档「自由成绩删不掉」这轮"""
import io, os, shutil

PROJ = os.path.dirname(os.path.abspath(__file__))
DAY = r'E:\Desktop\麦田_今日产出_2026-09-15'
for f in ['_patchP_自由成绩删除.py', '_自由成绩删除自检.py', '_线上自由成绩自检.py']:
    src = os.path.join(PROJ, f)
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(DAY, f))
for f in ['线上自由成绩_已删除可恢复.png']:
    src = os.path.join(PROJ, '手机截图', f)
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(DAY, f))

NOTE = os.path.join(DAY, '00_说明（先看这个）.txt')
add = u"""

========================================================
【补】2026-09-15 深夜（第五件）：用户说"自由成绩那里我要删除点删没反应"（已修）
========================================================
用户原话：「自由成绩那里我要删除点删没反应啊」

取证（只读）：云端 overrides.js 里「李志宏 半马」有 3 条：
  · rmu114vax 1:23:29（对，meet 2025杨凌农科城马拉松赛）
  · rmu16v607 raw「1：23.29」 sec=83.3 fmt=1:23 ← 被旧解析 bug 吞过的错值
  · rmu22vglv 1：23：29 → 1:23:29（对）
用户显然是在反复重录、想删掉重复和错的那条，但点了没反应。

三个真 bug（commit 15755fb 已上线）：
  ① 每行「删」按钮是按下标去删**本机** results 数组，可是列表是「云端成绩 + 本机成绩」拼的，
     云端那条排在前面 → 点云端行的"删"等于什么都没删/删错本机那条（而且没有任何提示）。
     修：改成按成绩身份（uid 或 姓名|秒）删 —— 本机那条直接删，云端那条记进 hiddenResults 屏蔽。
  ② ov().results 的过滤只读**云端** hiddenResults，本机记下的"删除"根本不参与显示 → 点了没反应。
     修：云端 ∪ 本机 hiddenResults，再减掉本机 shownResults。
  ③ pendingCount() 没算 hiddenResults / shownResults（也没算名册的 shown）→ 删完不算"待同步改动"，
     「同步我的修改到线上」还是灰的、提示"没有需要同步的修改"，删了也发不出去。修：补上这 3 项。
  另外补了「已删除的成绩（N 条，可恢复）」列表（和照片墙一套），删错的点 ↺ 恢复再同步就回来。

数据：把「李志宏 半马」那条重复的（rmu114vax）+ 被吞成 1:23 的（rmu16v607）放进 hiddenResults（可恢复），
只留最新那条正确的 1:23:29 在列表里。

顺带发现（用户自己的操作，没动）：他这轮又导入了 易嘉庚 / 姚语熙 的资料（9 条最好成绩），
并且自己把 王金豪 那两条被吞的 半马 1:24 / 全马 4:20 删掉了 ✅（正是我上一轮建议的做法）。
王金豪的 5 个最好成绩现在各有两条重复（资料导过两次）—— 榜上不会重复算，看着别扭可以在
「已录入的个人最好成绩」里把重复的点 ✕。另外推送时和用户的最新同步撞了 overrides.js 冲突，
已按"用他最新那份 + 补回我的屏蔽记录"解掉。

验证（脚本在本文件夹）：
  · _自由成绩删除自检.py 六项全过：列表/已删除都列得出；点删真的消失并进已删除；点 ↺ 真的回来；
    恢复"云端记过删的"会写 shownResults；同步载荷里 results 不含删掉的、hiddenResults 含它；
    本机自己发布的那条点删直接从本机删掉
  · _线上自由成绩自检.py 线上复核：列表 1 条（李志宏半马 1:23:29）、已删除 2 条带 ↺ 恢复 ✅
  · 通用自检 队长版/队员版 异常 0；名册同步自检 5 项全过；身份自检 4 项全过
"""
b = io.open(NOTE, encoding='utf-8-sig').read()
io.open(NOTE, 'w', encoding='utf-8-sig', newline='').write(b.rstrip('\r\n') + add.replace('\n', '\r\n'))
print('已归档（合计 %.1f MB）' % (sum(os.path.getsize(os.path.join(DAY, f)) for f in os.listdir(DAY)) / 1048576.0))
