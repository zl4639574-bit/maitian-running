# -*- coding: utf-8 -*-
"""B. 数据管理新增「数据表」分区：导出队员数据表(Excel) / 导入修正表(批量改正+同步)"""
import io

p = "assets/app.js"
s = io.open(p, encoding="utf-8", newline="").read().replace("\r\n", "\n")
orig = len(s)

# ── B1 分区列表加「数据表」 ────────────────────────────────────────────────
old = r"""  const SEC = [['sync', '同步'], ['comp', '比赛成绩'], ['team', '队伍信息'],
               ['honors', '荣誉'], ['hall', '优秀队员'], ['member', '队员名册'], ['photos', '照片'],
               ['results', '自由成绩']];"""
new = r"""  const SEC = [['sync', '同步'], ['comp', '比赛成绩'], ['team', '队伍信息'],
               ['honors', '荣誉'], ['hall', '优秀队员'], ['member', '队员名册'], ['table', '数据表'],
               ['photos', '照片'], ['results', '自由成绩']];"""
assert s.count(old) == 1, "B1 SEC"
s = s.replace(old, new)

# ── B2 数据表分区 HTML（放在名册分区之后）──────────────────────────────────
old = r"""  ${state.manageSec === 'photos' ? `"""
new = r"""  ${state.manageSec === 'table' ? `
  <div class="card sec">
    <h2>队员数据表（导出 / 改好导回）</h2>
    <div class="tiny" style="line-height:2">
      ① <b>导出</b>：把当前所有人 + 所有成绩导成一份 Excel（队员总表 / 成绩明细 / 有成绩但不在名册里 / 说明）。<br>
      ② 在 Excel 里改错的地方（学院写错、成绩多打一位…），改完把文件<b>导回来</b>；
         网站会先算出差异给你看，确认后一次性修正，再去「同步」发布，不用一条条点。<br>
      ③ 也可以在 Excel 里<b>加新队员</b>（队员总表加一行）或<b>补录成绩</b>（成绩明细加一行，【编号】留空）。<br>
      ④ Excel 里的各项目「最好成绩」列是自动算的，不用改（改了也不会生效）。
    </div>
    <div class="chips" style="margin-top:14px">
      <button class="btn" id="btnDtExport">导出队员数据表（Excel）</button>
      <button class="btn ghost" id="btnDtImport">选择改好的 Excel 导回</button>
      <input type="file" id="dtFile" accept=".xlsx,.xls" style="display:none">
    </div>
    <div id="dtBox" style="margin-top:14px"></div>
  </div>` : ''}

  ${state.manageSec === 'photos' ? `"""
assert s.count(old) == 1, "B2 数据表分区"
s = s.replace(old, new)

# ── B3 修正在场记录时允许 keep 标记（改成绩时"藏旧加新"，两条同一秒也不打架）──
old = r"""  const build = (id, base) => (base || []).concat(add[id] || [])
    .filter(r => r && r.name && r.sec && !hid.has(id + '|' + r.name + '|' + r.sec));"""
new = r"""  const build = (id, base) => (base || []).concat(add[id] || [])
    .filter(r => r && r.name && r.sec && (r.keep || !hid.has(id + '|' + r.name + '|' + r.sec)));"""
assert s.count(old) == 1, "B3 keep"
s = s.replace(old, new)

# ── B4 导出/导入的实现（插在 bindManage 之前）──────────────────────────────
old = r"""/* ---------------- 批量添加队员：粘贴表格或选文件 → 解析预览 → 一次入库 ---------------- */"""
new = r"""/* ---------------- 队员数据表：导出 / 改好导回（批量修正） ---------------- */

const DT_EVENTS = ['5000米', '3000米', '10000米', '1500米', '半马', '全马', '4公里', '12公里', '16公里'];
let fixPlan = null;

function dtCollect() {
  const o = ov();
  const members = (BASE.roster || []).map(m => {
    const e = o.memberEdits[m.name] || {};
    return Object.assign({}, m, e, { _from: '原始名册', _hidden: (o.hidden || []).indexOf(m.name) >= 0 });
  }).concat((o.newMembers || []).map(m => Object.assign({}, m, { _from: '队长新增', _hidden: false })));
  const records = [];
  competitions().forEach(c => (c.records || []).forEach(r => records.push(Object.assign({}, r, {
    _src: c.short || c.name, _date: c.date || '', _kind: '比赛/测速',
    _key: 'comp:' + c.id + '|' + r.name + '|' + r.sec,
  }))));
  (o.results || []).forEach(r => records.push(Object.assign({}, r, {
    _src: r.meet || '队伍上传', _date: r.date || '', _kind: '自由成绩',
    _key: 'res:' + (r.uid || (r.name + '|' + r.sec)),
  })));
  const best = {};
  records.forEach(r => {
    const n = r.name, ev = r.event || '未标注', sec = Number(r.sec);
    if (!n || !sec) return;
    const k = n + '|' + ev;
    if (!best[k] || sec < best[k].sec) best[k] = { sec: sec, src: r._src, date: r._date };
  });
  const events = DT_EVENTS.filter(e => Object.keys(best).some(k => k.split('|')[1] === e));
  Object.keys(best).forEach(k => { const ev = k.split('|')[1]; if (events.indexOf(ev) < 0) events.push(ev); });
  return { members: members, records: records, best: best, events: events };
}

function sheetAoa(wb, name) {
  const ws = wb.Sheets[name];
  if (!ws) return [];
  return XLSX.utils.sheet_to_json(ws, { header: 1, raw: true, defval: '' });
}

function exportDataTable() {
  if (typeof XLSX === 'undefined') return toast('表格功能还没加载好，刷新页面再试', 8000);
  const d = dtCollect();
  const wb = XLSX.utils.book_new();

  const head = ['序号', '姓名', '性别', '学院', '专业', '年级', '身份', '公开显示', '成绩条数', '来源']
    .concat(d.events.map(e => e + '最好成绩')).concat(['备注标签']);
  const aoa = [head];
  const byName = {};
  d.records.forEach(r => { (byName[r.name] = byName[r.name] || []).push(r); });
  const rank = m => { const l = m.level || []; return l.indexOf('正式') >= 0 ? 0 : (l.indexOf('预备') >= 0 ? 1 : 2); };
  d.members.slice().sort((a, b) => rank(a) - rank(b) || String(a.name).localeCompare(String(b.name), 'zh'))
    .forEach((m, i) => {
      const lv = m.level || [];
      const pub = (lv.indexOf('正式') >= 0 || lv.indexOf('预备') >= 0) && !m._hidden;
      const row = [i + 1, m.name || '', m.sex || '', m.college || '', m.major || '', m.grade || '',
                   lv.length ? lv.join('/') : '未分级', pub ? '是' : '否', (byName[m.name] || []).length, m._from || ''];
      d.events.forEach(e => {
        const b = d.best[m.name + '|' + e];
        row.push(b ? fmtSec(b.sec) : '');
      });
      row.push((m.tags || []).join('/'));
      aoa.push(row);
    });
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(aoa), '队员总表');

  const aoa2 = [['编号', '姓名', '性别', '项目', '成绩', '秒', '日期', '来源', '类型', '名次/备注']];
  d.records.slice().sort((a, b) => String(a.name).localeCompare(String(b.name), 'zh')).forEach(r => {
    aoa2.push([r._key, r.name || '', r.sex || '', r.event || '', r.fmt || fmtSec(r.sec), Number(r.sec) || '',
               r.date || r._date || '', r.meet || r._src || '', r._kind, r.rank || r.note || '']);
  });
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(aoa2), '成绩明细');

  const names = new Set(d.members.map(m => m.name));
  const orph = {};
  d.records.forEach(r => { if (r.name && !names.has(r.name)) (orph[r.name] = orph[r.name] || []).push(r.event || ''); });
  const aoa3 = [['姓名', '成绩条数', '涉及项目']].concat(Object.keys(orph).sort()
    .map(n => [n, orph[n].length, Array.from(new Set(orph[n].filter(Boolean))).join('/')]));
  if (aoa3.length > 1) XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(aoa3), '有成绩但不在名册里');

  const aoa4 = [
    ['队员数据表 —— 怎么改（改完把这个文件导回网页）'],
    ['导出时间', new Date().toLocaleString()],
    ['队员人数', d.members.length], ['成绩条数', d.records.length],
    [''],
    ['【队员总表】'],
    ['· 可改：性别 / 学院 / 专业 / 年级 / 身份（身份填 正式、预备、正式/预备；留空 = 不进公开名册）'],
    ['· 加新队员：最下面加一行，姓名必填；其他列能填就填'],
    ['· 不要改：序号 / 公开显示 / 成绩条数 / 各项目最好成绩（这些是自动算的）'],
    [''],
    ['【成绩明细】'],
    ['· 可改：项目 / 成绩 / 日期 / 名次备注'],
    ['· 删一条：把【成绩】那一格清空（或写“删除”）'],
    ['· 补录一条：最下面加一行，【编号】留空，填 姓名/项目/成绩/日期/来源'],
    ['   （来源写某场比赛的名字，就进那场的榜；留空 = 进自由成绩）'],
    ['· 千万不要改【编号】列，那是用来认这条成绩的'],
    [''],
    ['【规则】'],
    ['· 个人最好成绩只统计正式队员；每场比赛的榜包含当时参赛的所有同学'],
    ['· 某项目的最好成绩 = 该项目所有成绩里最快的一次，改完成绩会自动重算'],
  ];
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(aoa4), '说明');

  XLSX.writeFile(wb, '队员数据表.xlsx');
  toast('已导出：队员 ' + d.members.length + ' 人 / 成绩 ' + d.records.length + ' 条', 9000);
}

function buildFixPlan(sheets) {
  const o = ov();
  const baseByName = {}, curNew = {};
  (BASE.roster || []).forEach(m => { baseByName[m.name] = m; });
  (o.newMembers || []).forEach(m => { curNew[m.name] = m; });
  const plan = { memberFix: [], addMember: [], recFix: [], recHide: [], recDel: [], recAdd: [], recEdit: [], skip: [] };
  const normLevel = v => {
    const t = String(v == null ? '' : v).trim();
    if (!t || t === '未分级' || t === '-' || t === '无' || t === '否' || t === '0') return [];
    return t.split(/[,，、+/]/).map(x => x.trim()).filter(x => x === '正式' || x === '预备');
  };
  const sameLv = (a, b) => (a || []).slice().sort().join('/') === (b || []).slice().sort().join('/');

  const mt = sheets['队员总表'] || [];
  if (mt.length > 1) {
    const head = mt[0].map(x => String(x == null ? '' : x).trim());
    const at = (re, dflt) => { const i = head.findIndex(h => re.test(h)); return i >= 0 ? i : dflt; };
    const iN = at(/姓名/, 1), iS = at(/性别/, 2), iC = at(/学院/, 3), iM = at(/专业/, 4), iG = at(/年级/, 5), iL = at(/身份/, 6);
    mt.slice(1).forEach(row => {
      const name = String(row[iN] == null ? '' : row[iN]).trim().replace(/\s/g, '');
      if (!name) return;
      const g = (i) => String(row[i] == null ? '' : row[i]).trim();
      const info = { sex: g(iS), college: g(iC), major: g(iM), grade: g(iG), level: normLevel(row[iL]) };
      const cur = baseByName[name] ? Object.assign({}, baseByName[name], o.memberEdits[name] || {}) : curNew[name];
      if (!cur) { plan.addMember.push({ name: name, info: info }); return; }
      const diff = ['sex', 'college', 'major', 'grade'].filter(f => (info[f] || '') !== (cur[f] || ''));
      if (!sameLv(cur.level, info.level)) diff.push('身份');
      if (diff.length) plan.memberFix.push({ name: name, info: info, diff: diff, isNew: !baseByName[name], uid: cur.uid || '' });
    });
  }

  const rd = sheets['成绩明细'] || [];
  if (rd.length > 1) {
    const head = rd[0].map(x => String(x == null ? '' : x).trim());
    const at = (re, dflt) => { const i = head.findIndex(h => re.test(h)); return i >= 0 ? i : dflt; };
    const iK = at(/编号/, 0), iN = at(/姓名/, 1), iE = at(/项目/, 3), iR = at(/成绩/, 4),
          iSec = at(/秒/, 5), iD = at(/日期/, 6), iSrc = at(/来源/, 7), iNote = at(/名次|备注/, 9);
    const comps = competitions();
    const all = comps.reduce((a, c) => a.concat((c.records || []).map(r => Object.assign({}, r, { _cid: c.id }))), []);
    const findComp = (s) => comps.find(c => String(c.short) === s || String(c.name) === s)
      || comps.find(c => String(c.short || '').indexOf(s) >= 0);
    rd.slice(1).forEach(row => {
      const g = (i) => String(row[i] == null ? '' : row[i]).trim();
      const name = g(iN).replace(/\s/g, '');
      if (!name) return;
      const key = g(iK), ev = g(iE), rawRes = g(iR), date = g(iD), src = g(iSrc), note = g(iNote);
      const sec = Number(row[iSec]) > 0 ? Number(row[iSec]) : parseSec(rawRes);
      const isDel = !rawRes || /删除|删掉|delete|×/i.test(rawRes);

      if (key.indexOf('comp:') === 0) {
        const parts = key.slice(5).split('|');
        const cid = parts[0], oldSec = Number(parts[parts.length - 1]);
        const orig = all.find(r => r._cid === cid && r.name === name && Math.abs(Number(r.sec) - oldSec) < 0.05);
        if (!orig) { plan.skip.push('找不到：' + name + ' ' + (ev || '') + ' ' + (rawRes || '')); return; }
        if (isDel) {
          plan.recHide.push({ hideKey: cid + '|' + name + '|' + oldSec,
            desc: name + ' ' + (orig.event || '') + ' ' + (orig.fmt || fmtSec(orig.sec)) });
          return;
        }
        if (!sec) { plan.skip.push(name + ' 的成绩看不懂：' + rawRes); return; }
        if (Math.abs(sec - oldSec) > 0.05 || (ev && ev !== orig.event) || date !== (orig.date || '')
            || note !== (orig.note || orig.rank || '')) {
          plan.recFix.push({
            cid: cid, hideKey: cid + '|' + name + '|' + oldSec,
            desc: name + ' ' + (orig.event || '') + ' ' + (orig.fmt || fmtSec(orig.sec))
                  + ' → ' + (ev || orig.event) + ' ' + fmtSec(sec),
            rec: { name: name, event: ev || orig.event, raw: rawRes, sec: sec, fmt: fmtSec(sec),
                   sex: orig.sex || '', college: orig.college || '', date: date || orig.date || '',
                   note: note || '', keep: true },
          });
        }
        return;
      }
      if (key.indexOf('res:') === 0) {
        const uid = key.slice(4);
        const cur = (ovLocal().results || []).find(r => (r.uid || (r.name + '|' + r.sec)) === uid);
        if (!cur) { plan.skip.push('找不到自由成绩：' + name); return; }
        if (isDel) { plan.recDel.push({ uid: uid, desc: name + ' ' + (cur.event || '') + ' ' + (cur.fmt || fmtSec(cur.sec)) }); return; }
        if (sec && (Math.abs(sec - Number(cur.sec)) > 0.05 || (ev && ev !== cur.event) || date !== (cur.date || ''))) {
          plan.recEdit.push({ uid: uid, desc: name + ' ' + (cur.event || '') + ' ' + (cur.fmt || fmtSec(cur.sec))
            + ' → ' + (ev || cur.event) + ' ' + fmtSec(sec),
            rec: Object.assign({}, cur, { event: ev || cur.event, raw: rawRes, sec: sec, fmt: fmtSec(sec),
                                          date: date || cur.date, meet: src || cur.meet }) });
        }
        return;
      }
      if (!sec) { plan.skip.push(name + ' 这行没有编号、成绩也认不出来，已跳过'); return; }
      const c = src ? findComp(src) : null;
      plan.recAdd.push({ cid: c ? c.id : '', compName: c ? (c.short || c.name) : '',
        rec: { uid: 'r' + Date.now() + '_' + plan.recAdd.length, name: name, event: ev || '未标注',
               raw: rawRes, sec: sec, fmt: fmtSec(sec), date: date, meet: src, note: note, ts: Date.now() } });
    });
  }
  return plan;
}

function renderFixPlan() {
  const box = $('#dtBox');
  if (!box || !fixPlan) return;
  const p = fixPlan;
  const total = p.memberFix.length + p.addMember.length + p.recFix.length + p.recEdit.length
    + p.recHide.length + p.recDel.length + p.recAdd.length;
  if (!total) {
    box.innerHTML = '<div class="notice">没有发现差异 —— 文件里的数据跟现在一致。'
      + (p.skip.length ? '<br><span class="tiny">跳过 ' + p.skip.length + ' 行：' + esc(p.skip.slice(0, 3).join('；')) + '</span>' : '')
      + '</div>';
    return;
  }
  const li = (n, txt) => n ? '<li>' + txt + '</li>' : '';
  box.innerHTML = `
  <div class="notice" style="border-color:var(--wheat)">
    <b>发现这些改动，确认后一次性应用（应用完去「同步」发布）：</b>
    <ul style="margin:10px 0 0 18px;line-height:1.9">
      ${li(p.memberFix.length, '修改队员信息 ' + p.memberFix.length + ' 人：' + esc(p.memberFix.slice(0, 6).map(x => x.name + '（' + x.diff.join('、') + '）').join('；')) + (p.memberFix.length > 6 ? ' 等' : ''))}
      ${li(p.addMember.length, '新增队员 ' + p.addMember.length + ' 人：' + esc(p.addMember.slice(0, 10).map(x => x.name).join('、')))}
      ${li(p.recFix.length, '修正成绩 ' + p.recFix.length + ' 条：' + esc(p.recFix.slice(0, 5).map(x => x.desc).join('；')) + (p.recFix.length > 5 ? ' 等' : ''))}
      ${li(p.recEdit.length, '修改自由成绩 ' + p.recEdit.length + ' 条：' + esc(p.recEdit.slice(0, 5).map(x => x.desc).join('；')))}
      ${li(p.recHide.length, '删除成绩 ' + p.recHide.length + ' 条：' + esc(p.recHide.slice(0, 5).map(x => x.desc).join('；')))}
      ${li(p.recDel.length, '删除自由成绩 ' + p.recDel.length + ' 条：' + esc(p.recDel.slice(0, 5).map(x => x.desc).join('；')))}
      ${li(p.recAdd.length, '补录成绩 ' + p.recAdd.length + ' 条：' + esc(p.recAdd.slice(0, 5).map(x => x.rec.name + ' ' + x.rec.event + ' ' + x.rec.fmt + (x.compName ? '（' + x.compName + '）' : '（自由成绩）')).join('；')))}
    </ul>
    ${p.skip.length ? '<div class="tiny" style="margin-top:8px">跳过 ' + p.skip.length + ' 行：' + esc(p.skip.slice(0, 3).join('；')) + (p.skip.length > 3 ? ' 等' : '') + '</div>' : ''}
    <div class="chips" style="margin-top:12px">
      <button class="btn" id="btnDtApply">应用这些修正</button>
      <button class="btn ghost" id="btnDtCancel">取消</button>
    </div>
  </div>`;
  const ap = $('#btnDtApply'), cc = $('#btnDtCancel');
  if (cc) cc.onclick = () => { fixPlan = null; render(); };
  if (ap) ap.onclick = applyFixPlan;
}

function applyFixPlan() {
  const p = fixPlan;
  if (!p) return;
  const l = ovLocal();
  l.memberEdits = l.memberEdits || {};
  l.newMembers = l.newMembers || [];
  l.hiddenRecords = l.hiddenRecords || [];
  l.compRecords = l.compRecords || {};
  p.memberFix.forEach(x => {
    if (x.isNew) {
      const m = l.newMembers.filter(m => m.name === x.name && (!x.uid || m.uid === x.uid))[0];
      if (m) Object.assign(m, x.info);
    } else {
      l.memberEdits[x.name] = Object.assign({}, l.memberEdits[x.name], x.info);
    }
  });
  p.addMember.forEach(x => {
    l.newMembers.push(Object.assign({ uid: nmUid(), name: x.name, addedAt: new Date().toISOString().slice(0, 10) }, x.info));
  });
  p.recHide.forEach(x => { l.hiddenRecords.push(x.hideKey); });
  p.recFix.forEach(x => {
    l.hiddenRecords.push(x.hideKey);
    (l.compRecords[x.cid] = l.compRecords[x.cid] || []).push(x.rec);
  });
  p.recDel.forEach(x => { l.results = (l.results || []).filter(r => (r.uid || (r.name + '|' + r.sec)) !== x.uid); });
  p.recEdit.forEach(x => {
    (l.results = l.results || []).forEach(r => { if ((r.uid || (r.name + '|' + r.sec)) === x.uid) Object.assign(r, x.rec); });
  });
  p.recAdd.forEach(x => {
    if (x.cid) { (l.compRecords[x.cid] = l.compRecords[x.cid] || []).push(x.rec); }
    else { l.results = (l.results || []).concat([x.rec]); }
  });
  saveLocalOv();
  const total = p.memberFix.length + p.addMember.length + p.recFix.length + p.recEdit.length
    + p.recHide.length + p.recDel.length + p.recAdd.length;
  fixPlan = null;
  toast('已应用 ' + total + ' 处修正 —— 去「同步」点一次「同步我的修改到线上」就上线了', 11000);
  render();
}

/* ---------------- 批量添加队员：粘贴表格或选文件 → 解析预览 → 一次入库 ---------------- */"""
assert s.count(old) == 1, "B4 数据表函数"
s = s.replace(old, new)

# ── B5 事件绑定 ────────────────────────────────────────────────────────────
old = r"""  const nbp = $('#btnNmPreview');"""
new = r"""  const dte = $('#btnDtExport');
  if (dte) dte.onclick = exportDataTable;
  const dti = $('#btnDtImport'), dtf = $('#dtFile');
  if (dti && dtf) {
    dti.onclick = () => dtf.click();
    dtf.onchange = () => {
      const f = dtf.files && dtf.files[0];
      if (!f) return;
      const fr = new FileReader();
      fr.onerror = () => toast('文件读不出来，换一个试试', 8000);
      fr.onload = () => {
        try {
          const wb = XLSX.read(new Uint8Array(fr.result), { type: 'array' });
          const sheets = {};
          ['队员总表', '成绩明细'].forEach(n => { if (wb.SheetNames.indexOf(n) >= 0) sheets[n] = sheetAoa(wb, n); });
          if (!sheets['队员总表'] && !sheets['成绩明细'])
            return toast('这个文件里没有「队员总表」或「成绩明细」工作表 —— 请用网站导出的那份改', 10000);
          fixPlan = buildFixPlan(sheets);
          renderFixPlan();
        } catch (e) {
          toast('解析失败：' + String((e && e.message) || e).slice(0, 60), 10000);
        }
      };
      fr.readAsArrayBuffer(f);
    };
  }
  const nbp = $('#btnNmPreview');"""
assert s.count(old) == 1, "B5 事件绑定"
s = s.replace(old, new)

io.open(p, "w", encoding="utf-8", newline="\r\n").write(s)
print("B 完成: %d -> %d 字符" % (orig, len(s)))
