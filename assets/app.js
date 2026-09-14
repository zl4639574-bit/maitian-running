/* ==========================================================================
   麦田守望长跑队 · 数据中心
   一套代码，三种模式：展示版(view) / 队员版(member) / 队长版(captain)
   - 展示版：只读，给全队和外面看
   - 队员版：手机可以录自己的成绩
   - 队长版：批量导入、照片上传、队伍信息与名册管理、一键同步到线上
   ========================================================================== */
'use strict';

const MODE = window.APP_MODE || 'view';        // view | member | captain
const ROOT = window.APP_ROOT || '';            // 子目录页面用 '../'

/* ------------------------------------------------------------------ 工具 */

const $  = (s, r) => (r || document).querySelector(s);
const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function parseSec(v) {
  if (v === null || v === undefined || v === '') return null;
  if (v instanceof Date) {
    if (v.getFullYear() <= 1900) return v.getHours() * 60 + v.getMinutes() + v.getSeconds() / 60;
    return null;
  }
  if (typeof v === 'number') {
    if (v > 0 && v < 1) {
      const t = v * 86400, h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), s = Math.round(t % 60);
      return h * 60 + m + s / 60;
    }
    return v < 60 ? v * 60 : v;
  }
  let s = String(v).trim()
    .replace(/[’‘′]/g, "'").replace(/[”“″]/g, '"').replace(/：/g, ':').replace(/\s/g, '');
  if (!s) return null;
  if (/dns|dnf|缺|误|请假|未参加|无成绩|退赛/i.test(s)) return null;
  s = s.replace(/[（(][^)）]*[)）]/g, '').trim();
  if (s.indexOf("'") >= 0 || s.indexOf('"') >= 0) {
    const p = s.split(/['"]/).filter(x => x !== '').map(Number);
    if (p.some(isNaN)) return null;
    if (p.length === 1) return p[0];
    if (p.length === 2) return p[0] * 60 + p[1];
    return null;
  }
  if (s.indexOf(':') >= 0) {
    const p = s.split(':').filter(x => x !== '').map(Number);
    if (p.some(isNaN)) return null;
    if (p.length === 3) {
      if (p[2] === 0 && p[0] < 60 && p[1] < 60) return p[0] * 60 + p[1];
      return p[0] * 3600 + p[1] * 60 + p[2];
    }
    if (p.length === 2) return p[0] * 60 + p[1];
    return null;
  }
  const f = parseFloat(s);
  if (isNaN(f) || f <= 0) return null;
  return f < 60 ? f * 60 : f;
}

function fmtSec(sec) {
  if (sec === null || sec === undefined || isNaN(sec)) return '-';
  sec = Math.round(sec * 10) / 10;
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = Math.round(sec % 60);
  const p2 = n => (n < 10 ? '0' + n : '' + n);
  return h >= 1 ? h + ':' + p2(m) + ':' + p2(s) : m + ':' + p2(s);
}

function distM(ev) {
  const s = String(ev || '');
  if (/半马|半程|21\.0975/.test(s)) return 21097.5;
  if (/全马|全程|42\.195/.test(s)) return 42195;
  let m = s.match(/(\d+(?:\.\d+)?)\s*(公里|千米|km|KM)/i);
  if (m) return parseFloat(m[1]) * 1000;
  m = s.match(/(\d+)\s*米/);
  if (m) return parseFloat(m[1]);
  return 0;
}

function fmtPace(sec, ev) {
  const d = distM(ev);
  if (!d || !sec) return '—';
  return fmtSec(sec / (d / 1000)) + '/km';
}

function todayStr() {
  const d = new Date(), p = n => (n < 10 ? '0' + n : n);
  return d.getFullYear() + '.' + p(d.getMonth() + 1) + '.' + p(d.getDate());
}

let _uid = 0;
function newUid() {
  return 'r' + Date.now().toString(36) + '_' + (++_uid) + '_' + Math.random().toString(36).slice(2, 6);
}

function toast(msg, ms) {
  let t = $('#toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('on');
  clearTimeout(t._tm);
  t._tm = setTimeout(() => t.classList.remove('on'), ms || 2400);
}

function download(name, text, mime) {
  const blob = new Blob([text], { type: mime || 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}

function copyText(txt) {
  const done = () => toast('已复制，直接粘贴到微信里就行');
  const fail = () => {
    const ta = document.createElement('textarea');
    ta.value = txt;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); done(); } catch (e) { toast('复制失败，请手动选择'); }
    ta.remove();
  };
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(txt).then(done, fail);
  else fail();
}

/* -------------------------------------------------------------- 本地存储 */

const LS_RESULTS = 'mt_results_v1';      // 录入的成绩（队员/队长）
const LS_LOCAL   = 'mt_ov_local_v1';     // 队长本机未同步的修改
const LS_CFG     = 'mt_gh_cfg_v1';       // 队长版：GitHub 同步配置

function lsGet(k, dflt) {
  try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : dflt; }
  catch (e) { return dflt; }
}
function lsSet(k, v) {
  try { localStorage.setItem(k, JSON.stringify(v)); return true; }
  catch (e) { toast('这个浏览器不让存数据，改动无法保存'); return false; }
}

function myResults() {
  const list = lsGet(LS_RESULTS, []);
  let dirty = false;
  list.forEach((r, i) => { if (!r.uid) { r.uid = 'r' + (r.ts || 0) + '_' + i; dirty = true; } });
  if (dirty) lsSet(LS_RESULTS, list);
  return list;
}
function setMyResults(l) { lsSet(LS_RESULTS, l); }
function addMyResults(recs) { const l = myResults().concat(recs); lsSet(LS_RESULTS, l); return l; }
function delMyResult(uid) { lsSet(LS_RESULTS, myResults().filter(r => r.uid !== uid)); }

/* ------------------------------------------------------------ 数据合并层 */

const BASE = window.TEAM_DATA || { team: {}, roster: [], datasets: [], pb: [] };
const BASE_PHOTOS = window.TEAM_PHOTOS || { photos: [] };

const EMPTY_OV = { team: {}, honors: null, activities: null, hidden: [], memberEdits: {},
                   results: [], photos: [], competitions: [], hiddenRecords: [],
                   hall: null, queue: null };

let CLOUD_OV = null;      // 云端 overrides.json（线上生效的修改）
let LOCAL_OV = MODE === 'captain' ? lsGet(LS_LOCAL, null) : null;   // 队长本机未同步的修改
let SYNC_STATE = 'loading';   // loading | cloud | local | offline

function ov() {
  const c = CLOUD_OV || {}, l = LOCAL_OV || {};
  return {
    team: Object.assign({}, c.team || {}, l.team || {}),
    honors: l.honors || c.honors || null,
    activities: l.activities || c.activities || null,
    hidden: Array.from(new Set((c.hidden || []).concat(l.hidden || []))),
    memberEdits: Object.assign({}, c.memberEdits || {}, l.memberEdits || {}),
    results: (c.results || []).concat(l.results || []),
    photos: (c.photos || []).concat(l.photos || []),
    competitions: (c.competitions || []).concat(l.competitions || []),
    compRecords: mergeCompRecords(c.compRecords, l.compRecords),
    hiddenRecords: Array.from(new Set((c.hiddenRecords || []).concat(l.hiddenRecords || []))),
    hall: l.hall || c.hall || null,
    queue: l.queue || c.queue || null,
  };
}

function mergeCompRecords(a, b) {
  const out = {};
  [a || {}, b || {}].forEach(src => Object.keys(src).forEach(k => {
    out[k] = (out[k] || []).concat(src[k] || []);
  }));
  return out;
}

/** 每场比赛 / 每次测速的成绩册：原始资料里的 + 队长补充的成绩 - 被删掉的 */
function competitions() {
  const o = ov();
  const hid = new Set(o.hiddenRecords);
  const add = o.compRecords || {};
  const build = (id, base) => (base || []).concat(add[id] || [])
    .filter(r => r && r.name && r.sec && !hid.has(id + '|' + r.name + '|' + r.sec));
  const out = (BASE.datasets || []).map(ds => ({
    id: ds.id, builtin: true,
    name: ds.label + (ds.date ? '（' + ds.date + '）' : ''),
    short: ds.label, date: ds.date, event: (ds.events && ds.events[0]) ? ds.events[0].event : '',
    note: ds.note || '', source: ds.source || '',
    records: build(ds.id, ds.records),
  }));
  o.competitions.forEach(c => out.push(Object.assign({ builtin: false, short: c.name }, c,
    { records: build(c.id, c.records) })));
  out.sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')));
  return out;
}

function teamInfo() {
  const o = ov();
  return Object.assign({}, BASE.team, o.team, {
    honors: o.honors || BASE.team.honors || [],
    activities: o.activities || BASE.team.activities || [],
  });
}

/** 名册：只保留正式 / 预备 队员，去掉被删的，套用修改 */
function rosterList() {
  const o = ov();
  const hidden = new Set(o.hidden);
  return (BASE.roster || [])
    .filter(m => !hidden.has(m.name))
    .filter(m => (m.level || []).some(l => l === '正式' || l === '预备'))
    .map(m => {
      const e = o.memberEdits[m.name] || {};
      return Object.assign({}, m, e, {
        level: e.level || (m.level || []).filter(l => l === '正式' || l === '预备'),
      });
    });
}

/** 所有成绩（每场比赛 + 线上发布的自由成绩 + 本机的） */
function allResults() {
  const out = [];
  competitions().forEach(c => (c.records || []).forEach(r => out.push(Object.assign({}, r, {
    srcLabel: c.name, srcDate: c.date, src: c.name, compId: c.id,
  }))));
  ov().results.forEach(r => out.push(Object.assign({}, r, {
    published: true, srcLabel: r.meet || '队伍上传', srcDate: r.date || '',
    src: (r.meet || '队伍上传') + ' ' + (r.date || ''),
  })));
  if (MODE !== 'view') myResults().forEach(r => out.push(Object.assign({}, r, {
    local: true, srcLabel: r.meet || '本机上传', srcDate: r.date || '',
    src: (r.meet || '本机上传') + ' ' + (r.date || ''),
  })));
  return out;
}

/** 成绩榜唯一内容：跨表个人最好成绩 */
function personalBests() {
  const map = {};
  allResults().forEach(r => {
    if (!r.name || !r.sec) return;
    const k = r.name + '|' + (r.event || '');
    if (!map[k] || r.sec < map[k].sec) {
      map[k] = Object.assign({}, r, { event: r.event || '距离未标注' });
    } else if (r.sec === map[k].sec && r.local) {
      map[k].local = true;
    }
  });
  return Object.values(map);
}

function memberBests(name) {
  const m = {};
  allResults().forEach(r => {
    if (r.name !== name) return;
    const k = r.event || r.srcLabel;
    if (!m[k] || r.sec < m[k].sec) m[k] = { sec: r.sec, fmt: r.fmt || fmtSec(r.sec) };
  });
  return m;
}

/** 相册：一个赛事一堆照片 */
function albums() {
  const all = (BASE_PHOTOS.photos || []).concat(ov().photos || []);
  const map = {};
  all.forEach(p => {
    const key = p.album || '未分类';
    if (!map[key]) map[key] = { name: key, date: p.albumDate || '', photos: [] };
    map[key].photos.push(p);
    if (p.albumDate && !map[key].date) map[key].date = p.albumDate;
  });
  return Object.values(map).sort((a, b) => {
    if (!a.date && !b.date) return b.photos.length - a.photos.length;
    if (!a.date) return 1;
    if (!b.date) return -1;
    return b.date.localeCompare(a.date);
  });
}

function photoSrc(p) {
  return p.data ? p.data : ROOT + 'images/' + p.file;
}

/* ------------------------------------------------------------------ 状态 */

const state = {
  tab: 'home',
  comp: '',                                   // '' = 个人最好成绩，否则是某场比赛的 id
  pbEvent: '', pbSex: '', pbQ: '', pbSort: null,
  rosterLevel: '', rosterQ: '', rosterCollege: '',
  album: '', photoCat: '',
  manageSec: 'sync',
  mRosterQ: '',
  mComp: '',                                  // 数据管理里选中的比赛
};

const MEDAL = ['', 'g1', 'g2', 'g3'];

const TABS = {
  view:    [['home', '总览'], ['board', '成绩榜'], ['roster', '队员名册'], ['photos', '照片墙'], ['about', '荣誉与资料']],
  member:  [['home', '总览'], ['board', '成绩榜'], ['roster', '队员名册'], ['upload', '上传成绩'], ['photos', '照片墙'], ['about', '荣誉与资料']],
  captain: [['home', '总览'], ['board', '成绩榜'], ['roster', '队员名册'], ['upload', '上传成绩'],
            ['manage', '数据管理'], ['photos', '照片墙'], ['about', '荣誉与资料']],
};

/* --------------------------------------------------------------- 渲染：总览 */

function renderHome() {
  const ros = rosterList();
  const recs = allResults().length;
  const pb = personalBests();
  const alb = albums();
  const latest = (BASE.datasets || []).slice().sort((a, b) => String(b.date).localeCompare(String(a.date)))[0];
  const latestEv = latest && latest.events && latest.events[0] ? latest.events[0].event : '';
  const top = latestEv ? personalBests()
    .filter(r => r.event === latestEv && (BASE.datasets || []).some(d => d.id === latest.id))
    .slice(0, 0) : [];
  // 最近一次测速的现场名次（用原始那次的记录，不是 PB）
  const live = latest ? (latest.records || []).filter(r => r.event === latestEv && r.rank <= 5) : [];

  return `
  <div class="hero">
    ${BASE_PHOTOS.logo ? `<img class="logo" src="${ROOT}images/${esc(BASE_PHOTOS.logo)}" alt="队徽">` : ''}
    <h1>${esc(teamInfo().name || '麦田守望长跑队')}</h1>
    <p class="sub">${esc(teamInfo().alias || '')} · 成立于 ${esc(teamInfo().founded || '')}</p>
    <div class="slogan">${esc(teamInfo().slogan || '')}</div>
  </div>

  <div class="stats-row">
    <div class="stat-card"><div class="v">${ros.length}</div><div class="k">在册队员</div></div>
    <div class="stat-card"><div class="v">${pb.length}</div><div class="k">个人最好成绩</div></div>
    <div class="stat-card"><div class="v">${recs}</div><div class="k">成绩记录</div></div>
    <div class="stat-card"><div class="v">${alb.reduce((a, x) => a + x.photos.length, 0)}</div><div class="k">照片（${alb.length} 个相册）</div></div>
  </div>

  <div class="card sec">
    <div class="sec-head"><h2>队伍简介</h2>
      <button class="btn ghost sm" data-go="about">队伍荣誉 →</button></div>
    <p class="sub" style="line-height:1.85;font-size:14.5px">${esc(teamInfo().intro || '')}</p>
    <div class="chips" style="margin-top:16px">
      ${(teamInfo().media || []).map(m => `<span class="chip" style="cursor:default">${esc(m[0])} · ${esc(m[1])}</span>`).join('')}
    </div>
  </div>

  ${MODE !== 'view' ? `
  <div class="card sec">
    <div class="sec-head"><h2>上传我的成绩</h2><button class="btn sm" data-go="upload">去上传 →</button></div>
    <p class="sub">${myResults().length
      ? `本机已记录 <b>${myResults().length}</b> 条成绩，会显示在「成绩榜」里（带「本机」标记）。`
      : '把你最近一次测速、比赛的成绩录进来，就能在成绩榜看到自己的最好成绩。'}</p>
  </div>` : ''}

  ${latest ? `
  <div class="card sec">
    <div class="sec-head">
      <h2>最近一次测速 · ${esc(latest.label)}</h2>
      <button class="btn ghost sm" data-go="board">看最好成绩榜 →</button>
    </div>
    <div class="tiny" style="margin-bottom:14px">${esc(latest.date)} · ${esc(latestEv)} · 共 ${latest.count} 条记录</div>
    <div class="best-list">
      ${live.map(r => `
        <div class="best-row">
          <div class="medal ${MEDAL[r.rank] || ''}">${r.rank}</div>
          <div class="nm">${esc(r.name)}<span class="tiny" style="margin-left:8px">${esc(r.college || '')}</span></div>
          <div class="tm">${esc(r.fmt)}</div>
        </div>`).join('') || '<div class="empty">暂无记录</div>'}
    </div>
  </div>` : ''}

  <div class="card sec">
    <div class="sec-head"><h2>照片墙</h2>
      <button class="btn ghost sm" data-go="photos">看全部相册 →</button></div>
    <div class="albrow">
      ${alb.slice(0, 4).map(a => `
        <div class="albmini" data-album="${esc(a.name)}">
          <img src="${photoSrc(a.photos[0])}" loading="lazy" alt="${esc(a.name)}">
          <div class="albmini-m"><div class="n">${esc(a.name)}</div><div class="c">${a.photos.length} 张</div></div>
        </div>`).join('')}
    </div>
  </div>

  <div class="card sec">
    <div class="sec-head"><h2>近几年的主要战绩</h2>
      <button class="btn ghost sm" data-go="about">全部荣誉 →</button></div>
    <div class="timeline">
      ${(teamInfo().honors || []).slice(-4).map(h => `
        <div class="tl-item"><div class="tl-year">${esc(h[0])}</div><div class="tl-text">${esc(h[1])}</div></div>`).join('')}
    </div>
  </div>`;
}

/* ------------------------------------------------------------ 渲染：成绩榜 */

function renderBoard() {
  const comps = competitions();
  const cur = state.comp ? comps.find(c => c.id === state.comp) : null;
  if (state.comp && !cur) state.comp = '';

  const chipsRow = `
  <div class="chips sec">
    <div class="chip ${state.comp === '' ? 'active' : ''}" data-comp="">个人最好成绩</div>
    ${comps.map(c => `<div class="chip ${state.comp === c.id ? 'active' : ''}" data-comp="${esc(c.id)}">${esc(c.short || c.name)}
      <span class="n">${c.records.length}</span></div>`).join('')}
  </div>`;

  const head = `
  <div class="sec-head"><h1>成绩榜</h1>
    ${MODE !== 'view' ? '<button class="btn ghost sm" data-go="upload">＋ 上传我的成绩</button>' : ''}
    ${MODE === 'captain' ? '<button class="btn ghost sm" data-go="manage" data-msec="comp">管理比赛成绩 →</button>' : ''}</div>`;

  /* ---------- 某一场比赛的成绩册 ---------- */
  if (cur) {
    const evs = Array.from(new Set(cur.records.map(r => r.event).filter(Boolean)));
    let rows = cur.records.slice();
    if (state.pbSex) rows = rows.filter(r => r.sex === state.pbSex);
    if (state.pbQ) {
      const q = state.pbQ.toLowerCase();
      rows = rows.filter(r => (r.name || '').toLowerCase().includes(q) || (r.college || '').toLowerCase().includes(q));
    }
    rows.sort((a, b) => distM(b.event) - distM(a.event) || String(a.event).localeCompare(String(b.event), 'zh') || a.sec - b.sec);
    const rk = {};
    rows.forEach(r => { rk[r.event || ''] = (rk[r.event || ''] || 0) + 1; r._rk = rk[r.event || '']; });

    return head + chipsRow + `
    <div class="card sec" style="padding:16px 20px">
      <div class="tiny" style="line-height:1.8">
        <b style="font-size:13.5px;color:var(--t1)">${esc(cur.name)}</b>
        ${cur.date ? ' · ' + esc(cur.date) : ''}
        ${cur.source ? '<br>来源：' + esc(cur.source) : ''}
        ${cur.note ? '<br>备注：' + esc(cur.note) : ''}
        <br>共 ${cur.records.length} 条记录${evs.length ? '，项目：' + evs.map(esc).join(' / ') : ''}
        ${!cur.builtin ? ' <span class="tagbadge green">队长新增</span>' : ''}
        ${MODE === 'captain' ? ' · <a href="#" data-go="manage" data-msec="comp">添加/修改这场比赛</a>' : ''}
      </div>
    </div>

    <div class="toolbar">
      <div class="chips">
        <div class="chip ${state.pbSex === '' ? 'active' : ''}" data-sex="">全部</div>
        ${Array.from(new Set(cur.records.map(r => r.sex).filter(Boolean))).map(s =>
          `<div class="chip ${state.pbSex === s ? 'active' : ''}" data-sex="${esc(s)}">${esc(s)}</div>`).join('')}
      </div>
      <input type="search" id="boardQ" placeholder="搜姓名 / 学院" value="${esc(state.pbQ)}">
      <span class="tiny">共 ${rows.length} 条</span>
    </div>

    <div class="tbl-wrap">
      <table class="tbl">
        <thead><tr><th class="no-sort">名次</th><th class="no-sort">姓名</th>
          <th class="no-sort hide-sm">性别</th>
          ${evs.length > 1 ? '<th class="no-sort">项目</th>' : ''}
          <th class="no-sort">成绩</th><th class="no-sort">配速</th>
          <th class="no-sort hide-sm">学院</th><th class="no-sort hide-sm">备注</th></tr></thead>
        <tbody>
        ${rows.length ? rows.map(r => `
          <tr>
            <td class="rank ${MEDAL[r._rk] ? 'top' + r._rk : ''}">${r._rk}</td>
            <td><b>${esc(r.name)}</b></td>
            <td class="sex-b hide-sm">${esc(r.sex || '')}</td>
            ${evs.length > 1 ? `<td class="tiny">${esc(r.event || '')}</td>` : ''}
            <td class="tm">${esc(r.fmt || fmtSec(r.sec))}</td>
            <td class="pace">${esc(fmtPace(r.sec, r.event))}</td>
            <td class="tiny hide-sm">${esc(r.college || '')}</td>
            <td class="tiny hide-sm">${esc(r.note || '')}</td>
          </tr>`).join('') : '<tr><td colspan="8" class="empty">这场比赛还没有成绩</td></tr>'}
        </tbody>
      </table>
    </div>`;
  }

  /* ---------- 个人最好成绩 ---------- */
  const all = personalBests();
  const evs = Array.from(new Set(all.map(r => r.event))).sort((a, b) => distM(b) - distM(a));
  const sexes = Array.from(new Set(all.map(r => r.sex).filter(Boolean)));

  let rows = all.slice();
  if (state.pbEvent) rows = rows.filter(r => r.event === state.pbEvent);
  if (state.pbSex)   rows = rows.filter(r => r.sex === state.pbSex);
  if (state.pbQ) {
    const q = state.pbQ.toLowerCase();
    rows = rows.filter(r => (r.name || '').toLowerCase().includes(q)
                         || (r.college || '').toLowerCase().includes(q)
                         || (r.event || '').toLowerCase().includes(q));
  }

  const sk = state.pbSort;
  if (sk) {
    const dir = sk.dir === 'desc' ? -1 : 1;
    rows.sort((a, b) => {
      const x = a[sk.key], y = b[sk.key];
      if (typeof x === 'string' || typeof y === 'string') return String(x || '').localeCompare(String(y || ''), 'zh') * dir;
      return ((x || 0) - (y || 0)) * dir;
    });
  } else {
    rows.sort((a, b) => distM(b.event) - distM(a.event) || String(a.event).localeCompare(String(b.event), 'zh') || a.sec - b.sec);
  }

  const rk = {};
  rows.forEach(r => { rk[r.event] = (rk[r.event] || 0) + 1; r._rk = rk[r.event]; });

  const th = (key, label, cls) => {
    const on = state.pbSort && state.pbSort.key === key;
    return `<th class="${cls || ''}" data-sort="${key}">${label}${on ? (state.pbSort.dir === 'desc' ? ' ↓' : ' ↑') : ''}</th>`;
  };

  return head + chipsRow + `
  <p class="sub sec">上面按「一场比赛一张榜」看原始名次；下面这一张是把所有比赛合起来，每个人每个项目只留最快的一次。</p>

  <div class="toolbar">
    <div class="chips">
      <div class="chip ${state.pbEvent === '' ? 'active' : ''}" data-ev="">全部项目</div>
      ${evs.map(e => `<div class="chip ${state.pbEvent === e ? 'active' : ''}" data-ev="${esc(e)}">${esc(e)}
        <span class="n">${all.filter(r => r.event === e).length}</span></div>`).join('')}
    </div>
    <div class="chips">
      <div class="chip ${state.pbSex === '' ? 'active' : ''}" data-sex="">全部</div>
      ${sexes.map(s => `<div class="chip ${state.pbSex === s ? 'active' : ''}" data-sex="${esc(s)}">${esc(s)}</div>`).join('')}
    </div>
    <input type="search" id="boardQ" placeholder="搜姓名 / 学院" value="${esc(state.pbQ)}">
    <span class="tiny">共 ${rows.length} 条</span>
  </div>

  <div class="tbl-wrap">
    <table class="tbl tbl-board">
      <thead><tr>
        ${th('sec', '#')}
        ${th('name', '姓名')}
        <th class="no-sort hide-sm">性别</th>
        <th class="no-sort">项目</th>
        ${th('sec', '最好成绩')}
        <th class="no-sort">配速</th>
        <th class="no-sort hide-sm">学院</th>
        <th class="no-sort hide-sm">成绩来源</th>
      </tr></thead>
      <tbody>
      ${rows.length ? (function () {
        let last = null;
        const showGrp = !state.pbSort && state.pbEvent === '';
        return rows.map(r => {
          let grp = '';
          if (showGrp && r.event !== last) { last = r.event; grp = `<tr class="grp"><td colspan="8">${esc(r.event)}</td></tr>`; }
          return grp + `
        <tr>
          <td class="rank ${MEDAL[r._rk] ? 'top' + r._rk : ''}">${r._rk}</td>
          <td><b>${esc(r.name)}</b>${r.local ? ' <span class="tagbadge local">本机</span>' : ''}${r.published ? ' <span class="tagbadge green">队伍</span>' : ''}</td>
          <td class="sex-b hide-sm">${esc(r.sex || '')}</td>
          <td class="tiny">${esc(r.event)}</td>
          <td class="tm">${esc(r.fmt || fmtSec(r.sec))}</td>
          <td class="pace">${esc(fmtPace(r.sec, r.event))}</td>
          <td class="tiny hide-sm">${esc(r.college || '')}</td>
          <td class="tiny hide-sm">${esc(r.src || '')}</td>
        </tr>`;
        }).join('');
      })() : '<tr><td colspan="8" class="empty">没有符合条件的记录</td></tr>'}
      </tbody>
    </table>
  </div>

  <div class="tiny" style="margin-top:10px;line-height:1.9">
    点表头「最好成绩」可以按时间排序；配速按项目距离折算（半马 21.0975km / 全马 42.195km）。
    ${MODE !== 'view' && myResults().length ? '<br><b>带「本机」标记的是你自己录的成绩</b>，只存在这台设备上；要进全队榜单，请提交给队长。' : ''}
  </div>`;
}

/* ---------------------------------------------------------- 渲染：队员名册 */

function renderRoster() {
  let list = rosterList();
  const colleges = Array.from(new Set(list.map(m => m.college).filter(Boolean))).sort();
  const LEVELS = [['', '全部'], ['正式', '正式队员'], ['预备', '预备队员']];

  if (state.rosterLevel) list = list.filter(m => (m.level || []).includes(state.rosterLevel));
  if (state.rosterCollege) list = list.filter(m => m.college === state.rosterCollege);
  if (state.rosterQ) {
    const q = state.rosterQ.toLowerCase();
    list = list.filter(m => m.name.toLowerCase().includes(q) || (m.college || '').toLowerCase().includes(q)
                         || (m.major || '').toLowerCase().includes(q));
  }

  return `
  <div class="sec-head"><h1>队员名册</h1>
    <span class="tiny">正式队员 ${rosterList().filter(m => m.level.includes('正式')).length} 人 ·
      预备队员 ${rosterList().filter(m => m.level.includes('预备')).length} 人 · 当前筛选 ${list.length} 人</span></div>

  <div class="toolbar">
    <div class="chips">
      ${LEVELS.map(([v, l]) => `<div class="chip ${state.rosterLevel === v ? 'active' : ''}" data-lvl="${esc(v)}">${esc(l)}
        <span class="n">${v ? rosterList().filter(m => m.level.includes(v)).length : rosterList().length}</span></div>`).join('')}
    </div>
    <select id="rosterCollege" class="sel">
      <option value="">全部学院</option>
      ${colleges.map(c => `<option value="${esc(c)}" ${state.rosterCollege === c ? 'selected' : ''}>${esc(c)}</option>`).join('')}
    </select>
    <input type="search" id="rosterQ" placeholder="搜姓名 / 学院 / 专业" value="${esc(state.rosterQ)}">
  </div>

  <div class="grid-cards">
    ${list.length ? list.map(m => {
      const b = memberBests(m.name);
      const items = Object.entries(b).slice(0, 2);
      return `
      <div class="pcard">
        <div class="nm">${esc(m.name)}</div>
        <div class="meta">${m.grade ? esc(m.grade) + ' 级 · ' : ''}${esc(m.college || '')}${m.major ? ' · ' + esc(m.major) : ''}</div>
        <div style="margin-top:8px">
          ${(m.level || []).map(l => `<span class="tagbadge wheat">${esc(l)}</span>`).join('')}
          ${m.sex ? `<span class="tagbadge">${esc(m.sex)}</span>` : ''}
        </div>
        ${items.length ? `<div class="pb">${items.map(([ev, v]) =>
            `<div><span class="muted">${esc(ev)}</span><b>${esc(v.fmt)}</b></div>`).join('')}</div>`
          : `<div class="pb"><div class="muted">暂无测速成绩</div></div>`}
      </div>`;
    }).join('') : '<div class="empty">没有匹配的队员</div>'}
  </div>`;
}

/* ------------------------------------------------------- 渲染：上传成绩 */

function renderUpload() {
  const L = myResults().sort((a, b) => (b.date || '').localeCompare(a.date || ''));
  const batch = MODE === 'captain';

  return `
  <div class="sec-head"><h1>上传成绩</h1>
    <button class="btn ghost sm" data-go="board">看成绩榜 →</button></div>

  <div class="card sec">
    <h2>① 录入一条成绩</h2>
    <div class="tiny" style="margin-bottom:8px">先点一下是什么项目（半马 / 全马 也可以）：</div>
    <div class="chips" style="margin-bottom:16px">
      ${['5000米', '3000米', '10000米', '半马', '全马', '其他'].map((t, i) =>
        `<div class="chip ${i === 0 ? 'active' : ''}" data-ty="${esc(t)}">${esc(t)}</div>`).join('')}
    </div>
    <div class="grid2" style="margin-bottom:14px">
      <div class="field"><label>姓名 *</label><input id="f_name" placeholder="例如 张津浩" list="nameList">
        <datalist id="nameList">${rosterList().map(m => `<option value="${esc(m.name)}">`).join('')}</datalist>
      </div>
      <div class="field"><label>项目 / 距离 *</label><input id="f_event" placeholder="5000米 / 半马 / 全马" list="evList" value="5000米">
        <datalist id="evList">${['1500米', '3000米', '5000米', '10000米', '4公里', '12公里', '16公里', '半马', '全马']
          .map(e => `<option value="${e}">`).join('')}</datalist>
      </div>
      <div class="field"><label>成绩 * （净计时；分:秒 或 时:分:秒）</label><input id="f_result" placeholder="18:35 / 1:23:22"></div>
      <div class="field"><label>日期</label><input id="f_date" value="${todayStr()}"></div>
      <div class="field"><label>性别</label><select id="f_sex"><option value="">未填</option><option>男</option><option>女</option></select></div>
      <div class="field"><label>学院</label><input id="f_college" placeholder="例如 林学院"></div>
      <div class="field"><label>名次（可选）</label><input id="f_rank" placeholder="例如 大学生组第 5"></div>
      <div class="field"><label>赛事名称 / 备注</label><input id="f_meet" placeholder="例如 2026 杨凌马拉松"></div>
    </div>
    <button class="btn" id="btnAdd">添加到我的成绩</button>
    <span class="tiny" style="margin-left:10px">18:35、1:23:22、18'35"、18.5（分钟）都能认</span>
  </div>

  ${batch ? `
  <div class="card sec">
    <h2>② 批量导入 Excel / CSV（队长）</h2>
    <div class="drop" id="drop">
      <div class="big">📄</div>
      <div><b>把表格拖到这里</b>，或 <span style="color:var(--wheat);font-weight:700">点击选择文件</span></div>
      <div class="tiny" style="margin-top:8px">手机上点这里会打开文件选择器，选微信里收到的成绩表也能用<br>
        支持 .xlsx / .xls / .csv</div>
      <input type="file" id="fileInput" accept=".xlsx,.xls,.csv" style="display:none">
    </div>
    <div id="importArea"></div>
  </div>` : ''}

  <div class="card sec">
    <div class="sec-head"><h2>${batch ? '③' : '②'} 我录入的成绩</h2>
      <div class="chips">
        <button class="btn ghost sm" id="btnCopy" ${L.length ? '' : 'disabled'}>复制成文本</button>
        <button class="btn ghost sm" id="btnCsv" ${L.length ? '' : 'disabled'}>导出 CSV</button>
        <button class="btn danger sm" id="btnClear" ${L.length ? '' : 'disabled'}>清空</button>
      </div>
    </div>
    ${L.length ? `
    <div class="tbl-wrap">
      <table class="tbl" style="min-width:auto">
        <thead><tr><th class="no-sort">姓名</th><th class="no-sort">项目</th><th class="no-sort">成绩</th>
          <th class="no-sort hide-sm">日期</th><th class="no-sort hide-sm">赛事 / 备注</th><th class="no-sort"></th></tr></thead>
        <tbody>${L.map(r => `
          <tr><td><b>${esc(r.name)}</b>${r.submitted ? ' <span class="tagbadge green">已提交</span>' : ''}</td>
            <td class="tiny">${esc(r.event)}</td>
            <td class="tm">${esc(r.fmt || fmtSec(r.sec))}</td><td class="tiny hide-sm">${esc(r.date || '')}</td>
            <td class="tiny hide-sm">${esc(r.meet || '')}${r.rank ? ' · ' + esc(r.rank) : ''}</td>
            <td><button class="btn flat sm" data-del="${esc(r.uid)}">删除</button></td></tr>`).join('')}
        </tbody>
      </table>
    </div>` : '<div class="empty">还没有录入成绩</div>'}

    ${batch && L.length ? `
    <div class="notice" style="margin-top:16px;border-color:var(--wheat)">
      <b>本机有 ${L.length} 条成绩还没上线。</b><br>
      点下面的按钮就发布 + 同步到线上（约 1 分钟），全队立刻能看到。<br>
      想做成「某场比赛一张榜」，也可以去 <b>数据管理 → 比赛成绩</b> 把它们并进那场比赛。
    </div>
    <div class="chips" style="margin-top:12px">
      <button class="btn" id="btnPublishSync">发布并同步到线上（${L.length} 条）</button>
      <button class="btn ghost" data-go="manage" data-msec="comp">改成并进某场比赛 →</button>
    </div>` : ''}

    <div class="notice" style="margin-top:16px">
      ${batch ? '成绩先存在<b>本机</b>；点上面的「发布并同步到线上」，全队才能看到。'
              : '这里的成绩只保存在<b>你这台设备的浏览器</b>里，别人看不到自己手机上的这一份。'}
    </div>
  </div>

  ${batch ? '' : `
  <div class="card sec">
    <h2>③ 提交给全队（不用经过队长）</h2>
    ${QUEUE_CFG && QUEUE_CFG.token ? `
      <div class="tiny" style="line-height:1.9;margin-bottom:14px">
        点下面的按钮，把还没提交的成绩送到队里的收集仓库，<b>几分钟后自动进全队成绩榜</b>，
        不用等队长操作。已经提交过的会标上「已提交」。
      </div>
      <button class="btn" id="btnSubmitAll" ${L.filter(r => !r.submitted).length ? '' : 'disabled'}>
        提交 ${L.filter(r => !r.submitted).length} 条给全队
      </button>
      <span class="tiny" style="margin-left:10px">提交后可以随时在队长版的「比赛成绩」里被删掉</span>` : `
      <div class="notice">还没开通「队员直传」。让队长在<b>队长版 → 数据管理 → 队员直传</b>里开通，
        之后你就能一键把成绩送上全队榜。</div>`}
  </div>`}`;
}

/* ------------------------------------------------- 渲染：数据管理（队长版） */

function renderManage() {
  const o = ov();
  const info = teamInfo();
  const ros = BASE.roster || [];
  const hiddenSet = new Set(o.hidden);
  const editList = ros.filter(m => !hiddenSet.has(m.name)).filter(m => state.mRosterQ
    ? m.name.includes(state.mRosterQ) : (m.level || []).some(l => l === '正式' || l === '预备')).slice(0, 60);
  const removed = ros.filter(m => hiddenSet.has(m.name));
  const added = o.results;
  const cfg = ghCfg();
  const pend = pendingCount();

  const SEC = [['sync', '同步'], ['comp', '比赛成绩'], ['team', '队伍信息'],
               ['honors', '荣誉'], ['hall', '优秀队员'], ['member', '队员名册'], ['photos', '照片'],
               ['results', '自由成绩']];
  const comps = competitions();
  const curComp = comps.find(c => c.id === state.mComp) || comps[0];

  return `
  <div class="sec-head"><h1>数据管理</h1>
    <span class="tiny">${pend ? `<b style="color:var(--wheat)">有 ${pend} 处修改还没同步到线上</b>` : '本机修改已同步'}</span></div>

  <div class="chips sec">
    ${SEC.map(([k, l]) => `<div class="chip ${state.manageSec === k ? 'active' : ''}" data-msec="${k}">${esc(l)}</div>`).join('')}
  </div>

  ${state.manageSec === 'sync' ? `
  <div class="card sec">
    <h2>同步到线上</h2>
    <div class="tiny" style="line-height:2">
      当前状态：${SYNC_STATE === 'cloud' ? '✅ 已连上线上数据，改动可以同步'
        : SYNC_STATE === 'local' ? (cfg.token ? '✅ 已配好令牌，可以同步（线上还没有数据文件，你第一次点同步时会自动创建）'
                                              : '⚠️ 还没配令牌，先按下面填好')
        : '⚠️ 读取线上数据失败（离线或网络问题），本机修改仍然可用'}
       <br>线上仓库：<b>${esc(cfg.owner)} / ${esc(cfg.repo)}</b>（分支 ${esc(cfg.branch)}）
       <br>访问令牌：${cfg.token ? '<b style="color:var(--field)">✅ 已填写</b>' : '<b style="color:#c0392b">⚠️ 还没填，同步不了</b>'}
      <br>你的修改会提交到这个仓库，GitHub Pages 会自动重新发布（约 1 分钟）。
    </div>
    ${(!pend && myResults().length) ? `
    <div class="notice" style="border-color:var(--wheat);margin-top:12px;line-height:2">
      ⚠️ 你还有 <b>${myResults().length}</b> 条在「上传成绩」里导入/录入的成绩，只是存在本机、<b>还没发布</b>，
      所以同步按钮是灰的。<br>
      <button class="btn sm" id="btnPubSync2" style="margin-top:8px">发布这 ${myResults().length} 条并同步到线上</button>
    </div>` : ''}
    <div class="grid2" style="margin:16px 0">
      <div class="field"><label>GitHub 用户名</label><input data-cfg="owner" value="${esc(cfg.owner || 'zl4639574-bit')}" placeholder="zl4639574-bit"></div>
      <div class="field"><label>仓库名</label><input data-cfg="repo" value="${esc(cfg.repo || 'maitian-running')}" placeholder="maitian-running"></div>
      <div class="field"><label>分支</label><input data-cfg="branch" value="${esc(cfg.branch || 'master')}" placeholder="master"></div>
      <div class="field"><label>访问令牌（只存在本机浏览器里）</label><input data-cfg="token" type="password" value="${esc(cfg.token)}" placeholder="github_pat_..."></div>
    </div>
    <div class="chips">
      <button class="btn" id="btnSaveCfg">保存设置</button>
      <button class="btn ghost" id="btnPull">从线上拉取</button>
      <button class="btn ghost" id="btnPush" ${pend ? '' : 'disabled'}>同步我的修改到线上</button>
      <button class="btn danger" id="btnResetLocal">丢弃本机修改</button>
      <button class="btn ghost" id="btnTest">测试同步（不改数据）</button>
    </div>

    <div class="notice" style="margin-top:16px;line-height:2">
      <b>第一次用，照着做三步（以后就不用管了）：</b><br>
      <b>①</b> <button class="btn sm" id="btnMakeToken" style="margin:4px 6px 4px 0">一键打开建令牌页面（权限已勾好）</button><br>
      　　打开的页面里：有效期选 <b>No expiration</b>（永久），点最下面 <b>Generate token</b>，复制那串 <code>ghp_...</code><br>
      <b>②</b> 把 <code>ghp_...</code> 粘到上面「访问令牌」框 → 点「<b>保存设置</b>」<br>
      <b>③</b> <button class="btn sm" id="btnPhoneLink" style="margin:4px 6px 4px 0">生成我的专用链接</button>
      　→ 复制那条链接，<b>存到手机书签</b>（或微信发给自己）<br>
      <span class="tiny">以后：手机上点书签打开 → 改数据 → 点「同步我的修改到线上」→ 1 分钟上线。
      <b>不用再碰令牌、也不用 VPN</b>。<br>
      换届：把这条链接直接给下一任队长，他打开就能改、能同步，不用建账号、不用弄令牌。
      （链接等于管理钥匙，存好、别发群里；想作废就在 GitHub 删掉令牌重新生成一条）</span>
    </div>
    <div id="phoneBox" style="margin-top:12px"></div>
    <div class="notice" style="margin-top:16px;line-height:1.9">
      <span class="tiny">不想用一键按钮的话，手工也能建：GitHub → 头像 → Settings → Developer settings →
      Personal access tokens → <b>Tokens (classic)</b> → Generate new token (classic) → 勾上 <b>repo</b> →
      生成后复制 <code>ghp_...</code> 粘到上面的「访问令牌」。<br>
      令牌只保存在这台设备的浏览器里，不会写进网页、也不会提交进仓库，我看不到。</span>
    </div>
  </div>` : ''}

  ${state.manageSec === 'comp' ? `
  <div class="card sec">
    <div class="sec-head"><h2>比赛成绩（谁都能看，只有队长能改）</h2></div>
    <div class="tiny" style="margin-bottom:14px">
      每一场比赛 / 每次测速就是一张成绩榜。原始资料里已有的比赛已经在这里；新比赛可以自己建，
      成绩可以一条条录，也可以在「上传成绩」里批量导入后并进来。
    </div>
    <div class="grid2" style="margin-bottom:16px">
      <div class="field"><label>选择要操作的比赛</label>
        <select id="compSel">${comps.map(c => `<option value="${esc(c.id)}" ${curComp && c.id === curComp.id ? 'selected' : ''}>${esc(c.name)}${c.builtin ? '' : ' · 新增'}</option>`).join('')}</select></div>
      <div class="field"><label>&nbsp;</label>
        <div class="chips">
          <button class="btn ghost sm" id="btnDelCompRecords">删除这场比赛里某条成绩…</button>
          ${curComp && !curComp.builtin ? '<button class="btn danger sm" id="btnDelComp">删除这场比赛</button>' : ''}
        </div>
      </div>
    </div>

    <h3>新建一场比赛</h3>
    <div class="grid3" style="margin-bottom:12px">
      <div class="field"><label>比赛名称 *</label><input id="c_name" placeholder="例如 2026 杨凌马拉松"></div>
      <div class="field"><label>日期</label><input id="c_date" placeholder="2026.04.12"></div>
      <div class="field"><label>主要项目</label><input id="c_event" placeholder="半马 / 全马 / 5000米"></div>
    </div>
    <div class="field" style="margin-bottom:12px"><label>备注</label><input id="c_note" placeholder="例如 大学生组；天气 12℃"></div>
    <button class="btn" id="btnAddComp">新建这场比赛</button>

    ${curComp ? `
    <hr style="border:0;border-top:1px solid var(--line);margin:24px 0">
    <h3>往「${esc(curComp.name)}」里录一条成绩</h3>
    <div class="grid3" style="margin-bottom:12px">
      <div class="field"><label>姓名 *</label><input id="cr_name"></div>
      <div class="field"><label>项目</label><input id="cr_event" value="${esc(curComp.event || '')}" placeholder="5000米"></div>
      <div class="field"><label>成绩 *</label><input id="cr_res" placeholder="18:35 / 1:23:22"></div>
      <div class="field"><label>性别</label><select id="cr_sex"><option value="">未填</option><option>男</option><option>女</option></select></div>
      <div class="field"><label>学院</label><input id="cr_college"></div>
      <div class="field"><label>备注 / 名次</label><input id="cr_note"></div>
    </div>
    <div class="chips">
      <button class="btn" id="btnAddCompRec">加入这场比赛的榜单</button>
      <button class="btn ghost" id="btnMergeMine" ${myResults().length ? '' : 'disabled'}>把「上传成绩」里的 ${myResults().length} 条并入</button>
    </div>

    <div style="margin-top:22px">
      <h3>当前榜单（${curComp.records.length} 条）</h3>
      <div class="tbl-wrap">
        <table class="tbl" style="min-width:auto">
          <thead><tr><th class="no-sort">姓名</th><th class="no-sort">项目</th><th class="no-sort">成绩</th>
            <th class="no-sort hide-sm">学院</th><th class="no-sort"></th></tr></thead>
          <tbody>${curComp.records.slice(0, 60).map(r => `
            <tr><td><b>${esc(r.name)}</b></td><td class="tiny">${esc(r.event || '')}</td>
              <td class="tm">${esc(r.fmt || fmtSec(r.sec))}</td>
              <td class="tiny hide-sm">${esc(r.college || '')}</td>
              <td><button class="btn danger sm" data-recdel="${esc(curComp.id)}|${esc(r.name)}|${r.sec}">删</button></td></tr>`).join('')
            || '<tr><td colspan="5" class="empty">还没有成绩</td></tr>'}
          </tbody>
        </table>
      </div>
      ${curComp.records.length > 60 ? '<div class="tiny" style="margin-top:8px">只显示前 60 条，删除操作仍然有效。</div>' : ''}
    </div>` : ''}
  </div>` : ''}

  ${state.manageSec === 'hall' ? `
  <div class="card sec">
    <div class="sec-head"><h2>优秀队员 · 个人最好成绩</h2>
      <button class="btn ghost sm" id="btnAddHall">＋ 加一位</button></div>
    <div class="tiny" style="margin-bottom:14px">
      这里的内容会显示在「荣誉与资料」页。默认是空的（不显示那个板块），想放谁就加谁。
      成绩一行一条，例如 <code>全马 2:48:33</code>。
    </div>
    ${(ov().hall || []).map((a, i) => `
      <div class="hallrow">
        <div class="mrow-f" style="margin-bottom:8px">
          <input data-hall="${i}" data-hf="name" value="${esc(a.name || '')}" placeholder="姓名" class="w100">
          <input data-hall="${i}" data-hf="sex" value="${esc(a.sex || '')}" placeholder="性别" class="w60">
          <input data-hall="${i}" data-hf="note" value="${esc(a.note || '')}" placeholder="一句话介绍（可空）">
          <button class="btn danger sm" data-halldel="${i}">删</button>
        </div>
        <textarea class="ta" rows="3" data-hall="${i}" data-hf="items"
          placeholder="全马 2:48:33&#10;半马 1:19:58">${esc((a.items || []).join('\n'))}</textarea>
      </div>`).join('') || '<div class="empty">还没有内容（荣誉与资料页就不会显示这个板块）</div>'}
    <button class="btn" id="btnSaveHall" style="margin-top:16px">保存</button>
  </div>` : ''}

  ${state.manageSec === 'team' ? `
  <div class="card sec">
    <h2>队伍信息</h2>
    <div class="grid2" style="margin-bottom:14px">
      <div class="field"><label>队名</label><input data-team="name" value="${esc(info.name)}"></div>
      <div class="field"><label>副标题</label><input data-team="alias" value="${esc(info.alias || '')}"></div>
      <div class="field"><label>口号</label><input data-team="slogan" value="${esc(info.slogan || '')}"></div>
      <div class="field"><label>成立日期</label><input data-team="founded" value="${esc(info.founded || '')}"></div>
    </div>
    <div class="field" style="margin-bottom:14px"><label>简介</label>
      <textarea data-team="intro" rows="4" class="ta">${esc(info.intro || '')}</textarea></div>
    <div class="field" style="margin-bottom:14px"><label>官方媒体（每行一个，格式：平台·账号）</label>
      <textarea data-team="media" rows="3" class="ta">${esc((info.media || []).map(m => m[0] + '·' + m[1]).join('\n'))}</textarea></div>
    <div class="field" style="margin-bottom:14px"><label>队伍活动（每行一条）</label>
      <textarea data-team="activities" rows="4" class="ta">${esc((info.activities || []).join('\n'))}</textarea></div>
    <button class="btn" id="btnSaveTeam">保存队伍信息</button>
  </div>` : ''}

  ${state.manageSec === 'honors' ? `
  <div class="card sec">
    <div class="sec-head"><h2>历年荣誉</h2><button class="btn ghost sm" id="btnAddHonor">＋ 加一条</button></div>
    ${(info.honors || []).map((h, i) => `
      <div class="rowline">
        <input class="row-year" data-hy="${i}" value="${esc(h[0])}" placeholder="年份">
        <input class="row-text" data-ht="${i}" value="${esc(h[1])}" placeholder="战绩描述">
        <button class="btn danger sm" data-hdel="${i}">删</button>
      </div>`).join('') || '<div class="empty">还没有荣誉条目</div>'}
    <button class="btn" id="btnSaveHonors" style="margin-top:14px">保存荣誉</button>
    <div class="tiny" style="margin-top:10px">提示：点「加一条」会在最后面加一个空行，填好一起保存。</div>
  </div>` : ''}

  ${state.manageSec === 'member' ? `
  <div class="card sec">
    <div class="sec-head"><h2>队员名册管理</h2>
      <input type="search" id="mRosterQ" placeholder="搜姓名" value="${esc(state.mRosterQ)}" class="inp-inline">
    </div>
    <div class="tiny" style="margin-bottom:12px">
      名册共 ${ros.length} 人（展示版只显示标记为正式/预备的 ${rosterList().length} 人）。
      可以改学院/专业/年级/身份，或把某人从公开名册里删掉。改完记得去「同步」发布。
    </div>
    <div class="mgrid">
      ${editList.map(m => {
        const e = o.memberEdits[m.name] || {};
        return `
        <div class="mrow">
          <div class="mrow-h"><b>${esc(m.name)}</b>
            <span class="tagbadge ${(m.level || []).some(l => l === '正式' || l === '预备') ? 'wheat' : ''}">${esc((m.level || []).join('/') || '未分级')}</span>
          </div>
          <div class="mrow-f">
            <input data-me="${esc(m.name)}" data-mf="college" value="${esc(e.college != null ? e.college : (m.college || ''))}" placeholder="学院">
            <input data-me="${esc(m.name)}" data-mf="major" value="${esc(e.major != null ? e.major : (m.major || ''))}" placeholder="专业">
            <input data-me="${esc(m.name)}" data-mf="grade" value="${esc(e.grade != null ? e.grade : (m.grade || ''))}" placeholder="年级" class="w60">
            <select data-me="${esc(m.name)}" data-mf="level">
              ${[['', '未分级'], ['正式', '正式'], ['预备', '预备'], ['正式,预备', '正式+预备']].map(([v, l]) =>
                `<option value="${v}" ${(e.level ? e.level.join(',') : (m.level || []).join(',')) === v ? 'selected' : ''}>${l}</option>`).join('')}
            </select>
            <button class="btn danger sm" data-mdel="${esc(m.name)}">删除</button>
          </div>
        </div>`;
      }).join('') || '<div class="empty">没有匹配的队员</div>'}
    </div>
    <button class="btn" id="btnSaveMembers" style="margin-top:16px">保存名册修改</button>
    ${removed.length ? `
    <div style="margin-top:20px">
      <h3>已从名册移除（${removed.length} 人）</h3>
      <div class="chips">${removed.map(m => `<div class="chip" data-mrestore="${esc(m.name)}">${esc(m.name)} ↺</div>`).join('')}</div>
    </div>` : ''}
  </div>` : ''}

  ${state.manageSec === 'photos' ? `
  <div class="card sec">
    <h2>照片管理</h2>
    <div class="tiny" style="margin-bottom:14px">手机相册里的照片可以直接选，浏览器会自动压缩后再上传（长边 1500px）。</div>
    <div class="grid2" style="margin-bottom:14px">
      <div class="field"><label>放到哪个相册</label>
        <select id="albSel">${albums().map(a => `<option>${esc(a.name)}</option>`).join('')}
          <option value="__new">＋ 新建相册…</option></select></div>
      <div class="field"><label>新相册名（选「新建相册」时填）</label><input id="albNew" placeholder="例如 2026 杨凌马拉松"></div>
    </div>
    <div class="drop" id="photoDrop">
      <div class="big">🖼️</div>
      <div><b>点这里选照片</b>，或把照片拖进来</div>
      <div class="tiny" style="margin-top:6px">可一次选多张</div>
      <input type="file" id="photoInput" accept="image/*" multiple style="display:none">
    </div>
    <div id="photoPreview" style="margin-top:16px"></div>
    ${(ov().photos || []).length ? `
    <div style="margin-top:20px">
      <h3>本机新加的照片（${ov().photos.length} 张，尚未同步）</h3>
      <div class="pgrid">${ov().photos.map((p, i) => `
        <div class="pitem"><img src="${photoSrc(p)}"><div class="cap">${esc(p.album)}</div>
          <button class="btn danger sm" data-pdel="${i}" style="position:absolute;top:6px;right:6px">删</button></div>`).join('')}
      </div>
    </div>` : ''}
  </div>` : ''}

  ${state.manageSec === 'results' ? `
  <div class="card sec">
    <h2>已发布的队伍成绩</h2>
    <div class="tiny" style="margin-bottom:14px">
      这里是把导入/录入的成绩发布到线上后的样子。队员自己提交的成绩在「上传成绩」页里。
    </div>
    ${added.length ? `
    <div class="tbl-wrap">
      <table class="tbl" style="min-width:auto">
        <thead><tr><th class="no-sort">姓名</th><th class="no-sort">项目</th><th class="no-sort">成绩</th>
          <th class="no-sort hide-sm">日期</th><th class="no-sort hide-sm">赛事</th><th class="no-sort"></th></tr></thead>
        <tbody>${added.map((r, i) => `
          <tr><td><b>${esc(r.name)}</b></td><td class="tiny">${esc(r.event)}</td>
            <td class="tm">${esc(r.fmt || fmtSec(r.sec))}</td>
            <td class="tiny hide-sm">${esc(r.date || '')}</td><td class="tiny hide-sm">${esc(r.meet || '')}</td>
            <td><button class="btn danger sm" data-pubdel="${i}">删</button></td></tr>`).join('')}
        </tbody>
      </table>
    </div>
    <button class="btn" id="btnPublishMine" style="margin-top:14px">把「上传成绩」里录入的 ${myResults().length} 条发布到线上</button>`
      : '<div class="empty">还没有发布过成绩</div>'}
  </div>` : ''}`;
}

/* -------------------------------------------------------------- 照片墙 */

function renderPhotos() {
  const alb = albums();
  if (state.album) {
    const a = alb.find(x => x.name === state.album);
    if (!a) { state.album = ''; return renderPhotos(); }
    return `
    <div class="sec-head">
      <div style="display:flex;align-items:center;gap:12px">
        <button class="btn ghost sm" id="btnAlbBack">← 相册</button>
        <h1 style="font-size:22px;margin:0">${esc(a.name)}</h1>
      </div>
      <span class="tiny">${a.date ? esc(a.date) + ' · ' : ''}${a.photos.length} 张</span>
    </div>
    <div class="pgrid">
      ${a.photos.map((p, i) => `
        <div class="pitem" data-photo="${esc(a.name)}|${i}">
          <img src="${photoSrc(p)}" loading="lazy" alt="${esc(p.caption)}">
          <div class="cap">${esc(p.caption || '')}</div>
        </div>`).join('')}
    </div>
    ${lightboxHTML(a)}
    <div id="lbData" style="display:none">${esc(JSON.stringify(a.photos.map(p => ({ s: photoSrc(p), c: p.caption || '' }))))}</div>`;
  }

  return `
  <div class="sec-head"><h1>照片墙</h1>
    <span class="tiny">${alb.length} 个相册 · 共 ${alb.reduce((n, a) => n + a.photos.length, 0)} 张</span></div>
  ${MODE === 'captain' ? `<div class="chips sec"><button class="btn sm" data-go="manage" data-msec="photos">＋ 上传照片</button></div>` : ''}
  <div class="albgrid">
    ${alb.map(a => `
      <div class="alb" data-album="${esc(a.name)}">
        <img src="${photoSrc(a.photos[0])}" loading="lazy" alt="${esc(a.name)}">
        <div class="alb-m">
          <div class="n">${esc(a.name)}</div>
          <div class="c">${a.date ? esc(a.date) + ' · ' : ''}${a.photos.length} 张</div>
        </div>
      </div>`).join('')}
  </div>`;
}

function lightboxHTML(a) {
  return `
  <div class="lightbox" id="lightbox">
    <span class="lb-close" data-lb="close">×</span>
    <span class="lb-nav prev" data-lb="prev">‹</span>
    <div style="text-align:center">
      <img id="lbImg" src="" alt="">
      <div class="lb-cap" id="lbCap"></div>
    </div>
    <span class="lb-nav next" data-lb="next">›</span>
  </div>`;
}

/* -------------------------------------------------------- 渲染：荣誉与资料 */

function renderAbout() {
  const info = teamInfo();
  return `
  <h1>荣誉与资料</h1>
  <p class="sub sec">${esc(info.name || '')} · ${esc(info.alias || '')} · 成立于 ${esc(info.founded || '')}</p>

  <div class="card sec">
    <div class="sec-head"><h2>历年战绩</h2>
      ${MODE === 'captain' ? '<button class="btn ghost sm" data-go="manage" data-msec="honors">编辑 →</button>' : ''}</div>
    <div class="timeline">
      ${(info.honors || []).map(h => `
        <div class="tl-item"><div class="tl-year">${esc(h[0])}</div><div class="tl-text">${esc(h[1])}</div></div>`).join('')}
    </div>
  </div>

  ${(ov().hall || []).length ? `
  <div class="card sec">
    <div class="sec-head"><h2>优秀队员 · 个人最好成绩</h2>
      ${MODE === 'captain' ? '<button class="btn ghost sm" data-go="manage" data-msec="hall">编辑 →</button>' : ''}</div>
    <div class="grid-cards">
      ${(ov().hall || []).map(a => `
        <div class="pcard">
          <div class="nm">${esc(a.name)} ${a.sex ? `<span class="tagbadge">${esc(a.sex)}</span>` : ''}</div>
          <div class="pb">${(a.items || []).map(it => {
            const m = String(it).match(/^(.*?)\s*([\d:.']+)$/);
            return `<div><span class="muted">${esc(m ? m[1] : it)}</span><b>${esc(m ? m[2] : '')}</b></div>`;
          }).join('')}</div>
          ${a.note ? `<div class="tiny" style="margin-top:10px;line-height:1.6">${esc(a.note)}</div>` : ''}
        </div>`).join('')}
    </div>
  </div>` : ''}

  <div class="card sec">
    <div class="sec-head"><h2>队伍活动</h2>
      ${MODE === 'captain' ? '<button class="btn ghost sm" data-go="manage" data-msec="team">编辑 →</button>' : ''}</div>
    <div class="chips">${(info.activities || []).map(a => `<span class="chip" style="cursor:default">${esc(a)}</span>`).join('')}</div>
  </div>`;
}

/* ------------------------------------------------------------------ 渲染 */

function renderNav() {
  const tabs = TABS[MODE] || TABS.view;
  $('#nav').innerHTML = tabs.map(([k, l]) =>
    `<div class="nav-item ${state.tab === k ? 'active' : ''}" data-tab="${k}">${l}</div>`).join('');
}

function render() {
  if (!(TABS[MODE] || []).some(t => t[0] === state.tab)) state.tab = 'home';
  renderNav();
  const map = { home: renderHome, board: renderBoard, roster: renderRoster, upload: renderUpload,
                manage: renderManage, photos: renderPhotos, about: renderAbout };
  $('#page').innerHTML = (map[state.tab] || renderHome)()
    + `<div class="foot">${esc(teamInfo().name || '')} · 数据中心
         <br><a href="${ROOT}guide.txt" target="_blank">📖 ${MODE === 'view' ? '使用说明' : '使用说明（怎么上传 / 怎么改）'}</a>
         <br><span style="opacity:.7">数据更新于 ${esc(BASE.generated || '')}</span></div>`;
  if (state.tab === 'upload') bindUpload();
  if (state.tab === 'manage') bindManage();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function goTab(tab, extra) {
  state.tab = tab;
  if (extra && extra.msec) state.manageSec = extra.msec;
  try { if (location.hash !== '#' + tab) history.replaceState(null, '', '#' + tab); } catch (e) {}
  render();
}

/* ------------------------------------------------- 上传页交互（队员/队长） */

let pendingFile = null, importCfg = null;
const IMPORT_EVENTS = ['5000米', '3000米', '1500米', '10000米', '4公里', '12公里', '16公里', '半马', '全马', '其他'];

function bindUpload() {
  const add = $('#btnAdd');
  if (add) add.onclick = () => {
    const name = ($('#f_name').value || '').trim();
    const ev = ($('#f_event').value || '').trim();
    const raw = ($('#f_result').value || '').trim();
    if (!name) return toast('请填姓名');
    if (!ev) return toast('请填项目 / 距离');
    const sec = parseSec(raw);
    if (!sec) return toast('成绩没看懂，试试 18:35 或 1:23:22');
    addMyResults([{
      uid: newUid(), name, event: ev, raw, sec: Math.round(sec * 10) / 10, fmt: fmtSec(sec),
      sex: $('#f_sex').value, college: ($('#f_college').value || '').trim(),
      date: ($('#f_date').value || '').trim() || todayStr(),
      rank: ($('#f_rank').value || '').trim(),
      meet: ($('#f_meet').value || '').trim(), ts: Date.now(),
    }]);
    toast('已记录：' + name + ' ' + ev + ' ' + fmtSec(sec));
    render();
  };

  const drop = $('#drop'), fi = $('#fileInput');
  if (drop && fi) {
    drop.onclick = () => fi.click();
    ['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('over'); }));
    ['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove('over'); }));
    drop.addEventListener('drop', e => { if (e.dataTransfer.files[0]) readTableFile(e.dataTransfer.files[0]); });
    fi.onchange = () => { if (fi.files[0]) readTableFile(fi.files[0]); };
  }

  const cp = $('#btnCopy');
  if (cp) cp.onclick = () => {
    const txt = '麦田守望 · 成绩上报（' + todayStr() + '）\n'
      + myResults().map(r => [r.name, r.event, r.fmt || fmtSec(r.sec), r.date, r.meet || ''].join('\t')).join('\n');
    copyText(txt);
  };
  const csv = $('#btnCsv');
  if (csv) csv.onclick = () => {
    const head = ['姓名', '性别', '学院', '项目', '成绩', '成绩(秒)', '日期', '赛事/备注'];
    const lines = [head.join(',')].concat(myResults().map(r => [r.name, r.sex, r.college, r.event,
      r.fmt || fmtSec(r.sec), r.sec, r.date, r.meet].map(v => {
        const s = String(v == null ? '' : v);
        return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
      }).join(',')));
    download('麦田守望_我的成绩_' + todayStr() + '.csv', '\ufeff' + lines.join('\r\n'));
    toast('已导出 CSV');
  };
  const subm = $('#btnSubmitAll');
  if (subm) subm.onclick = submitMine;
  const clr = $('#btnClear');
  if (clr) clr.onclick = () => {
    if (confirm('确定清空本机记录的 ' + myResults().length + ' 条成绩？')) { setMyResults([]); toast('已清空'); render(); }
  };
  $$('[data-del]').forEach(b => b.onclick = () => { delMyResult(b.dataset.del); toast('已删除'); render(); });
}

/* -------- 批量导入（队长版，手机上也能用） -------- */

function readTableFile(file) {
  const r = new FileReader();
  r.onload = e => {
    try {
      const wb = XLSX.read(new Uint8Array(e.target.result), { type: 'array' });
      const names = wb.SheetNames;
      const sheets = names.map(n => XLSX.utils.sheet_to_json(wb.Sheets[n], { header: 1, raw: true, defval: '' }));
      const first = sheets[0];
      const hIdx = guessHeaderRow(first);
      pendingFile = { name: file.name, sheetNames: names, sheets };
      const cols = colOptions(first, hIdx);
      importCfg = {
        sheet: 0, header: hIdx,
        nameCol: guessCol(cols, /姓名|名字|人员|队员/),
        resCol: guessCol(cols, /成绩|用时|时间|结果|净计时/),
        sexCol: guessCol(cols, /性别/), colCol: guessCol(cols, /学院|院系|单位/),
        event: IMPORT_EVENTS[0], date: todayStr(), meet: file.name.replace(/\.[^.]+$/, ''),
      };
      if (importCfg.nameCol < 0) importCfg.nameCol = cols.length > 1 ? 1 : 0;
      if (importCfg.resCol < 0) importCfg.resCol = cols.length > 2 ? 2 : 1;
      renderImport();
      toast('已读取 ' + file.name + '，确认下面几列对不对');
    } catch (err) { toast('这个文件读不了：' + err.message); }
  };
  r.readAsArrayBuffer(file);
}

function guessHeaderRow(rows) {
  for (let i = 0; i < Math.min(rows.length, 8); i++) {
    const line = (rows[i] || []).map(c => String(c == null ? '' : c));
    if (line.some(c => /姓名|名字|队员|人员|人名/.test(c))) return i;
  }
  return 0;
}
function colOptions(rows, hIdx) {
  const width = Math.max.apply(null, rows.map(r => r.length));
  const head = rows[hIdx] || [];
  const out = [];
  for (let c = 0; c < width; c++) {
    const h = String(head[c] == null ? '' : head[c]).trim();
    out.push({ idx: c, label: h || ('第 ' + (c + 1) + ' 列') });
  }
  return out;
}
function guessCol(cols, re) { for (const c of cols) if (re.test(c.label)) return c.idx; return -1; }

function renderImport() {
  const box = $('#importArea');
  if (!box) return;
  if (!pendingFile) { box.innerHTML = ''; return; }
  const si = importCfg.sheet, rows = pendingFile.sheets[si], hIdx = importCfg.header;
  const cols = colOptions(rows, hIdx);
  const body = rows.slice(hIdx + 1).filter(r => r.some(c => c !== '' && c != null));
  const nm = importCfg.nameCol, rs = importCfg.resCol;

  const prev = body.slice(0, 6).map(r => {
    const sec = parseSec(r[rs]);
    return `<tr><td>${esc(r[nm])}</td><td>${esc(r[rs])}</td>
      <td class="tm">${sec ? esc(fmtSec(sec)) : '<span style="color:var(--red)">认不出</span>'}</td></tr>`;
  }).join('');

  const selBox = (label, key, allowNone, val) => `
    <div class="field"><label>${label}</label><select data-map="${key}">
      ${allowNone ? '<option value="-1">（不用）</option>' : ''}
      ${cols.map(c => `<option value="${c.idx}" ${c.idx === val ? 'selected' : ''}>${esc(c.label)}</option>`).join('')}
    </select></div>`;

  box.innerHTML = `
  <div style="margin-top:16px">
    <div class="tiny" style="margin-bottom:10px">已读取 <b>${esc(pendingFile.name)}</b>，${body.length} 行数据
      ${pendingFile.sheetNames.length > 1 ? '，共 ' + pendingFile.sheetNames.length + ' 个工作表' : ''}。</div>
    <div class="map-grid">
      ${pendingFile.sheetNames.length > 1 ? `<div class="field"><label>工作表</label><select data-map="sheet">
        ${pendingFile.sheetNames.map((s, i) => `<option value="${i}" ${i === si ? 'selected' : ''}>${esc(s)}</option>`).join('')}
      </select></div>` : ''}
      <div class="field"><label>表头行</label><select data-map="header">
        ${rows.slice(0, 8).map((r, i) => `<option value="${i}" ${i === hIdx ? 'selected' : ''}>第 ${i + 1} 行：${esc(String(r.slice(0, 3).map(c => c == null ? '' : c).join('|')).slice(0, 20))}</option>`).join('')}
      </select></div>
      ${selBox('姓名列', 'nameCol', false, nm)}
      ${selBox('成绩列', 'resCol', false, rs)}
      ${selBox('性别列', 'sexCol', true, importCfg.sexCol)}
      ${selBox('学院列', 'colCol', true, importCfg.colCol)}
      <div class="field"><label>项目 / 距离</label><select data-map="event">
        ${IMPORT_EVENTS.map(e => `<option ${e === importCfg.event ? 'selected' : ''}>${esc(e)}</option>`).join('')}
      </select></div>
      <div class="field"><label>日期</label><input data-map="date" value="${esc(importCfg.date)}"></div>
      <div class="field"><label>赛事 / 备注</label><input data-map="meet" value="${esc(importCfg.meet)}"></div>
    </div>
    <div class="preview"><table class="tbl" style="min-width:auto">
      <thead><tr><th class="no-sort">姓名</th><th class="no-sort">原始成绩</th><th class="no-sort">识别为</th></tr></thead>
      <tbody>${prev || '<tr><td colspan="3" class="empty">没有可预览的数据</td></tr>'}</tbody>
    </table></div>
    <div style="margin-top:16px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
      <button class="btn" id="btnDoImport">导入这 ${body.length} 行</button>
      <button class="btn flat sm" id="btnCancelImport">取消</button>
    </div>
  </div>`;

  $$('[data-map]', box).forEach(el => {
    el.onchange = () => {
      const k = el.dataset.map, v = el.value;
      if (k === 'sheet') importCfg.sheet = +v;
      else if (k === 'header') {
        importCfg.header = +v;
        const c2 = colOptions(pendingFile.sheets[importCfg.sheet], importCfg.header);
        importCfg.nameCol = guessCol(c2, /姓名|名字|人员|队员/);
        importCfg.resCol = guessCol(c2, /成绩|用时|时间|结果|净计时/);
        importCfg.sexCol = guessCol(c2, /性别/);
        importCfg.colCol = guessCol(c2, /学院|院系|单位/);
      } else if (['nameCol', 'resCol', 'sexCol', 'colCol'].includes(k)) importCfg[k] = +v;
      else importCfg[k] = v;
      renderImport();
    };
  });
  $('#btnDoImport').onclick = doImport;
  $('#btnCancelImport').onclick = () => { pendingFile = null; box.innerHTML = ''; };
}

function doImport() {
  const rows = pendingFile.sheets[importCfg.sheet];
  const body = rows.slice(importCfg.header + 1).filter(r => r.some(c => c !== '' && c != null));
  const out = [];
  let bad = 0, noName = 0;
  body.forEach(r => {
    const name = String(r[importCfg.nameCol] == null ? '' : r[importCfg.nameCol]).trim().replace(/\s/g, '');
    if (!/^[\u4e00-\u9fa5·]{2,5}$/.test(name)) { noName++; return; }
    const raw = r[importCfg.resCol];
    const sec = parseSec(raw);
    if (!sec) { bad++; return; }
    let ev = importCfg.event;
    const m = String(raw == null ? '' : raw).match(/[（(]\s*(\d+)\s*k/i);
    if (m) ev = (parseInt(m[1], 10) * 1000) + '米';
    out.push({
      uid: newUid(), name, event: ev, raw: String(raw == null ? '' : raw),
      sec: Math.round(sec * 10) / 10, fmt: fmtSec(sec),
      sex: importCfg.sexCol >= 0 ? String(r[importCfg.sexCol] || '') : '',
      college: importCfg.colCol >= 0 ? String(r[importCfg.colCol] || '') : '',
      date: importCfg.date, meet: importCfg.meet, ts: Date.now(),
    });
  });
  if (!out.length) return toast('一条都没导入成功，检查一下列对应关系');
  addMyResults(out);
  pendingFile = null;
  toast('已导入 ' + out.length + ' 条' + (bad ? '，跳过 ' + bad + ' 条成绩认不出的' : '')
        + (noName ? '，跳过 ' + noName + ' 条没姓名的' : '')
        + (MODE === 'captain' ? '；点下面「发布并同步到线上」全队才能看到' : ''), 7000);
  state.tab = MODE === 'captain' ? 'upload' : 'board';   // 队长留在本页，才能看到发布按钮
  render();
}

/* --------------------------------------------- 数据管理交互（队长版） */

function ovLocal() { return LOCAL_OV || (LOCAL_OV = {}); }

/** 把「上传成绩」里录入/导入的成绩，转成「待同步到线上」的正式成绩（清空本机草稿） */
function publishMine() {
  const mine = myResults();
  if (!mine.length) return 0;
  const l = ovLocal();
  l.results = (l.results || []).concat(mine.map(r => Object.assign({}, r, { local: false, published: true })));
  saveLocalOv();
  setMyResults([]);
  return mine.length;
}

/** 一键：发布本机录入的成绩 → 直接同步到线上（没配令牌则只发布，并提示去配） */
async function publishAndSync() {
  const n = publishMine();
  render();
  if (!n) return toast('本机没有新录入的成绩');
  const cfg = ghCfg();
  if (!cfg.token) return toast('已把 ' + n + ' 条标成待上线，但还没配「访问令牌」→ 数据管理 → 同步 里填一次即可', 10000);
  toast('已发布 ' + n + ' 条，正在同步到线上…（约 1 分钟）', 6000);
  await pushToGitHub();
}
function addCompRecords(compId, recs) {
  const l = ovLocal();
  l.compRecords = l.compRecords || {};
  l.compRecords[compId] = (l.compRecords[compId] || []).concat(recs);
  saveLocalOv();
  return l;
}
function pendingCount() {
  const l = LOCAL_OV || {};
  let n = 0;
  if (l.team && Object.keys(l.team).length) n += Object.keys(l.team).length;
  if (l.honors) n += 1;
  if (l.activities) n += 1;
  if (l.hidden && l.hidden.length) n += l.hidden.length;
  if (l.memberEdits) n += Object.keys(l.memberEdits).length;
  if (l.results && l.results.length) n += l.results.length;
  if (l.photos && l.photos.length) n += l.photos.length;
  if (l.competitions && l.competitions.length) n += l.competitions.length;
  if (l.compRecords) n += Object.keys(l.compRecords).reduce((a, k) => a + l.compRecords[k].length, 0);
  if (l.hiddenRecords && l.hiddenRecords.length) n += l.hiddenRecords.length;
  if (l.hall) n += 1;
  if (l.queue) n += 1;
  return n;
}
function saveLocalOv() {
  LOCAL_OV = LOCAL_OV || {};
  lsSet(LS_LOCAL, LOCAL_OV);
}

const GH_DEF = { owner: 'zl4639574-bit', repo: 'maitian-running', branch: 'master' };
/** 读同步配置：没填的用默认值补齐，避免"未填写"卡住 */
function ghCfg() {
  const c = lsGet(LS_CFG, {}) || {};
  return { owner: c.owner || GH_DEF.owner, repo: c.repo || GH_DEF.repo,
           branch: c.branch || GH_DEF.branch, token: c.token || '' };
}

function bindManage() {
  const cfg = ghCfg();
  $$('[data-cfg]').forEach(el => el.onchange = () => {
    cfg[el.dataset.cfg] = el.value.trim();
    lsSet(LS_CFG, cfg);
  });
  const s1 = $('#btnSaveCfg');
  if (s1) s1.onclick = () => {          // 直接读输入框，不依赖有没有触发过 onchange
    $$('[data-cfg]').forEach(el => { cfg[el.dataset.cfg] = (el.value || '').trim(); });
    lsSet(LS_CFG, cfg);
    toast(cfg.token ? '设置已保存，可以往下点「同步我的修改到线上」了' : '设置已保存；要同步还得填访问令牌', 4200);
    render();
  };

  const bmt = $('#btnMakeToken');
  if (bmt) bmt.onclick = () => {
    window.open('https://github.com/settings/tokens/new?scopes=repo&description=' +
      encodeURIComponent('麦田守望数据中心'), '_blank');
    toast('在打开的页面点最下面 Generate token，复制 ghp_... 回来粘贴', 8000);
  };
  const bpl = $('#btnPhoneLink');
  if (bpl) bpl.onclick = () => {
    const box = $('#phoneBox'), c = ghCfg();
    if (location.protocol === 'file:') {      // 本地双击打开的页面：生成的链接手机打不开
      if (box) box.innerHTML = '<div class="notice">⚠️ 你现在是<b>双击本地文件</b>打开的队长版，'
        + '这样生成的链接是 <code>file:///E:/...</code> 开头的，<b>手机打不开</b>。<br>'
        + '请改用线上网址打开队长版，再点这个按钮：<br>'
        + '<code>https://zl4639574-bit.github.io/maitian-running/captain/</code></div>';
      return;
    }
    if (!c.token) { if (box) box.innerHTML = '<div class="notice">先把访问令牌填好并保存，再生成手机链接</div>'; return; }
    const payload = { owner: c.owner, repo: c.repo, branch: c.branch, token: c.token };
    const url = location.href.replace(/#.*$/, '') + '#t=' + b64uEncode(JSON.stringify(payload));
    if (box) box.innerHTML = '<div class="field"><label>手机专用链接（存到手机书签，用它打开就不用再填令牌）</label>'
      + '<textarea class="ta" rows="3" readonly>' + esc(url) + '</textarea></div>'
      + '<button class="btn sm" id="btnCopyPhone">复制链接</button>'
      + '<div class="tiny" style="margin-top:8px;line-height:1.9">手机上：打开链接 → 加书签 → 以后每次用书签进队长版即可，'
      + '不用再填任何东西。<br>换届：把这条链接发给下一任队长就行（链接里带着权限，放在网址 # 后面，'
      + '不会被提交到仓库，但别外发；想作废就在 GitHub 里把令牌删掉重新生成一条）。</div>';
    const cb = $('#btnCopyPhone');
    if (cb) cb.onclick = () => copyText(url);
  };

  const bTest = $('#btnTest');
  if (bTest) bTest.onclick = testSync;

  const pull = $('#btnPull');
  if (pull) pull.onclick = async () => {
    toast('正在读取线上数据…');
    const ok = await loadCloud(true);
    toast(ok ? '已拉取线上数据' : '读取失败，检查用户名/仓库名/令牌');
    render();
  };
  const push = $('#btnPush');
  if (push) push.onclick = pushToGitHub;
  const rl = $('#btnResetLocal');
  if (rl) rl.onclick = () => {
    if (confirm('丢弃本机所有未同步的修改？（已同步到线上的不受影响）')) {
      LOCAL_OV = {};
      lsSet(LS_LOCAL, {});
      toast('已丢弃');
      render();
    }
  };

  const bt = $('#btnSaveTeam');
  if (bt) bt.onclick = () => {
    const t = ovLocal().team || (ovLocal().team = {});
    $$('[data-team]').forEach(el => {
      const k = el.dataset.team, v = el.value;
      if (k === 'media') t.media = v.split('\n').map(s => s.trim()).filter(Boolean).map(s => s.split(/[·\s]+/));
      else if (k === 'activities') t.activities = v.split('\n').map(s => s.trim()).filter(Boolean);
      else t[k] = v.trim();
    });
    saveLocalOv(); toast('队伍信息已保存（记得去「同步」发布）'); render();
  };

  const bh = $('#btnSaveHonors');
  if (bh) bh.onclick = () => {
    const ys = $$('[data-hy]'), ts = $$('[data-ht]');
    const arr = ys.map((y, i) => [y.value.trim(), ts[i].value.trim()]).filter(x => x[0] || x[1]);
    ovLocal().honors = arr;
    saveLocalOv(); toast('荣誉已保存'); render();
  };
  const ah = $('#btnAddHonor');
  if (ah) ah.onclick = () => {
    const info = teamInfo();
    ovLocal().honors = (info.honors || []).concat([['', '']]);
    saveLocalOv(); render();
  };
  $$('[data-hdel]').forEach(b => b.onclick = () => {
    const info = teamInfo();
    const arr = (info.honors || []).slice();
    arr.splice(+b.dataset.hdel, 1);
    ovLocal().honors = arr;
    saveLocalOv(); render();
  });

  const sm = $('#btnSaveMembers');
  if (sm) sm.onclick = () => {
    const edits = ovLocal().memberEdits || (ovLocal().memberEdits = {});
    const byName = {};
    $$('[data-me]').forEach(el => {
      const n = el.dataset.me, f = el.dataset.mf;
      byName[n] = byName[n] || {};
      byName[n][f] = el.value;
    });
    Object.entries(byName).forEach(([n, f]) => {
      const base = (BASE.roster || []).find(m => m.name === n) || {};
      const lvl = (f.level || '').split(',').map(s => s.trim()).filter(Boolean);
      edits[n] = {
        college: f.college, major: f.major, grade: f.grade,
        level: lvl.length ? lvl : (base.level || []).filter(l => l === '正式' || l === '预备'),
      };
    });
    saveLocalOv(); toast('名册修改已保存'); render();
  };
  $$('[data-mdel]').forEach(b => b.onclick = () => {
    const n = b.dataset.mdel;
    const l = ovLocal();
    l.hidden = (l.hidden || []).concat([n]);
    saveLocalOv(); toast('已从公开名册移除 ' + n); render();
  });
  $$('[data-mrestore]').forEach(b => b.onclick = () => {
    const n = b.dataset.mrestore, l = ovLocal();
    l.hidden = (l.hidden || []).filter(x => x !== n);
    saveLocalOv(); render();
  });
  const mq = $('#mRosterQ');
  if (mq) mq.oninput = () => {
    state.mRosterQ = mq.value;
    clearTimeout(window._mt);
    window._mt = setTimeout(() => { render(); const el = $('#mRosterQ'); if (el) { el.focus(); el.setSelectionRange(el.value.length, el.value.length); } }, 260);
  };

  // ---- 优秀队员 ----
  const sah = $('#btnAddHall');
  if (sah) sah.onclick = () => {
    const cur = (ov().hall || []).slice();
    cur.push({ name: '', sex: '', items: [], note: '' });
    ovLocal().hall = cur; saveLocalOv(); render();
  };
  const shh = $('#btnSaveHall');
  if (shh) shh.onclick = () => {
    const arr = [];
    Array.from(new Set($$('[data-hall]').map(x => x.dataset.hall))).forEach(i => {
      const g = f => ($(`[data-hall="${i}"][data-hf="${f}"]`) || {}).value || '';
      arr.push({ name: g('name').trim(), sex: g('sex').trim(),
                 items: g('items').split('\n').map(x => x.trim()).filter(Boolean),
                 note: g('note').trim() });
    });
    ovLocal().hall = arr.filter(a => a.name);
    saveLocalOv(); toast('已保存优秀队员'); render();
  };
  $$('[data-halldel]').forEach(b => b.onclick = () => {
    const cur = (ov().hall || []).slice();
    cur.splice(+b.dataset.halldel, 1);
    ovLocal().hall = cur; saveLocalOv(); render();
  });

  // ---- 队员直传 ----
  const sbq = $('#btnSaveQueue');
  if (sbq) sbq.onclick = () => {
    const t = ($('#q_token').value || '').trim();
    if (!t) return toast('请先填收集仓库令牌');
    qcfgSet({ owner: ghCfg().owner,
              repo: ($('#q_repo').value || '').trim() || 'maitian-run-queue',
              branch: ($('#q_branch').value || '').trim() || 'main', token: t });
    toast('令牌已存在这台设备上（不会上传到仓库）', 4200);
    render();
  };
  const bml = $('#btnMakeLink');
  if (bml) bml.onclick = () => {
    const box = $('#linkBox'), q = qcfgGet();
    if (!q || !q.token) { if (box) box.innerHTML = '<div class="notice">先填令牌并保存，再生成链接</div>'; return; }
    const url = memberLink(q);
    if (box) box.innerHTML = '<div class="field"><label>队员专用链接（发到群里，队员点开就能提交成绩）</label>'
      + '<textarea class="ta" rows="3" readonly>' + esc(url) + '</textarea></div>'
      + '<button class="btn sm" id="btnCopyLink">复制链接</button>'
      + '<div class="tiny" style="margin-top:8px">队员第一次用这条链接打开后，提交按钮会一直记在他手机上（以后用普通队员版网址也行）。</div>';
    const cb = $('#btnCopyLink');
    if (cb) cb.onclick = () => copyText(url);
  };
  const cbq = $('#btnClearQueue');
  if (cbq) cbq.onclick = () => {
    if (!confirm('关闭队员直传？（队员版的提交按钮会消失）')) return;
    qcfgSet(null); toast('已关闭'); render();
  };

  // ---- 比赛成绩管理 ----
  const cs = $('#compSel');
  if (cs) cs.onchange = () => { state.mComp = cs.value; render(); };
  const ac = $('#btnAddComp');
  if (ac) ac.onclick = () => {
    const name = ($('#c_name').value || '').trim();
    if (!name) return toast('先填比赛名称');
    const l = ovLocal();
    l.competitions = (l.competitions || []).concat([{
      id: 'c' + Date.now().toString(36), name,
      date: ($('#c_date').value || '').trim(), event: ($('#c_event').value || '').trim(),
      note: ($('#c_note').value || '').trim(), records: [],
    }]);
    saveLocalOv();
    state.mComp = l.competitions[l.competitions.length - 1].id;
    toast('已新建比赛，下面就能往里录成绩了');
    render();
  };
  const acr = $('#btnAddCompRec');
  if (acr) acr.onclick = () => {
    const cur = competitions().find(c => c.id === state.mComp) || competitions()[0];
    if (!cur) return toast('先新建一场比赛');
    const name = ($('#cr_name').value || '').trim();
    const ev = ($('#cr_event').value || '').trim();
    const raw = ($('#cr_res').value || '').trim();
    if (!name) return toast('请填姓名');
    const sec = parseSec(raw);
    if (!sec) return toast('成绩没看懂');
    addCompRecords(cur.id, [{
      name, event: ev, raw, sec: Math.round(sec * 10) / 10, fmt: fmtSec(sec),
      sex: $('#cr_sex').value, college: ($('#cr_college').value || '').trim(),
      note: ($('#cr_note').value || '').trim(),
    }]);
    toast('已加入「' + cur.name + '」');
    render();
  };
  const mm = $('#btnMergeMine');
  if (mm) mm.onclick = () => {
    const cur = competitions().find(c => c.id === state.mComp) || competitions()[0];
    const mine = myResults();
    if (!cur || !mine.length) return toast('没有可并入的成绩');
    addCompRecords(cur.id, mine.map(r => Object.assign({}, r, { note: r.note || r.rank || '' })));
    setMyResults([]);
    toast('已把 ' + mine.length + ' 条并入「' + cur.name + '」（记得同步到线上）', 4200);
    render();
  };
  $$('[data-recdel]').forEach(b => b.onclick = () => {
    const [cid, nm, sec] = String(b.dataset.recdel).split('|');
    const l = ovLocal();
    l.hiddenRecords = (l.hiddenRecords || []).concat([cid + '|' + nm + '|' + sec]);
    saveLocalOv();
    toast('已删除这条成绩');
    render();
  });
  const dc = $('#btnDelComp');
  if (dc) dc.onclick = () => {
    const cur = competitions().find(c => c.id === state.mComp);
    if (!cur || cur.builtin) return;
    if (!confirm('确定删除比赛「' + cur.name + '」？（里面的成绩一起删除）')) return;
    const l = ovLocal();
    l.competitions = (l.competitions || []).filter(c => c.id !== cur.id);
    saveLocalOv();
    state.mComp = '';
    toast('已删除');
    render();
  };
  const dcr = $('#btnDelCompRecords');
  if (dcr) dcr.onclick = () => toast('在下面的「当前榜单」里，点每行右边的「删」');

  // 照片
  const pd = $('#photoDrop'), pi = $('#photoInput');
  if (pd && pi) {
    pd.onclick = () => pi.click();
    ['dragenter', 'dragover'].forEach(ev => pd.addEventListener(ev, e => { e.preventDefault(); pd.classList.add('over'); }));
    ['dragleave', 'drop'].forEach(ev => pd.addEventListener(ev, e => { e.preventDefault(); pd.classList.remove('over'); }));
    pd.addEventListener('drop', e => handlePhotos(e.dataTransfer.files));
    pi.onchange = () => handlePhotos(pi.files);
  }
  $$('[data-pdel]').forEach(b => b.onclick = () => {
    const l = ovLocal();
    l.photos = (l.photos || []).slice();
    l.photos.splice(+b.dataset.pdel, 1);
    saveLocalOv(); render();
  });

  const pm = $('#btnPublishMine');
  if (pm) pm.onclick = publishAndSync;          // 自由成绩区：发布 + 同步一步到位
  const p2 = $('#btnPubSync2');
  if (p2) p2.onclick = publishAndSync;          // 同步分区：本机有没发布的成绩时出现
  const p3 = $('#btnPublishSync');
  if (p3) p3.onclick = publishAndSync;          // 上传成绩页：导入完就能看到的大按钮
  $$('[data-pubdel]').forEach(b => b.onclick = () => {
    const l = ovLocal();
    const arr = ovLocal().results.slice();
    arr.splice(+b.dataset.pubdel, 1);
    l.results = arr;
    saveLocalOv(); render();
  });
}

/** 照片：压缩后存到本机待同步列表 */
function handlePhotos(files) {
  if (!files || !files.length) return;
  const sel = $('#albSel'), nw = $('#albNew');
  let album = sel ? sel.value : '';
  if (album === '__new') album = (nw && nw.value.trim()) || '新相册';
  if (!album) album = '未分类';
  const list = Array.from(files);
  let done = 0;
  const l = ovLocal();
  l.photos = l.photos || [];
  const out = [];
  list.forEach(f => {
    if (!/^image\//.test(f.type)) return;
    const img = new Image();
    const fr = new FileReader();
    fr.onload = () => {
      img.onload = () => {
        const MAX = 1500;
        let w = img.width, h = img.height;
        if (w > MAX) { h = Math.round(h * MAX / w); w = MAX; }
        const cv = document.createElement('canvas');
        cv.width = w; cv.height = h;
        cv.getContext('2d').drawImage(img, 0, 0, w, h);
        const data = cv.toDataURL('image/jpeg', 0.8);
        out.push({
          album, albumDate: (album.match(/\d{4}/) || [todayStr().slice(0, 4)])[0],
          file: 'up_' + Date.now() + '_' + out.length + '.jpg',
          caption: f.name.replace(/\.[^.]+$/, '').slice(0, 18),
          data, size: Math.round(data.length * 0.75),
        });
        done++;
        if (done === list.length) {
          l.photos = l.photos.concat(out);
          saveLocalOv();
          const mb = out.reduce((a, x) => a + x.size, 0) / 1048576;
          toast('已加入 ' + out.length + ' 张到「' + album + '」（约 ' + mb.toFixed(1) + ' MB，待同步）', 4000);
          render();
        }
      };
      img.src = fr.result;
    };
    fr.readAsDataURL(f);
  });
}

/* -------------------------------------------------- GitHub 同步（队长版） */

const GH = 'https://api.github.com';

function b64enc(str) { return btoa(unescape(encodeURIComponent(str))); }

function ghHeaders(cfg) {
  return {
    'Authorization': 'Bearer ' + cfg.token,
    'Accept': 'application/vnd.github+json',
    'Content-Type': 'application/json',
    'X-GitHub-Api-Version': '2022-11-28',
  };
}

async function ghGetSha(cfg, path) {
  const r = await fetch(`${GH}/repos/${cfg.owner}/${cfg.repo}/contents/${encodeURI(path)}?ref=${encodeURIComponent(cfg.branch || 'master')}`, { headers: ghHeaders(cfg), cache: 'no-store' });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error('读取 ' + path + ' 失败 ' + r.status);
  return (await r.json()).sha;
}

async function ghPut(cfg, path, b64, message) {
  const sha = await ghGetSha(cfg, path);
  const body = { message, content: b64, branch: cfg.branch || 'main' };
  if (sha) body.sha = sha;
  const r = await fetch(`${GH}/repos/${cfg.owner}/${cfg.repo}/contents/${encodeURI(path)}`, {
    method: 'PUT', headers: ghHeaders(cfg), body: JSON.stringify(body),
  });
  if (!r.ok) {
    let msg = await r.text();
    if (/Branch .* not found/i.test(msg)) {          // 分支名不对 → 换一个再试
      const alt = (cfg.branch === 'main') ? 'master' : 'main';
      body.branch = alt;
      const r2 = await fetch(`${GH}/repos/${cfg.owner}/${cfg.repo}/contents/${encodeURI(path)}`, {
        method: 'PUT', headers: ghHeaders(cfg), body: JSON.stringify(body),
      });
      if (r2.ok) { cfg.branch = alt; lsSet(LS_CFG, cfg); return r2.json(); }
      msg = await r2.text();
    }
    throw new Error('写入 ' + path + ' 失败 ' + r.status + ' ' + msg.slice(0, 140));
  }
  return r.json();
}

/** 自动问 GitHub：这个仓库的默认分支叫什么（避免 main/master 填错） */
async function ghRealBranch(cfg) {
  try {
    const r = await fetch(`${GH}/repos/${cfg.owner}/${cfg.repo}`, { headers: ghHeaders(cfg), cache: 'no-store' });
    if (r.ok) {
      const d = await r.json();
      if (d && d.default_branch) return d.default_branch;
    }
  } catch (e) {}
  return cfg.branch || 'master';
}

/** 一键测试同步：写一条隐藏的自检标记 → 从网页回读 → 清除标记。不改动任何真实数据。 */
/** 从仓库直接读一个文件（走接口，不受网页 CDN 缓存影响）——自检用 */
async function ghGetText(cfg, path) {
  try {
    const r = await fetch(`${GH}/repos/${cfg.owner}/${cfg.repo}/contents/${encodeURI(path)}?ref=${encodeURIComponent(cfg.branch || 'master')}&t=${Date.now()}`,
      { headers: ghHeaders(cfg), cache: 'no-store' });
    if (!r.ok) return null;
    const d = await r.json();
    return decodeURIComponent(escape(atob(String(d.content || '').replace(/\s/g, ''))));
  } catch (e) { return null; }
}

/** 一键测试同步：写一条隐藏的自检标记 → 从仓库读回确认 → 再看网页端缓存 → 清除标记。不改动任何真实数据。 */
async function testSync() {
  const cfg = ghCfg();
  if (!cfg.token) return toast('先填访问令牌 → 保存设置，再点测试', 7000);
  const btn = $('#btnTest');
  const label = '测试同步（不改数据）';
  if (btn) { btn.disabled = true; btn.textContent = '测试中…（最多 90 秒）'; }
  try {
    cfg.branch = await ghRealBranch(cfg); lsSet(LS_CFG, cfg);
    const base = CLOUD_OV || EMPTY_OV;
    const stamp = Date.now();
    const mk = (extra) => '/* 由队长版写入 */\nwindow.TEAM_OVERRIDES = ' +
      JSON.stringify(Object.assign({}, base, extra, { queue: null }), null, 1) + ';\n';

    // ① 写入
    await ghPut(cfg, 'data/overrides.js', b64enc(mk({ selfTest: stamp })), '自检：写入测试标记');

    // ② 从仓库读回（走接口，最可靠，不受网页缓存影响）
    let apiOk = false;
    for (let i = 0; i < 8; i++) {
      const txt = await ghGetText(cfg, 'data/overrides.js');
      if (txt && txt.indexOf('"selfTest": ' + stamp) >= 0) { apiOk = true; break; }
      await new Promise(r => setTimeout(r, 1500));
    }

    // ③ 网页端（GitHub Pages 有缓存，通常 30~90 秒才刷新）
    let cdnOk = false;
    for (let i = 0; i < 20; i++) {
      await new Promise(r => setTimeout(r, 3000));
      if (btn) btn.textContent = '测试中…（等网页缓存 ' + ((i + 1) * 3) + 's）';
      try {
        const r = await fetch(ROOT + 'data/overrides.js?t=' + Date.now(), { cache: 'no-store' });
        if (r.ok) {
          const t = await r.text();
          const m = t.match(/=\s*([\s\S]*?);\s*$/);
          const o = m ? JSON.parse(m[1]) : {};
          if (o.selfTest === stamp) { cdnOk = true; break; }
        }
      } catch (e) {}
    }

    // ④ 清除标记（不管结果如何都擦干净测试痕迹）
    await ghPut(cfg, 'data/overrides.js', b64enc(mk({})), '自检完成：清除测试标记');
    await loadCloud(true);
    if (btn) { btn.disabled = false; btn.textContent = label; }
    render();

    if (apiOk && cdnOk) toast('✅ 测试通过：写入成功、网页端也读到了，同步完全正常', 9000);
    else if (apiOk) toast('✅ 写入成功（仓库已确认读到）。网页端还在刷新缓存（GitHub 约 1 分钟），过一会儿刷新页面就能看到 —— 同步功能本身正常', 12000);
    else toast('⚠️ 写入成功，但没能从仓库读回标记（可能是网络或令牌权限问题），把这段话发我', 12000);
  } catch (e) {
    if (btn) { btn.disabled = false; btn.textContent = label; }
    const msg = String(e && e.message || e);
    if (/Secret detected|secret_scanning/i.test(msg)) toast('被 GitHub 拦下：内容里被判定含密钥（把「队员直传」的历史配置清掉再试）', 10000);
    else toast('❌ 测试失败：' + msg, 12000);
  }
}

async function pushToGitHub() {
  const cfg = ghCfg();
  if (!cfg.token) return toast('还没填「访问令牌」：数据管理 → 同步 → 粘上 github_pat_... → 点保存设置', 6000);
  const l = LOCAL_OV || {};
  if (!pendingCount()) {
    const mine = myResults().length;
    return toast(mine ? ('本机没有待同步的改动 —— 但「上传成绩」里有 ' + mine + ' 条还没发布，先去那页点「发布并同步到线上」')
                      : '没有需要同步的修改', 9000);
  }
  cfg.branch = await ghRealBranch(cfg);   // 用仓库真实的分支（main / master 自动认）
  lsSet(LS_CFG, cfg);                     // 顺便把正确的分支存回去
  await loadCloud(true);            // 先拉一次最新的云端数据，避免把别人刚提交的覆盖掉
  const btn = $('#btnPush');
  if (btn) { btn.disabled = true; btn.textContent = '正在同步…'; }
  try {
    // 1) 云端已有的 + 本机修改合并成新的 overrides
    const cloud = CLOUD_OV || EMPTY_OV;
    const merged = {
      team: Object.assign({}, cloud.team || {}, l.team || {}),
      honors: l.honors || cloud.honors || null,
      activities: l.activities || cloud.activities || null,
      hidden: Array.from(new Set((cloud.hidden || []).concat(l.hidden || []))),
      memberEdits: Object.assign({}, cloud.memberEdits || {}, l.memberEdits || {}),
      results: (cloud.results || []).concat(l.results || []),
      competitions: (cloud.competitions || []).concat(l.competitions || []),
      compRecords: mergeCompRecords(cloud.compRecords, l.compRecords),
      hiddenRecords: Array.from(new Set((cloud.hiddenRecords || []).concat(l.hiddenRecords || []))),
      hall: (l.hall || cloud.hall || null),
      queue: null,          // 令牌绝不写进仓库（GitHub 密钥扫描会拦截，也不安全）
      photos: (cloud.photos || []).concat((l.photos || []).map(p => {
        const { data, size, ...rest } = p;
        return rest;                      // 图片本体单独提交，引用文件名
      })),
      updated: new Date().toISOString(),
    };
    // 2) 先传图片
    let n = 0;
    for (const p of (l.photos || [])) {
      const b64 = String(p.data).split(',')[1];
      await ghPut(cfg, 'images/' + p.file, b64, '上传照片 ' + p.album + ' / ' + p.file);
      n++;
      if (btn) btn.textContent = `正在同步… 照片 ${n}/${(l.photos || []).length}`;
    }
    // 3) 再传数据
    const ovB64 = btoa(unescape(encodeURIComponent('window.TEAM_OVERRIDES = ' + JSON.stringify(merged, null, 1) + ';\n')));
    await ghPut(cfg, 'data/overrides.js', ovB64, '更新队伍数据（队伍信息/荣誉/名册/成绩/照片）');
    CLOUD_OV = merged;
    LOCAL_OV = {};
    lsSet(LS_LOCAL, {});
    toast('同步成功！约 1 分钟后三个版本全部更新', 5000);
    render();
  } catch (e) {
    console.error(e);
    const msg = String(e && e.message || '');
    if (/Secret detected|secret_scanning/i.test(msg)) {
      toast('同步被 GitHub 拦下了：内容里被判定含密钥。请到「队员直传」点「关闭直传」，再点一次同步。', 9000);
    } else {
      toast('同步失败：' + msg, 7000);
    }
    if (btn) { btn.disabled = false; btn.textContent = '同步我的修改到线上'; }
  }
}

/* ------------------------------------------------- 队员直传（不经过队长） */

let QUEUE_CFG = null;      // 队员直传配置（令牌只来源：专用链接 or 本机保存，绝不来自仓库文件）

const LS_QUEUE = 'mt_queue_v1';

function qcfgGet() { return lsGet(LS_QUEUE, null); }
function qcfgSet(o) { if (o) lsSet(LS_QUEUE, o); else localStorage.removeItem(LS_QUEUE); }
function b64uEncode(str) {
  return btoa(unescape(encodeURIComponent(str))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function b64uDecode(str) {
  try { return decodeURIComponent(escape(atob(String(str).replace(/-/g, '+').replace(/_/g, '/')))); }
  catch (e) { return ''; }
}
/** 队长生成给队员的专用链接：令牌放在 # 后面，不会提交到仓库 */
function memberLink(q) {
  const base = location.href.replace(/captain\/?[^/]*$/, '');
  return base + 'member/#q=' + b64uEncode(JSON.stringify(q));
}

async function loadQueueCfg() {
  const m = location.hash.match(/[#&]q=([A-Za-z0-9_\-]+)/);      // 1) 专用链接
  if (m) {
    try {
      const o = JSON.parse(b64uDecode(m[1]));
      if (o && o.token && o.repo) { QUEUE_CFG = o; qcfgSet(o); }   // 记在这台设备上，以后普通链接也能用
    } catch (e) {}
  }
  if (!QUEUE_CFG) QUEUE_CFG = qcfgGet();                         // 2) 本机保存过
  return !!(QUEUE_CFG && QUEUE_CFG.token && QUEUE_CFG.repo);
}

/** 队长页：链接里带 #t=... 时自动填好同步配置（手机书签免输令牌） */
function loadCfgFromHash() {
  const m = location.hash.match(/[#&]t=([A-Za-z0-9_\-]+)/);
  if (!m) return false;
  try {
    const o = JSON.parse(b64uDecode(m[1]));
    if (o && o.token && o.repo) {
      lsSet(LS_CFG, { owner: o.owner || GH_DEF.owner, repo: o.repo, branch: o.branch || GH_DEF.branch, token: o.token });
      return true;
    }
  } catch (e) {}
  return false;
}

async function submitToQueue(recs) {
  if (!QUEUE_CFG || !QUEUE_CFG.token) throw new Error('还没开通队员直传');
  const id = 'q' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 6);
  const payload = { uid: id, who: (recs[0] || {}).name || '', ts: Date.now(), records: recs };
  const path = 'queue/' + id + '.json';
  const url = GH + '/repos/' + (QUEUE_CFG.owner || 'zl4639574-bit') + '/' + QUEUE_CFG.repo + '/contents/' + encodeURI(path);
  const r = await fetch(url, {
    method: 'PUT',
    headers: ghHeaders({ token: QUEUE_CFG.token }),
    body: JSON.stringify({ message: '成绩上报 ' + payload.who, content: btoa(unescape(encodeURIComponent(JSON.stringify(payload)))), branch: QUEUE_CFG.branch || 'main' }),
  });
  if (!r.ok) throw new Error('提交失败 ' + r.status + ' ' + (await r.text()).slice(0, 100));
  return true;
}

async function submitMine() {
  const list = myResults();
  const todo = list.filter(r => !r.submitted);
  if (!todo.length) return toast('没有新成绩要提交');
  const btn = $('#btnSubmitAll');
  if (btn) { btn.disabled = true; btn.textContent = '正在提交…'; }
  try {
    await submitToQueue(todo.map(r => ({
      name: r.name, event: r.event, sec: r.sec, fmt: r.fmt || fmtSec(r.sec),
      sex: r.sex || '', college: r.college || '', date: r.date || '',
      meet: r.meet || '', note: r.rank || r.note || '',
    })));
    todo.forEach(r => { r.submitted = true; });
    setMyResults(list);
    toast('已提交 ' + todo.length + ' 条，几分钟后就进全队成绩榜了', 5000);
    render();
  } catch (e) {
    toast('提交失败：' + e.message, 6000);
    if (btn) { btn.disabled = false; btn.textContent = '重新提交'; }
  }
}

/* ------------------------------------------------------------ 初始化 */

async function loadCloud(force) {
  try {
    const r = await fetch(ROOT + 'data/overrides.js?t=' + Date.now(), { cache: force ? 'reload' : 'no-store' });
    if (!r.ok) { SYNC_STATE = 'local'; return false; }
    const txt = await r.text();
    const m = txt.match(/window\.TEAM_OVERRIDES\s*=\s*([\s\S]*?);\s*$/);
    CLOUD_OV = m ? JSON.parse(m[1]) : null;
    SYNC_STATE = CLOUD_OV ? 'cloud' : 'local';
    return true;
  } catch (e) {
    SYNC_STATE = 'offline';
    return false;
  }
}

document.addEventListener('click', e => {
  const t = e.target.closest('[data-tab],[data-go],[data-album],[data-lvl],[data-ev],[data-sex],[data-msec],[data-comp],[data-ty],[data-photo],[data-lb]');
  if (!t) return;
  const d = t.dataset;
  if (d.tab) return goTab(d.tab);
  if (d.go) return goTab(d.go, { msec: d.msec });
  if (d.msec) { state.manageSec = d.msec; return render(); }
  if (d.comp !== undefined && t.classList.contains('chip')) { state.comp = d.comp; state.pbQ = ''; state.pbSex = ''; return render(); }
  if (d.ty !== undefined && t.classList.contains('chip')) {
    const f = $('#f_event');
    if (f) { f.value = d.ty; $$('[data-ty]').forEach(x => x.classList.toggle('active', x === t)); }
    return;
  }
  if (d.album !== undefined) { state.album = d.album; state.tab = 'photos'; return render(); }
  if (d.lvl !== undefined) { state.rosterLevel = d.lvl; return render(); }
  if (d.ev !== undefined && t.classList.contains('chip')) { state.pbEvent = d.ev; return render(); }
  if (d.sex !== undefined && t.classList.contains('chip')) { state.pbSex = d.sex; return render(); }
  if (d.sort) {
    if (state.pbSort && state.pbSort.key === d.sort) state.pbSort.dir = state.pbSort.dir === 'desc' ? 'asc' : 'desc';
    else state.pbSort = { key: d.sort, dir: 'asc' };
    return render();
  }
  if (d.photo !== undefined) return openLightbox(t);
  if (d.lb) {
    if (d.lb === 'close') return closeLightbox();
    return stepLightbox(d.lb === 'next' ? 1 : -1);
  }
}, false);

document.addEventListener('change', e => {
  if (e.target.id === 'rosterCollege') { state.rosterCollege = e.target.value; render(); }
}, false);

document.addEventListener('input', e => {
  if (e.target.id === 'boardQ') {
    state.pbQ = e.target.value;
    clearTimeout(window._qi);
    window._qi = setTimeout(() => { render(); const el = $('#boardQ'); if (el) { el.focus(); el.setSelectionRange(el.value.length, el.value.length); } }, 260);
  }
  if (e.target.id === 'rosterQ') {
    state.rosterQ = e.target.value;
    clearTimeout(window._ri);
    window._ri = setTimeout(() => { render(); const el = $('#rosterQ'); if (el) { el.focus(); el.setSelectionRange(el.value.length, el.value.length); } }, 260);
  }
}, false);

document.addEventListener('click', e => {
  if (e.target.id === 'btnAlbBack') { state.album = ''; render(); }
}, false);

/* 灯箱 */
let lbList = [], lbIdx = 0;
function openLightbox(el) {
  const data = $('#lbData');
  if (!data) return;
  try { lbList = JSON.parse(data.textContent); } catch (err) { lbList = []; }
  const v = (el && el.dataset ? el.dataset.photo : '') || '';
  const i = parseInt(String(v).split('|')[1], 10);
  lbIdx = isNaN(i) ? 0 : i;
  showLb();
}
function showLb() {
  const p = lbList[lbIdx];
  if (!p) return;
  $('#lbImg').src = p.s;
  $('#lbCap').textContent = p.c + '  (' + (lbIdx + 1) + '/' + lbList.length + ')';
  $('#lightbox').classList.add('on');
}
function closeLightbox() { const lb = $('#lightbox'); if (lb) lb.classList.remove('on'); }
function stepLightbox(d2) {
  if (!lbList.length) return;
  lbIdx = (lbIdx + d2 + lbList.length) % lbList.length;
  showLb();
}
document.addEventListener('keydown', e => {
  const lb = $('#lightbox');
  if (!lb || !lb.classList.contains('on')) return;
  if (e.key === 'Escape') closeLightbox();
  if (e.key === 'ArrowRight') stepLightbox(1);
  if (e.key === 'ArrowLeft') stepLightbox(-1);
}, false);

(async function init() {
  if (typeof XLSX === 'undefined' && MODE === 'captain') console.warn('SheetJS 未加载，Excel 导入不可用');
  const h = (location.hash || '').replace('#', '');
  if ((TABS[MODE] || []).some(t => t[0] === h)) state.tab = h;
  await loadCloud(false);
  await loadQueueCfg();
  if (MODE === 'captain' && loadCfgFromHash()) toast('已用链接里的账号自动填好，可以直接同步', 4000);
  render();
})();
