# -*- coding: utf-8 -*-
"""补三处：①「1:23.29」当 时:分.秒 ②成绩栏"识别为"提示 ③bindUpload 里挂上监听"""
import io, os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'app.js')
s = io.open(P, encoding='utf-8', newline='').read()
crlf = '\r\n' in s
s = s.replace('\r\n', '\n')

subs = []

old_a = """    if (p.length === 2) return pickSec([p[0] * 60 + p[1], p[0] * 3600 + p[1] * 60], ev);   // 分:秒（长距离就是 时:分）"""
new_a = """    if (p.length === 2) {
      // 分:秒；长距离时按 时:分。另外「1:23.29」这种拿点号当第二道冒号的写法（时:分.秒）也认
      const dotSec = (p[1] % 1 !== 0 && String(p[1]).split('.')[1].length <= 2)
        ? p[0] * 3600 + Math.floor(p[1]) * 60 + Math.round((p[1] % 1) * 100) : null;
      return pickSec([p[0] * 60 + p[1], dotSec, p[0] * 3600 + p[1] * 60], ev);
    }"""
subs.append(('两段式「1:23.29」', old_a, new_a))

old_b = """      <div class="field"><label>成绩 * （净计时；分:秒 或 时:分:秒）</label><input id="f_result" placeholder="18:35 / 1:23:22"></div>"""
new_b = """      <div class="field"><label>成绩 * （净计时；分:秒 或 时:分:秒）</label><input id="f_result" placeholder="18:35 / 1:23:22">
        <div class="tiny" id="f_resultHint" style="margin-top:4px"></div></div>"""
subs.append(('成绩栏提示容器', old_b, new_b))

old_c = """  const add = $('#btnAdd');
  if (add) add.onclick = () => {
    const name = ($('#f_name').value || '').trim();
    const ev = ($('#f_event').value || '').trim();
    const raw = ($('#f_result').value || '').trim();"""
new_c = """  // 成绩栏：边打边告诉你"识别成多少"，以及这个成绩对该项目是不是不太像（写 1:24:00 = 1 小时 24 分）
  const fres = $('#f_result'), fhint = $('#f_resultHint');
  const updResHint = () => {
    if (!fres || !fhint) return;
    const raw = String(fres.value || '').trim();
    const ev2 = ($('#f_event').value || '').trim();
    if (!raw) { fhint.textContent = ''; return; }
    const sec = parseSec(raw, ev2);
    if (!sec) { fhint.textContent = '⚠️ 认不出这个写法，试试 18:35 或 1:24:00'; return; }
    fhint.textContent = secSuspicion(sec, ev2) || ('识别为 ' + fmtSec(sec) + (ev2 ? '（' + ev2 + '）' : ''));
  };
  if (fres) fres.oninput = updResHint;
  const fev = $('#f_event');
  if (fev) fev.oninput = updResHint;
  const add = $('#btnAdd');
  if (add) add.onclick = () => {
    const name = ($('#f_name').value || '').trim();
    const ev = ($('#f_event').value || '').trim();
    const raw = ($('#f_result').value || '').trim();"""
subs.append(('bindUpload 监听', old_c, new_c))

for label, old, new in subs:
    if old not in s:
        print('!! 没找到：' + label); continue
    s = s.replace(old, new, 1)
    print('  已改：' + label)

if crlf:
    s = s.replace('\n', '\r\n')
io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('写回完成（CRLF=%s）' % crlf)
