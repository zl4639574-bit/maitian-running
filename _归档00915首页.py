# -*- coding: utf-8 -*-
"""归档「完善资料上成绩上报首页」这轮"""
import io, os, shutil

PROJ = os.path.dirname(os.path.abspath(__file__))
DAY = r'E:\Desktop\麦田_今日产出_2026-09-15'
for f in ['_patchQ_完善资料上首页.py', '_完善资料上首页自检.py', '_线上队员端首页自检.py']:
    src = os.path.join(PROJ, f)
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(DAY, f))
for f in ['线上队员端_第一次来_完善资料首页.png', '线上队员端_填过资料_成绩上报首页.png']:
    src = os.path.join(PROJ, '手机截图', f)
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(DAY, f))

NOTE = os.path.join(DAY, '00_说明（先看这个）.txt')
add = u"""

========================================================
【补】2026-09-15 深夜（第六件）：完善资料上成绩上报首页（commit 4bbcfd6 已上线）
========================================================
用户原话：「把完善资料放在成绩上报的首页面吧，这样更方便」

做法（队员端 report/）：
  ① 成绩上报页顶部新增一张卡片：
     · 本机存过资料 → 标题「欢迎回来，XXX 👋」+ 说明「你上次填的资料还在这台手机里（姓名：XXX）
       —— 要改就点下面的按钮，不用重填」；
     · 第一次来 → 标题「第一次来？先花 1 分钟完善资料 👇」+ 说明资料包含哪些项、填完怎么交给队长。
     两个按钮：「完善 / 修改我的资料 →」（跳完善资料页）、「直接上报成绩 ↓」（跳回录入表单，
     光标自动落在姓名框）。卡片下面还有一句"两件事互不影响"。
  ② 队员端默认落地页跟着身份走：**第一次来（本机没存过资料）默认停在「完善我的资料」**，
     填过的队员默认停在「成绩上报」——这样新队员打开链接看到的就是填资料，老队员直接填成绩。
  ③ 两个页签都还在，随时互跳；完善资料页原来的「去上报成绩 →」保留。

验证：
  · _完善资料上首页自检.py 五项全过：① 第一次来默认完善我的资料 ③ 填过资料的停在成绩上报且卡片
    显示「欢迎回来 + 姓名」② 卡片按钮跳得过去 ④ 「直接上报成绩 ↓」跳回来并聚焦姓名框
    ⑤ 完善资料页的「去上报成绩 →」仍然好用
  · _线上队员端首页自检.py 线上复核 + 两张截图（线上队员端_第一次来_完善资料首页.png /
    线上队员端_填过资料_成绩上报首页.png）✅
  · _跑自检html.py report 异常 0；说明书【十七】已加这一节
"""
b = io.open(NOTE, encoding='utf-8-sig').read()
io.open(NOTE, 'w', encoding='utf-8-sig', newline='').write(b.rstrip('\r\n') + add.replace('\n', '\r\n'))
print('已归档（合计 %.1f MB）' % (sum(os.path.getsize(os.path.join(DAY, f)) for f in os.listdir(DAY)) / 1048576.0))
