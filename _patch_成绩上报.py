# -*- coding: utf-8 -*-
"""新增「成绩上报」收集入口：
   ① 新页面 report/index.html（MODE='report'）：队员填成绩 → 复制文本 / 导出 CSV → 发队长
   ② 队长版「上传成绩」新增「② 粘贴文本导入」：把队员发来的文本直接贴进来 → 预览 → 入库
"""
import io, os

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'assets', 'app.js')
s = io.open(P, 'rb').read().decode('utf-8').replace('\r\n', '\n')
done = []


def rep(old, new, label, cnt=1):
    global s
    n = s.count(old)
    assert n == cnt, '✗ %s：期望 %d 处，实际 %d 处' % (label, cnt, n)
    s = s.replace(old, new)
    done.append(label)


# ── ① 第三个入口：report ──
rep("""  captain: [['home', '总览'], ['board', '成绩榜'], ['roster', '队员名册'], ['upload', '上传成绩'],
            ['manage', '数据管理'], ['photos', '照片墙'], ['about', '荣誉与资料']],""",
    """  captain: [['home', '总览'], ['board', '成绩榜'], ['roster', '队员名册'], ['upload', '上传成绩'],
            ['manage', '数据管理'], ['photos', '照片墙'], ['about', '荣誉与资料']],
  report:  [['upload', '成绩上报']],          // 队员成绩收集页：只填 + 导出，不需要令牌""",
    '①a TABS 加 report')

rep("""function renderUpload() {
  const L = myResults().sort((a, b) => (b.date || '').localeCompare(a.date || ''));
  const rosterNames = new Set(rosterList().map(m => m.name));""",
    """function renderUpload() {
  const L = myResults().sort((a, b) => (b.date || '').localeCompare(a.date || ''));
  const rosterNames = new Set(rosterList().map(m => m.name));
  const rep = MODE === 'report';        // 成绩上报页（队员填 → 导出给队长导入）""",
    '①b renderUpload 识别 report 模式')

rep("""  <div class="sec-head"><h1>上传成绩</h1>
    <button class="btn ghost sm" data-go="board">看成绩榜 →</button></div>""",
    """  <div class="sec-head"><h1>${rep ? '成绩上报' : '上传成绩'}</h1>
    ${MODE === 'captain' ? '<button class="btn ghost sm" data-go="board">看成绩榜 →</button>' : ''}</div>

  ${rep ? `<div class="notice" style="margin-bottom:16px">
    <b>怎么把成绩交给队长（三步）</b><br>
    ① 下面把这次比赛/测速的成绩一条条填进来（填错可以删了重填）；<br>
    ② 拉到底点「复制成上报文本」，或者点「导出 CSV」存成一个小文件；<br>
    ③ 把这段文字（或那个文件）发到队群，或者直接发给队长。<br>
    <span class="tiny">不用登录、不用密码，填的内容只存在你自己手机里，不会自动上传任何东西。</span>
  </div>` : ''}""",
    '①c 上报页的头部与说明')

rep("""    <div class="sec-head"><h2>${batch ? '③' : '②'} 我录入的成绩</h2>
      <div class="chips">
        <button class="btn ghost sm" id="btnCopy" ${L.length ? '' : 'disabled'}>复制成文本</button>
        <button class="btn ghost sm" id="btnCsv" ${L.length ? '' : 'disabled'}>导出 CSV</button>""",
    """    <div class="sec-head"><h2>${rep ? '我填的成绩（' + L.length + ' 条）' : (batch ? '③' : '②') + ' 我录入的成绩'}</h2>
      <div class="chips">
        <button class="btn ${rep ? '' : 'ghost'} sm" id="btnCopy" ${L.length ? '' : 'disabled'}>${rep ? '复制成上报文本（发队长）' : '复制成文本'}</button>
        <button class="btn ghost sm" id="btnCsv" ${L.length ? '' : 'disabled'}>导出 CSV</button>""",
    '①d 上报页的导出按钮文案')

rep("""    const txt = '麦田守望 · 成绩上报（' + todayStr() + '）\\n'
      + myResults().map(r => [r.name, r.event, r.fmt || fmtSec(r.sec), r.date, r.meet || ''].join('\\t')).join('\\n');
    copyText(txt);""",
    """    const txt = '麦田守望 · 成绩上报（' + todayStr() + '）\\n'
      + '姓名\\t项目\\t成绩\\t日期\\t赛事/名次\\n'
      + myResults().map(r => [r.name, r.event, r.fmt || fmtSec(r.sec), r.date, r.meet || r.rank || ''].join('\\t')).join('\\n');
    copyText(txt);
    toast('已复制，直接粘到队群里发给队长即可', 6000);""",
    '①e 上报文本加表头（队长那边能自动认列）')

# ── ② 队长版：粘贴文本导入 ──
rep("""  <div class="card sec">
    <div class="sec-head"><h2>${rep ? '我填的成绩（' + L.length + ' 条）' : (batch ? '③' : '②') + ' 我录入的成绩'}</h2>""",
    """  ${batch ? `
  <div class="card sec">
    <h2>② 粘贴文本导入（队员上报贴这里）</h2>
    <div class="tiny" style="margin-bottom:8px">队员在「成绩上报」页复制给你的那几行，直接粘到下面就行：
      一行一条，<b>姓名,项目,成绩[,日期,赛事/名次]</b>（逗号、制表符都能认；带表头会自动按列名认列）。<br>
      名字不在名册里的（外校选手、跑团朋友）也能进来，只会出现在这场比赛的榜上。</div>
    <textarea class="ta" id="pasteBox" rows="5" placeholder="张三,5000米,18:35,2026.09.15,校运会&#10;李四,10公里,42:10"></textarea>
    <div class="chips" style="margin-top:10px"><button class="btn ghost" id="btnPasteGo">解析并预览</button>
      <span class="tiny">解析完点「加进来」，再去「数据管理 → 比赛成绩」并进某场比赛</span></div>
    <div id="pasteArea"></div>
  </div>` : ''}

  <div class="card sec">
    <div class="sec-head"><h2>${batch ? '③' : '②'} 我录入的成绩</h2>""",
    '②a 上传页加「粘贴文本导入」区块')

rep("""/* --------------------------------------------- 数据管理交互（队长版） */""",
    """/* ---------------- 粘贴文本导入（队员上报的文字直接用）---------------- */

let pasteRows = null;

/** 一行一条：姓名,项目,成绩[,日期,赛事/名次]（默认按位置认列，有表头就按表头认） */
function pasteParseText(txt) {
  const rows = [], skip = [];
  const dir = { name: 0, event: 1, res: 2, date: 3, note: 4 };
  String(txt || '').split(/\\r?\\n/).forEach((line, i) => {
    const t = line.trim();
    if (!t) return;
    const p = t.split(/[\\t,，、]+/).map(x => x.trim());
    if (i === 0 && /姓名|名字/.test(p[0] || '')) {
      p.forEach((h, idx) => {
        if (/姓名|名字/.test(h)) dir.name = idx;
        else if (/项目|距离/i.test(h)) dir.event = idx;
        else if (/成绩|用时|结果|计时/.test(h)) dir.res = idx;
        else if (/日期/.test(h)) dir.date = idx;
        else if (/赛事|比赛|名次|备注|地点/.test(h)) dir.note = idx;
      });
      return;
    }
    const g = k => (dir[k] === undefined ? '' : (p[dir[k]] || '')).trim();
    const name = g('name').replace(/[（(].*?[)）]/g, '').replace(/\\s+/g, '');
    if (!/^[\\u4e00-\\u9fa5·a-zA-Z][\\u4e00-\\u9fa5·a-zA-Z0-9]{1,13}$/.test(name)) { skip.push('第' + (i + 1) + '行姓名看不懂'); return; }
    const sec = secFromCell(g('res'));
    if (!sec) { skip.push('第' + (i + 1) + '行成绩「' + g('res') + '」认不出'); return; }
    const note = g('note');
    rows.push({
      uid: newUid(), name: name, event: g('event') || '5000米',
      sec: Math.round(sec * 10) / 10, fmt: fmtSec(sec),
      date: g('date') || todayStr(), meet: note, note: note, rank: note, ts: Date.now(),
    });
  });
  const mem = new Set(rosterList().map(m => m.name));
  rows.forEach(r => { r._guest = !mem.has(r.name); });
  return { rows: rows, skip: skip, guests: rows.filter(r => r._guest).length };
}

function renderPasteArea() {
  const box = $('#pasteArea');
  if (!box) return;
  const d = pasteRows || { rows: [], skip: [], guests: 0 };
  if (!d.rows.length) {
    box.innerHTML = '<div class="notice" style="margin-top:12px">没解析出可用的行'
      + (d.skip.length ? '：' + esc(d.skip.slice(0, 3).join('；')) : '')
      + '。每行至少要有 姓名,项目,成绩。</div>';
    return;
  }
  box.innerHTML = `
    <div class="tiny" style="margin:12px 0 8px">解析出 <b>${d.rows.length}</b> 条`
      + (d.guests ? '，其中 <b>' + d.guests + '</b> 位不在名册（非队员，只进这场榜）' : '')
      + (d.skip.length ? '；跳过 ' + d.skip.length + ' 条：' + esc(d.skip.slice(0, 3).join('；')) : '') + '</div>
    <div class="tbl-wrap" style="max-height:260px;overflow:auto"><table class="tbl" style="min-width:auto">
      <thead><tr><th class="no-sort">姓名</th><th class="no-sort">项目</th><th class="no-sort">成绩</th>
      <th class="no-sort hide-sm">日期</th><th class="no-sort hide-sm">赛事/名次</th></tr></thead>
      <tbody>${d.rows.slice(0, 60).map(r => `<tr>
        <td><b>${esc(r.name)}</b>${r._guest ? ' <span class="tagbadge">非队员</span>' : ''}</td>
        <td class="tiny">${esc(r.event)}</td><td class="tm">${esc(r.fmt)}</td>
        <td class="tiny hide-sm">${esc(r.date)}</td><td class="tiny hide-sm">${esc(r.meet || '')}</td></tr>`).join('')}</tbody>
    </table></div>
    <div class="chips" style="margin-top:12px">
      <button class="btn" id="btnPasteDo">把这 ${d.rows.length} 条加进来</button>
      <button class="btn flat sm" id="btnPasteCancel">取消</button>
    </div>`;
  const no = $('#btnPasteCancel'), ok = $('#btnPasteDo');
  if (no) no.onclick = () => { pasteRows = null; render(); };
  if (ok) ok.onclick = () => {
    addMyResults(d.rows);
    pasteRows = null;
    toast('已加入 ' + d.rows.length + ' 条。接着：数据管理 → 比赛成绩 → 新建一场 → 把本机录入的成绩并进来 → 同步', 11000);
    render();
  };
}

/* --------------------------------------------- 数据管理交互（队长版） */""",
    '②b 粘贴解析 + 预览函数')

rep("""  const drop = $('#drop'), fi = $('#fileInput');""",
    """  const pg = $('#btnPasteGo');
  if (pg) pg.onclick = () => {
    const ta = $('#pasteBox');
    pasteRows = pasteParseText(ta ? ta.value : '');
    renderPasteArea();
  };

  const drop = $('#drop'), fi = $('#fileInput');""",
    '②c 绑定「解析并预览」')

io.open(P, 'wb').write(s.replace('\n', '\r\n').encode('utf-8'))
print('\n'.join('   ' + d for d in done))

# ── ③ 新页面 report/index.html ──
page = u"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>麦田守望长跑队 · 成绩上报</title>
<link rel="icon" href="../images/logo.jpg">
<link rel="stylesheet" href="../assets/style.css?v=4">
</head>
<body>

<div class="nav" id="nav"></div>
<div class="wrap" id="page"></div>
<div class="toast" id="toast"></div>

<script>
/* 成绩上报页：队员填成绩 → 复制文本 / 导出 CSV → 发给队长导入。不联网、不需要令牌。 */
window.APP_MODE = 'report';
window.APP_ROOT = '../';
(function () {
  var R = window.APP_ROOT;
  var files = [R + 'data/team-data.js', R + 'data/overrides.js'];
  var n = 0;
  function boot() {
    var a = document.createElement('script');
    a.src = R + 'assets/app.js?t=' + Date.now();
    document.head.appendChild(a);
  }
  files.forEach(function (f) {
    var s = document.createElement('script');
    s.src = f + '?t=' + Date.now();
    s.onload = s.onerror = function () { if (++n === files.length) boot(); };
    document.head.appendChild(s);
  });
})();
</script>
</body>
</html>
"""
d = os.path.join(HERE, 'report')
if not os.path.isdir(d):
    os.makedirs(d)
io.open(os.path.join(d, 'index.html'), 'w', encoding='utf-8', newline='\r\n').write(page)
print('   report/index.html 已创建')
