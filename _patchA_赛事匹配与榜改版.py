# -*- coding: utf-8 -*-
"""A 补丁：① 上报时赛事名自动匹配已有赛事 ② 成绩榜以「个人最好成绩」为主，赛事单独一个键跳转"""
import io, os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'app.js')
s = io.open(P, 'rb').read().decode('utf-8').replace('\r\n', '\n')
done = []


def rep(old, new, label, cnt=1):
    global s
    n = s.count(old)
    assert n == cnt, '✗ %s：期望 %d 处，实际 %d 处' % (label, cnt, n)
    s = s.replace(old, new)
    done.append(label)


# ── ① 状态里加 compList ──
rep("""  comp: '',                                   // '' = 个人最好成绩，否则是某场比赛的 id""",
    """  comp: '',                                   // '' = 个人最好成绩，否则是某场比赛的 id
  compList: false,                            // 成绩榜：是否展开「赛事列表」""",
    '①a state.compList')

# ── ② chips 行：PB + 赛事成绩（一个键） ──
rep("""  const chipsRow = `
  <div class="chips sec">
    <div class="chip ${state.comp === '' ? 'active' : ''}" data-comp="">个人最好成绩</div>
    ${comps.map(c => `<div class="chip ${state.comp === c.id ? 'active' : ''}" data-comp="${esc(c.id)}">${esc(c.short || c.name)}
      <span class="n">${c.records.length}</span></div>`).join('')}
  </div>`;""",
    """  const inComps = !!cur || state.compList;
  const chipsRow = `
  <div class="chips sec">
    <div class="chip ${!inComps ? 'active' : ''}" data-comp="">个人最好成绩</div>
    <div class="chip ${inComps ? 'active' : ''}" data-complist="1">赛事成绩
      <span class="n">${comps.length}</span></div>
  </div>`;""",
    '②a chips 变成两个键')

# ── ③ 赛事列表视图 ──
rep("""  /* ---------- 个人最好成绩 ---------- */
  const all = personalBests();""",
    """  /* ---------- 赛事列表：点进去看某一场 ---------- */
  if (state.compList) {
    const rows = comps.slice().sort((a, b) => dateKey(b.date) - dateKey(a.date));
    return head + chipsRow + `
    <div class="card sec" style="padding:14px 18px">
      <div class="tiny" style="line-height:1.8">一共 <b>${rows.length}</b> 场（比赛 + 队内测速）。
        点一场看那场的完整成绩册；<b>个人最好成绩</b>请点上面的「个人最好成绩」。</div>
    </div>

    <div class="comp-list">
      ${rows.map(c => `<div class="comp-row" data-comp="${esc(c.id)}">
        <div class="l">
          <div class="t"><b>${esc(c.short || c.name)}</b>${!c.builtin ? ' <span class="tagbadge green">队长新增</span>' : ''}</div>
          <div class="tiny">${esc(c.date || '日期未标注')}${c.event ? ' · ' + esc(c.event) : ''}${c.records.length ? '' : ' · 还没有成绩'}</div>
        </div>
        <div class="r">${c.records.length}<span class="u">条</span> →</div>
      </div>`).join('')}
    </div>`;
  }

  /* ---------- 个人最好成绩 ---------- */
  const all = personalBests();""",
    '③a 赛事列表视图')

# ── ④ 某场比赛页加「← 赛事列表」 ──
rep("""        ${MODE === 'captain' ? ' · <a href="#" data-go="manage" data-msec="comp">添加/修改这场比赛</a>' : ''}""",
    """        · <a href="#" data-complist="1">← 赛事列表</a>${MODE === 'captain' ? ' · <a href="#" data-go="manage" data-msec="comp">添加/修改这场比赛</a>' : ''}""",
    '④a 比赛页返回入口')

# ── ⑤ 点击处理：支持 data-complist 和赛事行 ──
rep("""  if (d.comp !== undefined && t.classList.contains('chip')) { state.comp = d.comp; state.pbQ = ''; state.pbSex = ''; return render(); }""",
    """  if (d.complist !== undefined) { state.compList = true; state.comp = ''; state.pbQ = ''; state.pbSex = ''; return render(); }
  if (d.comp !== undefined && (t.classList.contains('chip') || t.classList.contains('comp-row')
      || t.closest('.comp-row') || t.classList.contains('l') || t.classList.contains('t') || t.classList.contains('r'))) {
    const row = t.closest('.comp-row');
    state.comp = row ? row.dataset.comp : d.comp;
    state.compList = false; state.pbQ = ''; state.pbSex = ''; return render();
  }""",
    '⑤a 点击逻辑')

# ── ⑥ 赛事名匹配 ──
rep("""/* ---------------- 粘贴文本导入（队员上报的文字直接用）---------------- */""",
    """/* ---------------- 赛事名匹配（上报时自动对到已有赛事）---------------- */

/** 归一化：去掉空格、标点、年月日等，方便比对 */
function meetNorm(t) {
  return String(t || '').toLowerCase()
    .replace(/[\\s　]/g, '')
    .replace(/[（）()【】\\[\\]「」《》·,，.。、:：;；!！?？"'”“\-—_/\\\\|]/g, '')
    .replace(/20\\d\\d年?/g, '')
    .replace(/(比赛|赛事|马拉松|半马|全马|测速|测试|春季|冬季|秋季|夏季|校内|校园|校运会|运动会)/g, '');
}
/** 最长公共子串长度 */
function lcsLen(a, b) {
  let best = 0;
  const dp = new Array(b.length + 1).fill(0);
  for (let i = 1; i <= a.length; i++) {
    let prev = 0;
    for (let j = 1; j <= b.length; j++) {
      const tmp = dp[j];
      dp[j] = (a[i - 1] === b[j - 1]) ? prev + 1 : 0;
      if (dp[j] > best) best = dp[j];
      prev = tmp;
    }
  }
  return best;
}
/** 已有赛事的候选名（含短名） */
function meetCandidates() {
  const out = [];
  competitions().forEach(c => {
    if (c.name) out.push({ label: c.name, id: c.id });
    if (c.short && c.short !== c.name) out.push({ label: c.short, id: c.id });
  });
  return out;
}
/** 找最像的已有赛事；没有够像的就返回 null（= 新赛事） */
function meetMatch(v) {
  const q = meetNorm(v);
  if (q.length < 2) return null;
  let best = null;
  meetCandidates().forEach(c => {
    const n = meetNorm(c.label);
    if (!n) return;
    let sc = lcsLen(q, n) / Math.min(q.length, n.length);
    if (n.indexOf(q) >= 0 || q.indexOf(n) >= 0) sc += 0.25;
    if (n === q) sc = 1;
    if (!best || sc > best.sc) best = { sc: sc, label: c.label, id: c.id };
  });
  return (best && best.sc >= 0.45) ? best : null;
}

/* ---------------- 粘贴文本导入（队员上报的文字直接用）---------------- */""",
    '⑥a 匹配算法')

rep("""      <div class="field"><label>赛事名称 / 备注</label><input id="f_meet" placeholder="例如 2026 杨凌马拉松"></div>""",
    """      <div class="field"><label>赛事名称 / 备注</label>
        <input id="f_meet" placeholder="例如 2026 杨凌马拉松" list="meetList" autocomplete="off">
        <datalist id="meetList">${meetCandidates().map(c => `<option value="${esc(c.label)}">`).join('')}</datalist>
        <div class="tiny" id="meetHint" style="margin-top:4px">打几个字就会自动对上已有的赛事名</div>
      </div>""",
    '⑥b 输入框加候选 + 提示')

rep("""  const cp = $('#btnCopy');""",
    """  const mi = $('#f_meet');
  if (mi) mi.oninput = () => {
    const h = $('#meetHint');
    if (!h) return;
    const v = mi.value.trim();
    if (!v) { h.innerHTML = '打几个字就会自动对上已有的赛事名'; return; }
    const m = meetMatch(v);
    if (m && meetNorm(m.label) === meetNorm(v)) {
      h.innerHTML = '✅ 对上了已有赛事：<b>' + esc(m.label) + '</b>';
    } else if (m) {
      h.innerHTML = '≈ 最像已有赛事：<b>' + esc(m.label) + '</b>　'
        + '<a href="#" id="meetUse">用这个</a>　（不点它就会算成新赛事）';
      const u = $('#meetUse');
      if (u) u.onclick = (e) => { e.preventDefault(); mi.value = m.label; mi.oninput(); };
    } else {
      h.innerHTML = '🆕 这是新赛事名（队长那边会新建/合并这一场）';
    }
  };

  const cp = $('#btnCopy');""",
    '⑥c 输入时给匹配提示')

# ── ⑦ 样式：追加到 style.css ──
CSS_ADD = '''
/* ------------------------------------------------ 赛事列表 / 队员头像 */

.comp-list { margin-top: 8px; }
.comp-row {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  background: var(--card); border: 1px solid var(--line); border-radius: 16px;
  padding: 14px 18px; margin-bottom: 10px; cursor: pointer;
  transition: box-shadow .18s, transform .18s, border-color .18s;
}
.comp-row:hover { box-shadow: 0 8px 22px rgba(20,120,31,.10); border-color: var(--green-line); }
.comp-row .t { font-size: 15px; color: var(--t1); }
.comp-row .r { color: var(--green); font-weight: 700; font-size: 17px; white-space: nowrap; }
.comp-row .r .u { font-size: 12px; font-weight: 400; color: var(--t3); margin-left: 2px; }
.avatar {
  width: 46px; height: 46px; border-radius: 50%; object-fit: cover;
  background: var(--green-soft); border: 1px solid var(--green-line); flex: 0 0 auto;
}
.pcard .head-row { display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }
.pcard .head-row .who { min-width: 0; }
.pcard .head-row .nm { margin-bottom: 2px; }
'''
CSSP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'style.css')
css = io.open(CSSP, encoding='utf-8').read()
if 'comp-row' not in css:
    CRLF = chr(13) + chr(10)
    io.open(CSSP, 'w', encoding='utf-8', newline='').write(css.rstrip() + CRLF + CSS_ADD.replace(chr(10), CRLF))
    done.append('⑦a style.css 追加赛事列表/头像样式')
else:
    done.append('⑦a style.css 已有样式，跳过')

io.open(P, 'wb').write(s.replace('\n', '\r\n').encode('utf-8'))
print('\n'.join('   ' + d for d in done))
