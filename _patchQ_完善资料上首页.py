# -*- coding: utf-8 -*-
"""把「完善我的资料」放到成绩上报页的首页面（队员端 report/）
   ① 成绩上报页顶部加一张显眼的「先完善资料」卡片（带状态 + 一键跳过去）
   ② 第一次来的队员（本机没存过资料）默认就停在「完善我的资料」那一页
"""
import io, os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'app.js')
s = io.open(P, encoding='utf-8', newline='').read().replace('\r\n', '\n')
n = 0

# ① 首页卡片
old1 = """  ${rep ? `<div class="notice" style="margin-bottom:16px">
    <b>怎么把成绩交给队长（三步）</b><br>"""
new1 = """  ${rep ? (function () {
    const saved = (meDraft().name || '').trim();        // 本机存过的资料（队员自己手机上）
    return `<div class="card sec" style="border-left:5px solid var(--green);background:#f4f8f2">
      <h2 style="margin-bottom:6px">${saved ? '欢迎回来，' + esc(saved) + ' 👋' : '第一次来？先花 1 分钟完善资料 👇'}</h2>
      <div class="tiny" style="margin-bottom:12px">
        ${saved ? '你上次填的资料还在这台手机里（姓名：' + esc(saved) + '）—— 要改就点下面的按钮，不用重填。'
                : '完善资料 = 姓名 / 性别 / 学院 / 专业 / 年级 / 身份 / 个人最好成绩 / 照片。<br>填完点「复制资料文本」或「导出资料文件」发给队长，队长才能把你写进名册和成绩榜。'}
      </div>
      <div class="chips">
        <button class="btn" data-go="me">${saved ? '完善 / 修改我的资料 →' : '开始完善我的资料 →'}</button>
        <button class="btn ghost" id="btnJumpUpload">直接上报成绩 ↓</button>
      </div>
      <div class="tiny" style="margin-top:10px">两件事互不影响：资料填一次就行，成绩每次比赛都能报。</div>
    </div>`;
  })() : ''}

  ${rep ? `<div class="notice" style="margin-bottom:16px">
    <b>怎么把成绩交给队长（三步）</b><br>"""
assert old1 in s, '①'
s = s.replace(old1, new1, 1); n += 1

# ② 第一次来的队员默认停在「完善我的资料」
old2 = """  // 这个模式里没有「总览」这类默认页（比如成绩上报页只有一个 tab）→ 落到第一个可用 tab
  if (!(TABS[MODE] || []).some(t => t[0] === state.tab)) state.tab = (TABS[MODE] || [['home']])[0][0];"""
new2 = """  // 这个模式里没有「总览」这类默认页（比如成绩上报页只有一个 tab）→ 落到第一个可用 tab
  if (!(TABS[MODE] || []).some(t => t[0] === state.tab)) state.tab = (TABS[MODE] || [['home']])[0][0];
  // 队员端：第一次来（本机没存过资料）直接停在「完善我的资料」，填过的人还是停在成绩上报
  if (MODE === 'report' && !h && !(meDraft().name || '').trim()) state.tab = 'me';"""
assert old2 in s, '②'
s = s.replace(old2, new2, 1); n += 1

# ③ 「直接上报成绩 ↓」按钮：切到成绩上报并滚到录入表单
old3 = """function bindUpload() {"""
new3 = """function bindUpload() {
  const ju = $('#btnJumpUpload');
  if (ju) ju.onclick = () => {
    goTab('upload');
    setTimeout(() => { const el = document.getElementById('f_name'); if (el) { el.scrollIntoView({ block: 'center' }); el.focus(); } }, 250);
  };"""
assert old3 in s, '③'
s = s.replace(old3, new3, 1); n += 1

io.open(P, 'w', encoding='utf-8', newline='').write(s.replace('\n', '\r\n'))
print('改了 %d 处' % n)
