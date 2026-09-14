# -*- coding: utf-8 -*-
"""A. 个人最好成绩只统计「正式」队员（每场比赛的榜仍显示所有人）"""
import io

p = "assets/app.js"
s = io.open(p, encoding="utf-8", newline="").read().replace("\r\n", "\n")
orig = len(s)

old = r"""function personalBests() {
  const map = {};
  allResults().forEach(r => {
    if (!r.name || !r.sec) return;
    const k = r.name + '|' + (r.event || '');"""
new = r"""function personalBests() {
  const map = {};
  // 个人最好成绩只统计「正式队员」；非正式的同学只在当时的比赛榜里出现
  const official = new Set(rosterList().filter(m => (m.level || []).indexOf('正式') >= 0).map(m => m.name));
  allResults().forEach(r => {
    if (!r.name || !r.sec) return;
    if (!official.has(r.name)) return;
    const k = r.name + '|' + (r.event || '');"""
assert s.count(old) == 1, "A1 personalBests"
s = s.replace(old, new)

old = r"""  <p class="sub sec">上面按「一场比赛一张榜」看原始名次；下面这一张是把所有比赛合起来，每个人每个项目只留最快的一次。</p>"""
new = r"""  <p class="sub sec">上面按「一场比赛一张榜」看原始名次（含当时参赛的所有同学）；下面这一张是个人最好成绩，把所有比赛合起来、每人每项只留最快的一次，且<b>只统计正式队员</b>。</p>"""
assert s.count(old) == 1, "A2 榜单说明"
s = s.replace(old, new)

io.open(p, "w", encoding="utf-8", newline="\r\n").write(s)
print("A 完成: %d -> %d 字符" % (orig, len(s)))
