# -*- coding: utf-8 -*-
"""新增「单独添加个人最好成绩」：
   overrides 加 pbAdded / pbHidden 两个字段（五处合并点全改）
   + 数据管理→队员名册 里的单条添加/批量导入/删除 UI
"""
import io, os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'app.js')
raw = io.open(P, 'rb').read().decode('utf-8')
assert '\r\n' in raw, '不是 CRLF？'
s = raw.replace('\r\n', '\n')
orig_len = len(s)
done = []


def rep(old, new, label, cnt=1):
    global s
    n = s.count(old)
    assert n == cnt, '✗ %s：期望 %d 处，实际 %d 处' % (label, cnt, n)
    s = s.replace(old, new)
    done.append(label)


# ── ① EMPTY_OV ──
rep("                   hall: null, queue: null };",
    "                   hall: null, queue: null, pbAdded: [], pbHidden: [] };",
    '① EMPTY_OV 加 pbAdded/pbHidden')

# ── ② ov() 合并 + mergePbAdded 辅助 ──
rep("""    compRecords: mergeCompRecords(c.compRecords, l.compRecords),
    hiddenRecords:""",
    """    compRecords: mergeCompRecords(c.compRecords, l.compRecords),
    pbAdded: (function () {
      const hid = new Set((c.pbHidden || []).concat(l.pbHidden || []));
      return mergePbAdded(c.pbAdded, l.pbAdded)
        .filter(p => !hid.has(p.uid || (p.name + '|' + p.event)));
    })(),
    pbHidden: Array.from(new Set((c.pbHidden || []).concat(l.pbHidden || []))),
    hiddenRecords:""",
    '② ov() 合并 pbAdded/pbHidden')

rep("""function mergeCompRecords(a, b) {""",
    """/** 单独录入的个人最好成绩：按 uid 合并（本机覆盖云端），没有 uid 的老数据用 姓名|项目 兜底 */
function mergePbAdded(a, b) {
  const key = x => (x && (x.uid || ((x.name || '') + '|' + (x.event || '')))) || '';
  const m = {};
  (a || []).forEach(x => { if (x && x.name) m[key(x)] = x; });
  (b || []).forEach(x => { if (x && x.name) m[key(x)] = x; });
  return Object.keys(m).map(k => m[k]);
}

function mergeCompRecords(a, b) {""",
    '②b 加 mergePbAdded()')

# ── ③ 派生展示：personalBests() / memberBests() ──
rep("""    } else if (r.sec === map[k].sec && r.local) {
      map[k].local = true;
    }
  });
  return Object.values(map);""",
    """    } else if (r.sec === map[k].sec && r.local) {
      map[k].local = true;
    }
  });
  // 手工「单独添加」的个人最好成绩（同样只统计正式队员）
  ov().pbAdded.forEach(p => {
    if (!p.name || !p.sec || !official.has(p.name)) return;
    const k = p.name + '|' + (p.event || '');
    const rec = Object.assign({}, p, {
      manual: true, fmt: p.fmt || fmtSec(p.sec),
      srcLabel: p.note ? ('单独录入 · ' + p.note) : '单独录入',
      src: '单独录入', srcDate: p.date || '',
    });
    if (!map[k] || p.sec < map[k].sec) map[k] = rec;
  });
  return Object.values(map);""",
    '③ personalBests() 并入手工成绩')

rep("""function memberBests(name) {
  const m = {};
  allResults().forEach(r => {
    if (r.name !== name) return;
    const k = r.event || r.srcLabel;
    if (!m[k] || r.sec < m[k].sec) m[k] = { sec: r.sec, fmt: r.fmt || fmtSec(r.sec) };
  });
  return m;
}""",
    """function memberBests(name) {
  const m = {};
  allResults().forEach(r => {
    if (r.name !== name) return;
    const k = r.event || r.srcLabel;
    if (!m[k] || r.sec < m[k].sec) m[k] = { sec: r.sec, fmt: r.fmt || fmtSec(r.sec) };
  });
  ov().pbAdded.forEach(p => {                      // 队长单独录入的最好成绩
    if (p.name !== name || !p.sec) return;
    const k = p.event || '个人最好成绩';
    if (!m[k] || p.sec < m[k].sec) m[k] = { sec: p.sec, fmt: p.fmt || fmtSec(p.sec), manual: true };
  });
  return m;
}""",
    '③b memberBests() 并入手工成绩')

# 名册卡片最多显示 3 条
rep("      const items = Object.entries(b).slice(0, 2);",
    "      const items = Object.entries(b).sort((x, y) => x[1].sec - y[1].sec).slice(0, 3);",
    '③c 名册卡片显示 3 条')

# ── ④ pendingCount ──
rep("""  if (l.hiddenRecords && l.hiddenRecords.length) n += l.hiddenRecords.length;""",
    """  if (l.hiddenRecords && l.hiddenRecords.length) n += l.hiddenRecords.length;
  if (l.pbAdded) n += l.pbAdded.length;
  if (l.pbHidden) n += l.pbHidden.length;""",
    '④ pendingCount 计入 PB 改动')

# ── ⑤ pushToGitHub 的 merged（最危险的一处）──
rep("""      compRecords: mergeCompRecords(cloud.compRecords, l.compRecords),
      hiddenRecords: Array.from(new Set((cloud.hiddenRecords || []).concat(l.hiddenRecords || []))),""",
    """      compRecords: mergeCompRecords(cloud.compRecords, l.compRecords),
      pbAdded: (function () {
        const hid = new Set((cloud.pbHidden || []).concat(l.pbHidden || []));
        return mergePbAdded(cloud.pbAdded, l.pbAdded)
          .filter(p => !hid.has(p.uid || (p.name + '|' + p.event)));
      })(),
      pbHidden: Array.from(new Set((cloud.pbHidden || []).concat(l.pbHidden || []))),
      hiddenRecords: Array.from(new Set((cloud.hiddenRecords || []).concat(l.hiddenRecords || []))),""",
    '⑤ pushToGitHub merged 带上 pbAdded/pbHidden')

# ── ⑥ UI：队员名册分区里加「单独添加个人最好成绩」 ──
rep("""    <div class="mgrid">""",
    u"""    <div class="notice" style="margin-bottom:18px;border-color:var(--wheat)">
      <b>＋ 单独添加个人最好成绩（不用编一场比赛）</b>
      <div class="tiny" style="margin:8px 0">
        直接给某个队员记一条最好成绩（例如半马、全马、10 公里、3000 米）。它会出现在
        「个人最好成绩」榜（只统计正式队员）和该队员的名册卡片上；加完点「同步我的修改到线上」即上线。
      </div>
      <div class="grid2" style="margin:10px 0 4px">
        <div class="field"><label>姓名 *</label><input id="pb_name" list="pbNames" placeholder="例如 阿巴小洛"></div>
        <div class="field"><label>项目 *</label><input id="pb_event" list="pbEvents" placeholder="例如 半马"></div>
        <div class="field"><label>成绩 *</label><input id="pb_time" placeholder="1:23:29 或 17:02"></div>
        <div class="field"><label>日期</label><input id="pb_date" placeholder="2025.4.21"></div>
        <div class="field"><label>赛事 / 备注</label><input id="pb_note" placeholder="杨凌马拉松"></div>
      </div>
      <datalist id="pbNames">${(BASE.roster || []).map(m => '<option value="' + esc(m.name) + '"></option>').join('')}</datalist>
      <datalist id="pbEvents">${Array.from(new Set(allResults().map(r => r.event).filter(Boolean))).map(e => '<option value="' + esc(e) + '"></option>').join('')}</datalist>
      <button class="btn" id="btnAddPb">添加这条成绩</button>
      <span class="tiny" style="margin-left:10px">加完点「同步我的修改到线上」发布</span>
      <div id="pbBox"></div>
      <div class="tiny" style="margin-top:14px">批量导入：一行一条，<b>姓名,项目,成绩[,日期,备注]</b>（逗号 / 制表符都行，可从 Excel 直接复制）</div>
      <textarea class="ta" id="pbBatch" rows="4" placeholder="阿巴小洛,半马,1:23:29,2025.4.21,杨凌马拉松&#10;汪楷,全马,2:58:00"></textarea>
      <div class="chips" style="margin-top:10px"><button class="btn ghost" id="btnPbPreview">解析并预览</button></div>
      <div id="pbBatchBox"></div>
      <div style="margin-top:16px">
        <b class="tiny">已录入的个人最好成绩（${pbListAll().length} 条，含线上已上线的）</b>
        <div class="chips" style="margin-top:8px">
          ${pbListAll().slice(0, 100).map(p => `<div class="chip">${esc(p.name)} · ${esc(p.event)} <b>${esc(p.fmt || fmtSec(p.sec))}</b>${p.date ? '（' + esc(p.date) + '）' : ''}<span data-pbdel="${esc(p.uid || (p.name + '|' + p.event))}" style="cursor:pointer;color:#c0392b;margin-left:8px">✕</span></div>`).join('') || '<span class="tiny">还没有单独录入的成绩</span>'}
        </div>
        <div class="tiny" style="margin-top:8px">点 ✕ 删除（线上已上线的也能删，删完点「同步」）</div>
      </div>
    </div>

    <div class="mgrid">""",
    '⑥ 名册分区加 PB 录入界面')

# ── ⑦ 逻辑函数：列表 / 解析 / 预览（插在 renderNmBatch 之后）──
rep("""function renderNmBatch() {""",
    u"""/** 单独录入的个人最好成绩：云端 + 本机（去掉已删的） */
let pbBatchRows = null;
function pbUid() { return 'pb' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }
function pbListAll() {
  const hid = new Set((((CLOUD_OV || {}).pbHidden) || []).concat(((LOCAL_OV || {}).pbHidden) || []));
  const m = {};
  (((CLOUD_OV || {}).pbAdded) || []).concat(((LOCAL_OV || {}).pbAdded) || []).forEach(p => {
    if (p && p.name) m[p.uid || (p.name + '|' + p.event)] = p;
  });
  return Object.keys(m).map(k => m[k]).filter(p => !hid.has(p.uid || (p.name + '|' + p.event)));
}
/** 一行一条：姓名,项目,成绩[,日期,备注] */
function pbParseText(txt) {
  const rows = [], skip = [];
  String(txt || '').split(/\\r?\\n/).forEach((line, i) => {
    const t = line.trim();
    if (!t) return;
    const p = t.split(/[\\t,，、]+/).map(x => x.trim());
    if (/姓名|名字/.test(p[0] || '')) return;                       // 表头跳过
    if (!p[0] || !p[1] || !p[2]) { skip.push('第' + (i + 1) + '行少列（要 姓名,项目,成绩）'); return; }
    const sec = parseSec(p[2]);
    if (!sec) { skip.push('第' + (i + 1) + '行「' + p[2] + '」认不出成绩'); return; }
    rows.push({ uid: pbUid(), name: p[0], event: p[1], sec: sec, fmt: fmtSec(sec),
                date: p[3] || '', note: p[4] || '' });
  });
  return { rows: rows, skip: skip };
}

function renderPbBatch() {
  const box = $('#pbBatchBox');
  if (!box) return;
  const d = pbBatchRows || { rows: [], skip: [] };
  if (!d.rows.length) {
    box.innerHTML = '<div class="notice" style="margin-top:12px">没解析出可用的成绩'
      + (d.skip.length ? '：' + esc(d.skip.slice(0, 3).join('；')) : '')
      + '。每行至少要有 姓名、项目、成绩 三列。</div>';
    return;
  }
  box.innerHTML = `
    <div class="tiny" style="margin:12px 0 8px">解析出 <b>${d.rows.length}</b> 条`
      + (d.skip.length ? '；跳过 ' + d.skip.length + ' 条：' + esc(d.skip.slice(0, 3).join('；')) : '') + '</div>
    <div class="tbl-wrap" style="max-height:280px;overflow:auto">
      <table class="tbl" style="min-width:auto"><thead><tr>
        <th class="no-sort">姓名</th><th class="no-sort">项目</th><th class="no-sort">成绩</th>
        <th class="no-sort hide-sm">日期</th><th class="no-sort hide-sm">备注</th>
      </tr></thead><tbody>
      ${d.rows.slice(0, 80).map(r => `<tr><td><b>${esc(r.name)}</b></td><td class="tiny">${esc(r.event)}</td>
        <td class="tiny"><b>${esc(r.fmt)}</b></td><td class="tiny hide-sm">${esc(r.date)}</td>
        <td class="tiny hide-sm">${esc(r.note)}</td></tr>`).join('')}
      </tbody></table>
    </div>
    <div class="chips" style="margin-top:12px">
      <button class="btn" id="btnPbConfirm">把这 ${d.rows.length} 条加进去</button>
      <button class="btn ghost" id="btnPbCancel">取消</button>
    </div>`;
  const ok = $('#btnPbConfirm'), no = $('#btnPbCancel');
  if (no) no.onclick = () => { pbBatchRows = null; render(); };
  if (ok) ok.onclick = () => {
    const l = ovLocal();
    l.pbAdded = l.pbAdded || [];
    d.rows.forEach(r => l.pbAdded.push(r));
    saveLocalOv();
    pbBatchRows = null;
    toast('已记下 ' + d.rows.length + ' 条个人最好成绩 —— 记得点「同步我的修改到线上」发布', 10000);
    render();
  };
}

function renderNmBatch() {""",
    '⑦ 加 pbListAll / pbParseText / renderPbBatch')

# ── ⑧ 绑定按钮 ──
rep("""  const rsy = $('#btnRosterSync');
  if (rsy) rsy.onclick = () => pushToGitHub();""",
    u"""  const rsy = $('#btnRosterSync');
  if (rsy) rsy.onclick = () => pushToGitHub();
  // —— 单独添加个人最好成绩 ——
  const addPb = $('#btnAddPb');
  if (addPb) addPb.onclick = () => {
    const name = ($('#pb_name').value || '').trim().replace(/\\s/g, '');
    const event = ($('#pb_event').value || '').trim();
    const sec = parseSec(($('#pb_time').value || '').trim());
    if (!name) return toast('请填姓名');
    if (!event) return toast('请填项目（例如 半马 / 5000米 / 全马）');
    if (!sec) return toast('成绩认不出：可写 1:23:29（时:分:秒）或 17:02（分:秒）', 8000);
    const l = ovLocal();
    l.pbAdded = l.pbAdded || [];
    l.pbAdded.push({ uid: pbUid(), name: name, event: event, sec: sec, fmt: fmtSec(sec),
                     date: ($('#pb_date').value || '').trim(), note: ($('#pb_note').value || '').trim() });
    saveLocalOv();
    toast('已记下 ' + name + ' 的 ' + event + ' ' + fmtSec(sec) + ' —— 记得点「同步我的修改到线上」发布', 9000);
    render();
  };
  const pbp = $('#btnPbPreview');
  if (pbp) pbp.onclick = () => {
    const ta = $('#pbBatch');
    pbBatchRows = pbParseText(ta ? ta.value : '');
    renderPbBatch();
  };
  document.querySelectorAll('[data-pbdel]').forEach(x => {
    x.onclick = () => {
      const id = x.dataset.pbdel, l = ovLocal();
      l.pbAdded = (l.pbAdded || []).filter(p => (p.uid || (p.name + '|' + p.event)) !== id);
      l.pbHidden = l.pbHidden || [];
      if (l.pbHidden.indexOf(id) < 0) l.pbHidden.push(id);
      saveLocalOv();
      toast('已删掉这条成绩 —— 点「同步我的修改到线上」，展示版也会一起删掉', 9000);
      render();
    };
  });""",
    '⑧ 绑定 PB 录入/批量/删除按钮')

out = s.replace('\n', '\r\n')
io.open(P, 'wb').write(out.encode('utf-8'))
print('\n'.join('  ' + d for d in done))
print('app.js: %d → %d 字符' % (orig_len, len(s)))
