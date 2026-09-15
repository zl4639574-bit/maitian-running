# -*- coding: utf-8 -*-
"""新增「完善队员信息」入口（补齐 性别/学院/专业/年级）
   顺带修 bug：原来的「保存名册修改」不保存性别（所以没填性别的队员一直没地方补）
"""
import io, os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'app.js')
raw = io.open(P, 'rb').read().decode('utf-8')
s = raw.replace('\r\n', '\n')
n0 = len(s)
done = []


def rep(old, new, label, cnt=1):
    global s
    n = s.count(old)
    assert n == cnt, '✗ %s：期望 %d 处，实际 %d 处' % (label, cnt, n)
    s = s.replace(old, new)
    done.append(label)


# ── ① state 加两个 UI 状态 ──
rep("  mComp: '',                                  // 数据管理里选中的比赛",
    "  mComp: '',                                  // 数据管理里选中的比赛\n"
    "  mFillMode: '',                              // 完善信息：'' 收起 / 'lack' 只列信息不全 / 'all' 列全部",
    '① state 加 mFillMode')

# ── ② 抽成 saveRosterEdits() 并把「性别」也存进去 ──
rep("""  const sm = $('#btnSaveMembers');
  if (sm) sm.onclick = () => {
    const edits = ovLocal().memberEdits || (ovLocal().memberEdits = {});
    const byName = {};
    $$('[data-me]').forEach(el => {
      const n = el.dataset.me, f = el.dataset.mf;
      byName[n] = byName[n] || {};
      byName[n][f] = el.value;
    });
    Object.entries(byName).forEach(([n, f]) => {
      const lvl = (f.level || '').split(',').map(s => s.trim()).filter(Boolean);
      const base = (BASE.roster || []).find(m => m.name === n) || {};
      edits[n] = {
        college: f.college, major: f.major, grade: f.grade,
        level: lvl.length ? lvl : (base.level || []).filter(l => l === '正式' || l === '预备'),
      };
    });
    // 队长新加的队员：按 uid 精确保存（同名也不会互相覆盖）
    const byUid = {};
    $$('[data-muid]').forEach(el => {
      const u = el.dataset.muid, f = el.dataset.mf;
      byUid[u] = byUid[u] || {};
      byUid[u][f] = el.value;
    });
    Object.entries(byUid).forEach(([u, f]) => {
      const nm = (ovLocal().newMembers || []).find(m => (m.uid || m.name) === u);
      if (!nm) return;
      nm.college = f.college; nm.major = f.major; nm.grade = f.grade;
      const lvl = (f.level || '').split(',').map(x => x.trim()).filter(Boolean);
      nm.level = lvl.length ? lvl : (nm.level || ['正式']);
    });
    saveLocalOv(); toast('名册修改已保存'); render();
  };""",
    """  const sm = $('#btnSaveMembers');
  if (sm) sm.onclick = () => {
    const n = saveRosterEdits();
    toast('名册修改已保存（' + n + ' 人）—— 记得点「同步我的修改到线上」发布', 9000);
    render();
  };""",
    '② 保存逻辑抽成 saveRosterEdits()')

# 在 pendingCount 之前插入 saveRosterEdits / 完善信息 相关函数
rep("""function pendingCount() {""",
    """/**
 * 收集名册管理区里所有内联修改并写进本机草稿：
 * 学院 / 专业 / 年级 / 性别 / 身份（性别以前没保存，是 bug，这里补上）
 * 返回改动人数。
 */
function saveRosterEdits() {
  const l = ovLocal();
  const edits = l.memberEdits || (l.memberEdits = {});
  const byName = {};
  $$('[data-me]').forEach(el => {
    const n = el.dataset.me, f = el.dataset.mf;
    byName[n] = byName[n] || {};
    byName[n][f] = el.value;
  });
  Object.entries(byName).forEach(([n, f]) => {
    const lvl = (f.level || '').split(',').map(x => x.trim()).filter(Boolean);
    const base = (BASE.roster || []).find(m => m.name === n) || {};
    const out = Object.assign({}, edits[n] || {}, {
      college: f.college, major: f.major, grade: f.grade,
      level: lvl.length ? lvl : (base.level || []).filter(x => x === '正式' || x === '预备'),
    });
    if (f.sex !== undefined) out.sex = f.sex;          // 性别也能补了
    edits[n] = out;
  });
  // 队长新加的队员：按 uid 精确保存（同名也不会互相覆盖）
  const byUid = {};
  $$('[data-muid]').forEach(el => {
    const u = el.dataset.muid, f = el.dataset.mf;
    byUid[u] = byUid[u] || {};
    byUid[u][f] = el.value;
  });
  Object.entries(byUid).forEach(([u, f]) => {
    const nm = (l.newMembers || []).find(m => (m.uid || m.name) === u);
    if (!nm) return;
    nm.college = f.college; nm.major = f.major; nm.grade = f.grade;
    if (f.sex !== undefined) nm.sex = f.sex;
    const lvl = (f.level || '').split(',').map(x => x.trim()).filter(Boolean);
    nm.level = lvl.length ? lvl : (nm.level || ['正式']);
  });
  saveLocalOv();
  return Object.keys(byName).length + Object.keys(byUid).length;
}

/* ---------------- 完善队员信息（补齐 性别 / 学院 / 专业 / 年级）---------------- */

const FILL_FIELDS = ['sex', 'college', 'major', 'grade'];
let fillBatchRows = null;

/** 名册（正式/预备）里信息不全的人 */
function lackInfoList() {
  return rosterList().filter(m => FILL_FIELDS.some(f => !String(m[f] || '').trim()));
}
function isNewMember(m) {
  return (ov().newMembers || []).some(x => (x.uid || x.name) === (m.uid || m.name));
}
/** 完善信息内联表格（复用名册管理那套 data-me / data-muid / data-mf，保存走 saveRosterEdits） */
function fillTableHtml(mode) {
  const list = mode === 'all' ? rosterList() : lackInfoList();
  if (!list.length) return '<div class="notice" style="margin-top:12px">名册里的信息都齐了 ✅</div>';
  return `
    <div class="tiny" style="margin:12px 0 8px">共 <b>${list.length}</b> 人，直接在这里补，补完点下面的「保存这些修改」。</div>
    <div class="tbl-wrap" style="max-height:420px;overflow:auto">
      <table class="tbl" style="min-width:auto"><thead><tr>
        <th class="no-sort">姓名</th><th class="no-sort">性别</th><th class="no-sort">学院</th>
        <th class="no-sort hide-sm">专业</th><th class="no-sort hide-sm">年级</th>
      </tr></thead><tbody>
      ${list.map(m => {
        const k = isNewMember(m) ? ('data-muid="' + esc(m.uid || m.name) + '"') : ('data-me="' + esc(m.name) + '"');
        const lack = FILL_FIELDS.filter(f => !String(m[f] || '').trim());
        return `<tr>
          <td><b>${esc(m.name)}</b>${lack.length ? '<span class="tiny" style="margin-left:6px;color:var(--wheat)">缺 ' + lack.length + ' 项</span>' : ''}</td>
          <td><select ${k} data-mf="sex">
            ${[['', '—'], ['男', '男'], ['女', '女']].map(([v, l]) =>
              `<option value="${v}" ${(m.sex || '') === v ? 'selected' : ''}>${l}</option>`).join('')}
          </select></td>
          <td><input ${k} data-mf="college" value="${esc(m.college || '')}" placeholder="学院"></td>
          <td class="hide-sm"><input ${k} data-mf="major" value="${esc(m.major || '')}" placeholder="专业"></td>
          <td class="hide-sm"><input ${k} data-mf="grade" value="${esc(m.grade || '')}" placeholder="年级" class="w60"></td>
        </tr>`;
      }).join('')}
      </tbody></table>
    </div>
    <div class="chips" style="margin-top:12px">
      <button class="btn" id="btnFillSave">保存这些修改</button>
      <span class="tiny">保存后点「同步我的修改到线上」发布给全队</span>
    </div>`;
}

/** 批量补全：一行一条 姓名,性别,学院,专业,年级（表头自动认列；不填的列 = 不改） */
function fillParseText(txt) {
  const rows = [], skip = [];
  const dir = { name: 0 };
  String(txt || '').split(/\\r?\\n/).forEach((line, i) => {
    const t = line.trim();
    if (!t) return;
    const p = t.split(/[\\t,，、]+/).map(x => x.trim());
    if (i === 0 && /姓名|名字/.test(p[0] || '')) {
      p.forEach((h, idx) => {
        if (/姓名|名字/.test(h)) dir.name = idx;
        else if (/性别/.test(h)) dir.sex = idx;
        else if (/学院/.test(h)) dir.college = idx;
        else if (/专业/.test(h)) dir.major = idx;
        else if (/年级/.test(h)) dir.grade = idx;
      });
      return;
    }
    const g = k => (dir[k] === undefined ? '' : (p[dir[k]] || '')).trim();
    const name = (p[dir.name] || '').trim();
    if (!name) { skip.push('第' + (i + 1) + '行没写姓名'); return; }
    const o = { name: name };
    const sex = g('sex');
    if (sex === '男' || sex === '女') o.sex = sex;
    else if (sex) skip.push('第' + (i + 1) + '行「' + name + '」性别「' + sex + '」认不出（只能填 男/女）');
    if (g('college')) o.college = g('college');
    if (g('major')) o.major = g('major');
    if (g('grade')) o.grade = g('grade').replace(/[^0-9]/g, '') || g('grade');
    if (Object.keys(o).length === 1) { skip.push('第' + (i + 1) + '行「' + name + '」没有要补的信息'); return; }
    rows.push(o);
  });
  const byName = {};
  rosterList().forEach(m => { byName[m.name] = byName[m.name] || []; byName[m.name].push(m); });
  let matched = 0;
  rows.forEach(r => {
    const hit = byName[r.name] || [];
    r._hit = hit.length;
    r._cols = Object.keys(r).filter(x => x !== 'name' && x.indexOf('_') !== 0);
    if (hit.length) matched++;
    r._memo = !hit.length ? '名册里没有这个人（不会写入）'
      : (hit.length > 1 ? '名册里有 ' + hit.length + ' 个同名 → 都会更新' : '');
  });
  return { rows: rows, skip: skip, matched: matched };
}

function applyFill(rows) {
  const l = ovLocal();
  let touched = 0;
  (rows || []).forEach(r => {
    if (!r._hit) return;
    const hit = rosterList().filter(m => m.name === r.name);
    hit.forEach(m => {
      if (isNewMember(m)) {
        const nm = (l.newMembers || []).find(x => (x.uid || x.name) === (m.uid || m.name));
        if (!nm) return;
        FILL_FIELDS.forEach(f => { if (r[f]) nm[f] = r[f]; });
      } else {
        l.memberEdits = l.memberEdits || {};
        const e = l.memberEdits[r.name] = l.memberEdits[r.name] || {};
        FILL_FIELDS.forEach(f => { if (r[f]) e[f] = r[f]; });
      }
      touched++;
    });
  });
  saveLocalOv();
  return touched;
}

function renderFillBatch() {
  const box = $('#fillBatchBox');
  if (!box) return;
  const d = fillBatchRows || { rows: [], skip: [], matched: 0 };
  if (!d.rows.length) {
    box.innerHTML = '<div class="notice" style="margin-top:12px">没解析出可用的行'
      + (d.skip.length ? '：' + esc(d.skip.slice(0, 3).join('；')) : '')
      + '。每行至少要有姓名 + 要补的一项。</div>';
    return;
  }
  const label = { sex: '性别', college: '学院', major: '专业', grade: '年级' };
  box.innerHTML = `
    <div class="tiny" style="margin:12px 0 8px">
      解析出 <b>${d.rows.length}</b> 行，其中 <b>${d.matched}</b> 行能在名册里找到人`
      + (d.skip.length ? '；跳过 ' + d.skip.length + ' 条：' + esc(d.skip.slice(0, 3).join('；')) : '') + '</div>
    <div class="tbl-wrap" style="max-height:280px;overflow:auto">
      <table class="tbl" style="min-width:auto"><thead><tr>
        <th class="no-sort">姓名</th><th class="no-sort">要补的</th><th class="no-sort hide-sm">说明</th>
      </tr></thead><tbody>
      ${d.rows.slice(0, 80).map(r => `<tr>
        <td><b>${esc(r.name)}</b></td>
        <td class="tiny">${esc(r._cols.map(c => label[c] + '=' + r[c]).join('，'))}</td>
        <td class="tiny hide-sm">${r._hit ? esc(r._memo) : '<span style="color:#c0392b">' + esc(r._memo) + '</span>'}</td>
      </tr>`).join('')}
      </tbody></table>
    </div>
    <div class="chips" style="margin-top:12px">
      <button class="btn" id="btnFillConfirm">补全这 ${d.matched} 人</button>
      <button class="btn ghost" id="btnFillCancel">取消</button>
    </div>`;
  const ok = $('#btnFillConfirm'), no = $('#btnFillCancel');
  if (no) no.onclick = () => { fillBatchRows = null; render(); };
  if (ok) ok.onclick = () => {
    const n = applyFill(d.rows);
    fillBatchRows = null;
    toast('已补全 ' + n + ' 人 —— 记得点「同步我的修改到线上」发布', 10000);
    render();
  };
}

function pendingCount() {""",
    '②b 插入 saveRosterEdits / fillTableHtml / fillParseText / applyFill / renderFillBatch')

# ── ③ 名册管理行里加「性别」（这样列表里也能直接补）──
rep("""          <div class="mrow-f">
            <input ${k} data-mf="college" value="${esc(e.college != null ? e.college : (m.college || ''))}" placeholder="学院">""",
    """          <div class="mrow-f">
            <select ${k} data-mf="sex">
              ${[['', '性别—'], ['男', '男'], ['女', '女']].map(([v, l]) =>
                `<option value="${v}" ${((e.sex != null ? e.sex : (m.sex || '')) || '') === v ? 'selected' : ''}>${l}</option>`).join('')}
            </select>
            <input ${k} data-mf="college" value="${esc(e.college != null ? e.college : (m.college || ''))}" placeholder="学院">""",
    '③ 名册管理行加性别下拉')

# ── ④ 队员名册分区里插入「完善队员信息」界面 ──
rep("""    <div class="mgrid">""",
    u"""    <div class="notice" style="margin-bottom:18px">
      <b>＋ 完善队员信息（补齐 性别 / 学院 / 专业 / 年级）</b>
      <div class="tiny" style="margin:8px 0">
        当初只填了个名字、信息没填全的队员，在这里补齐就行。名册现在 ${rosterList().length} 人，
        其中 <b>${lackInfoList().length}</b> 人信息不全${lackSexCount ? '（缺性别 ' + lackSexCount + ' 人）' : ''}。
      </div>
      <div class="chips">
        <button class="btn" id="btnFillList">列出信息不全的 ${lackInfoList().length} 人</button>
        <button class="btn ghost" id="btnFillAll">列出名册全部 ${rosterList().length} 人</button>
      </div>
      <div id="fillBox">${state.mFillMode ? fillTableHtml(state.mFillMode) : ''}</div>
      <div class="tiny" style="margin-top:14px">批量补全：一行一条 <b>姓名,性别,学院,专业,年级</b>（不补的列就空着或少写；有表头会自动认列）</div>
      <textarea class="ta" id="fillBatch" rows="4" placeholder="阿巴小洛,男&#10;汪楷,男,水保所,水保2201,2020"></textarea>
      <div class="chips" style="margin-top:10px"><button class="btn ghost" id="btnFillPreview">解析并预览</button></div>
      <div id="fillBatchBox"></div>
    </div>

    <div class="mgrid">""",
    '④ 名册分区加完善信息界面')

# ── ⑤ renderManage 里算「缺性别」人数 ──
rep("""  const cfg = ghCfg();
  const pend = pendingCount();""",
    """  const cfg = ghCfg();
  const pend = pendingCount();
  const lackSexCount = rosterList().filter(m => !String(m.sex || '').trim()).length;""",
    '⑤ 统计缺性别人数')

# ── ⑥ 绑定按钮 ──
rep("""  const pbp = $('#btnPbPreview');""",
    """  const bfl = $('#btnFillList');
  if (bfl) bfl.onclick = () => { state.mFillMode = 'lack'; render(); };
  const bfa = $('#btnFillAll');
  if (bfa) bfa.onclick = () => { state.mFillMode = 'all'; render(); };
  const bfs = $('#btnFillSave');
  if (bfs) bfs.onclick = () => {
    const n = saveRosterEdits();
    state.mFillMode = 'lack';
    toast('已保存 ' + n + ' 人的信息 —— 记得点「同步我的修改到线上」发布', 10000);
    render();
  };
  const bfp = $('#btnFillPreview');
  if (bfp) bfp.onclick = () => {
    const ta = $('#fillBatch');
    fillBatchRows = fillParseText(ta ? ta.value : '');
    renderFillBatch();
  };
  const pbp = $('#btnPbPreview');""",
    '⑥ 绑定完善信息按钮')

out = s.replace('\n', '\r\n')
io.open(P, 'wb').write(out.encode('utf-8'))
print('\n'.join('  ' + d for d in done))
print('app.js: %d → %d 字符' % (n0, len(s)))
