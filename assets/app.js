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
  catch (e) {
    const full = /quota|exceeded/i.test(String((e && e.name) || '') + ' ' + String((e && e.message) || ''));
    toast(full
      ? '本机存储满了（浏览器只给约 5MB）：先把已有照片点「同步」传到线上，本机就腾空了，再继续加照片'
      : '这个浏览器不让存数据（可能是无痕/隐私模式打开的），改动无法保存 —— 换成普通窗口打开', 12000);
    return false;
  }
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
                   newMembers: [], results: [], photos: [], competitions: [], hiddenRecords: [],
                   hall: null, queue: null, pbAdded: [], pbHidden: [] };

let CLOUD_OV = null;      // 云端 overrides.json（线上生效的修改）
let LOCAL_OV = MODE === 'captain' ? lsGet(LS_LOCAL, null) : null;   // 队长本机未同步的修改
let SYNC_STATE = 'loading';   // loading | cloud | local | offline

function ov() {
  const c = CLOUD_OV || {}, l = LOCAL_OV || {};
  return {
    team: Object.assign({}, c.team || {}, l.team || {}),
    relay: l.relay || c.relay || null,          // 成绩/资料收件中转（队员端据此直传）
    honors: l.honors || c.honors || null,
    activities: l.activities || c.activities || null,
    // 本机"恢复显示"的人（shown）优先：从隐藏集合里剔除，这样同步后所有人也看得到
    hidden: Array.from(new Set((c.hidden || []).concat(l.hidden || [])))
      .filter(n => (l.shown || []).indexOf(n) < 0),
    memberEdits: Object.assign({}, c.memberEdits || {}, l.memberEdits || {}),
    newMembers: (function () {
      const m = {};
      (c.newMembers || []).forEach(x => { if (x && x.name) m[x.name] = x; });
      (l.newMembers || []).forEach(x => { if (x && x.name) m[x.name] = x; });   // 本机的覆盖云端
      // 新增队员没填身份 → 默认「正式」；不然会被加进去却不出现在公开名册里
      return Object.keys(m).map(k => {
        const x = m[k];
        if (!(x.level || []).length) return Object.assign({}, x, { level: ['正式'] });
        return x;
      });
    })(),
    results: (function () {
      const hid = new Set(c.hiddenResults || []);
      return (c.results || []).concat(l.results || [])
        .filter(r => !hid.has(r.uid || (r.name + '|' + r.sec)));
    })(),
    photos: (c.photos || []).concat(l.photos || []),
    competitions: (c.competitions || []).concat(l.competitions || []),
    compRecords: mergeCompRecords(c.compRecords, l.compRecords),
    pbAdded: (function () {
      const hid = new Set((c.pbHidden || []).concat(l.pbHidden || []));
      return mergePbAdded(c.pbAdded, l.pbAdded)
        .filter(p => !hid.has(p.uid || (p.name + '|' + p.event)));
    })(),
    pbHidden: Array.from(new Set((c.pbHidden || []).concat(l.pbHidden || []))),
    hiddenRecords: Array.from(new Set((c.hiddenRecords || []).concat(l.hiddenRecords || []))),
    hall: l.hall || c.hall || null,
    queue: l.queue || c.queue || null,
  };
}

/** 单独录入的个人最好成绩：按 uid 合并（本机覆盖云端），没有 uid 的老数据用 姓名|项目 兜底 */
function mergePbAdded(a, b) {
  const key = x => (x && (x.uid || ((x.name || '') + '|' + (x.event || '')))) || '';
  const m = {};
  (a || []).forEach(x => { if (x && x.name) m[key(x)] = x; });
  (b || []).forEach(x => { if (x && x.name) m[key(x)] = x; });
  return Object.keys(m).map(k => m[k]);
}

function mergeCompRecords(a, b) {
  const out = {};
  [a || {}, b || {}].forEach(src => Object.keys(src).forEach(k => {
    out[k] = (out[k] || []).concat(src[k] || []);
  }));
  return out;
}

/** 把 "2024.4.28" / "2022.10.14—10.15" / "2025.9.14" 这类日期转成可比较的数字 YYYYMMDD
    （纯字符串比较会把 12 月排到 4 月前面） */
function dateKey(s) {
  const m = String(s || '').match(/(\d{4})\s*[.\-/年]\s*(\d{1,2})(?:\s*[.\-/月]\s*(\d{1,2}))?/);
  if (!m) return 0;
  return parseInt(m[1], 10) * 10000 + parseInt(m[2], 10) * 100 + parseInt(m[3] || '1', 10);
}

/** 每场比赛 / 每次测速的成绩册：原始资料里的 + 队长补充的成绩 - 被删掉的 */
function competitions() {
  const o = ov();
  const hid = new Set(o.hiddenRecords);
  const add = o.compRecords || {};
  const build = (id, base) => (base || []).concat(add[id] || [])
    .filter(r => r && r.name && r.sec && (r.keep || !hid.has(id + '|' + r.name + '|' + r.sec)));
  const out = (BASE.datasets || []).map(ds => ({
    id: ds.id, builtin: true,
    name: ds.label + (ds.date ? '（' + ds.date + '）' : ''),
    short: ds.label, date: ds.date, event: (ds.events && ds.events[0]) ? ds.events[0].event : '',
    note: ds.note || '', source: ds.source || '',
    records: build(ds.id, ds.records),
  }));
  o.competitions.forEach(c => out.push(Object.assign({ builtin: false, short: c.name }, c,
    { records: build(c.id, c.records) })));
  out.sort((a, b) => dateKey(b.date) - dateKey(a.date));   // 按真实日期从近到远
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
  const fromBase = (BASE.roster || [])
    .filter(m => !hidden.has(m.name))
    .filter(m => (m.level || []).some(l => l === '正式' || l === '预备'))
    .map(m => {
      const e = o.memberEdits[m.name] || {};
      return Object.assign({}, m, e, {
        level: e.level || (m.level || []).filter(l => l === '正式' || l === '预备'),
      });
    });
  // 队长在「队员名册」里手动添加的新队员
  const added = (o.newMembers || [])
    .filter(m => !hidden.has(m.name))
    .filter(m => (m.level || []).some(l => l === '正式' || l === '预备'));
  return fromBase.concat(added);
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
  // 个人最好成绩只统计「正式队员」；非正式的同学只在当时的比赛榜里出现
  const official = new Set(rosterList().filter(m => (m.level || []).indexOf('正式') >= 0).map(m => m.name));
  allResults().forEach(r => {
    if (!r.name || !r.sec) return;
    if (!official.has(r.name)) return;
    const k = r.name + '|' + (r.event || '');
    if (!map[k] || r.sec < map[k].sec) {
      map[k] = Object.assign({}, r, { event: r.event || '距离未标注' });
    } else if (r.sec === map[k].sec && r.local) {
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
  return Object.values(map);
}

/** 名册卡片上显示顺序：常用比赛距离在前（不然半马/全马会被 1500 米挤掉） */
function pbOrder(ev) {
  const s = String(ev || '');
  if (/5000|5\s*公里|5K/i.test(s)) return 0;
  if (/3000|3\s*公里|3K/i.test(s)) return 1;
  if (/10000|10\s*公里|10K/i.test(s)) return 2;
  if (/半马|21\.|21公里/.test(s)) return 3;
  if (/全马|42|马拉松/.test(s)) return 4;
  return 5;
}

function memberBests(name) {
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

const PHOTO_PREVIEW = {};   // 本次会话里已直传线上的照片（本地先预览，不占 localStorage）
function photoSrc(p) {
  if (p.data) return p.data;
  if (p.file && PHOTO_PREVIEW[p.file]) return PHOTO_PREVIEW[p.file];
  return ROOT + 'images/' + p.file;
}

/* ------------------------------------------------------------------ 状态 */

const state = {
  tab: 'home',
  comp: '',                                   // '' = 个人最好成绩，否则是某场比赛的 id
  compList: false,                            // 成绩榜：是否展开「赛事列表」
  pbEvent: '', pbSex: '', pbQ: '', pbSort: null,
  rosterLevel: '', rosterQ: '', rosterCollege: '',
  album: '', photoCat: '',
  manageSec: 'sync',
  mRosterQ: '',
  mComp: '',                                  // 数据管理里选中的比赛
  mFillMode: '',                              // 完善信息：'' 收起 / 'lack' 只列信息不全 / 'all' 列全部
};

const MEDAL = ['', 'g1', 'g2', 'g3'];

const TABS = {
  view:    [['home', '总览'], ['board', '成绩榜'], ['roster', '队员名册'], ['photos', '照片墙'], ['about', '荣誉与资料']],
  member:  [['home', '总览'], ['board', '成绩榜'], ['roster', '队员名册'], ['upload', '上传成绩'], ['photos', '照片墙'], ['about', '荣誉与资料']],
  captain: [['home', '总览'], ['board', '成绩榜'], ['roster', '队员名册'], ['upload', '上传成绩'],
            ['manage', '数据管理'], ['photos', '照片墙'], ['about', '荣誉与资料']],
  report:  [['upload', '成绩上报'], ['me', '完善我的资料']],   // 队员收集页：填 + 导出，不需要令牌
};

/* --------------------------------------------------------------- 渲染：总览 */

function renderHome() {
  const ros = rosterList();
  const recs = allResults().length;
  const pb = personalBests();
  const alb = albums();
  // 最近一次测速 / 比赛：取"所有场次"里日期最新的一场（含队长在线上新加的比赛/测速，不只是本机资料）
  const comps = competitions().filter(c => (c.records || []).length);
  const latest = comps[0] || null;
  const latestLabel = latest ? (latest.short || latest.name || '') : '';
  const latestDate = latest ? (latest.date || '') : '';
  const latestEv = latest ? (latest.event || (latest.events && latest.events[0] ? latest.events[0].event : '') || '') : '';
  const latestRecs = latest ? (latest.records || []).filter(r => !latestEv || !r.event || r.event === latestEv) : [];
  const ranked = latestRecs.filter(r => r.rank);
  // 有现场名次就按名次；没有（比如队长刚导入的成绩）就按成绩快慢排前 5
  const live = (ranked.length
    ? ranked.slice().sort((a, b) => (a.rank || 99) - (b.rank || 99))
    : latestRecs.slice().sort((a, b) => (a.sec || 1e9) - (b.sec || 1e9))
      .map((r, i) => Object.assign({}, r, { rank: i + 1 }))
  ).slice(0, 5);

  return `
  <div class="hero">
    ${BASE_PHOTOS.logo ? `<img class="logo" src="${ROOT}images/${esc(BASE_PHOTOS.logo)}" alt="队徽">` : ''}
    <h1>${esc(teamInfo().name || '麦田守望长跑队')}</h1>
    <p class="sub">${esc(teamInfo().alias || '')} · 成立于 ${esc(teamInfo().founded || '')}</p>
    <div class="slogan">${esc(teamInfo().slogan || '')}</div>
    ${CLOUD_OV && CLOUD_OV.updated ? `<div class="tiny" style="margin-top:12px;opacity:.75">
      数据更新于 ${esc(fmtUpd(CLOUD_OV.updated))}${MODE === 'view' ? ' · 每 30 秒自动检查一次' : ''}</div>` : ''}
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
      <h2>最近一次测速 / 比赛 · ${esc(latestLabel)}</h2>
      <button class="btn ghost sm" data-go="board">看最好成绩榜 →</button>
    </div>
    <div class="tiny" style="margin-bottom:14px">${esc(latestDate)} · ${esc(latestEv)} · 共 ${latestRecs.length} 条记录</div>
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

  const inComps = !!cur || state.compList;
  const chipsRow = `
  <div class="chips sec">
    <div class="chip ${!inComps ? 'active' : ''}" data-comp="">个人最好成绩</div>
    <div class="chip ${inComps ? 'active' : ''}" data-complist="1">赛事成绩
      <span class="n">${comps.length}</span></div>
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
    // 名册里没有的人 = 非队员（跑团朋友、外校选手…）：只显示在这场的榜里
    const memSet = new Set(rosterList().map(m => m.name));
    const guestN = rows.filter(r => r.name && !memSet.has(r.name)).length;

    return head + chipsRow + `
    <div class="card sec" style="padding:16px 20px">
      <div class="tiny" style="line-height:1.8">
        <b style="font-size:13.5px;color:var(--t1)">${esc(cur.name)}</b>
        ${cur.date ? ' · ' + esc(cur.date) : ''}
        ${cur.source ? '<br>来源：' + esc(cur.source) : ''}
        ${cur.note ? '<br>备注：' + esc(cur.note) : ''}
        <br>共 ${cur.records.length} 条记录${guestN ? '（含 ' + guestN + ' 条非队员成绩）' : ''}${evs.length ? '，项目：' + evs.map(esc).join(' / ') : ''}
        ${!cur.builtin ? ' <span class="tagbadge green">队长新增</span>' : ''}
        · <a href="#" data-complist="1">← 赛事列表</a>${MODE === 'captain' ? ' · <a href="#" data-go="manage" data-msec="comp">添加/修改这场比赛</a>' : ''}
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
            <td><b>${esc(r.name)}</b>${memSet.has(r.name) ? '' : ' <span class="tagbadge" title="不在队伍名册里，只进这一场的榜">非队员</span>'}</td>
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

  /* ---------- 赛事列表：点进去看某一场 ---------- */
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
  <p class="sub sec">上面按「一场比赛一张榜」看原始名次（含当时参赛的所有同学）；下面这一张是个人最好成绩，把所有比赛合起来、每人每项只留最快的一次，且<b>只统计正式队员</b>。</p>

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
      const items = Object.entries(b).sort((x, y) => (pbOrder(x[0]) - pbOrder(y[0])) || (x[1].sec - y[1].sec)).slice(0, 4);
      const av = m.photo && /^data:|^https?:/.test(m.photo) ? m.photo
        : ROOT + (m.photo || 'images/logo.jpg');
      return `
      <div class="pcard">
        <div class="head-row">
          <img class="avatar" src="${esc(av)}" alt="" loading="lazy" onerror="this.src='${ROOT}images/logo.jpg'">
          <div class="who">
            <div class="nm">${esc(m.name)}</div>
            <div class="meta">${m.grade ? esc(m.grade) + ' 级 · ' : ''}${esc(m.college || '')}${m.major ? ' · ' + esc(m.major) : ''}</div>
          </div>
        </div>
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
  const rosterNames = new Set(rosterList().map(m => m.name));
  const rep = MODE === 'report';        // 成绩上报页（队员填 → 导出给队长导入）
  const batch = MODE === 'captain';

  return `
  <div class="sec-head"><h1>${rep ? '成绩上报' : '上传成绩'}</h1>
    ${MODE === 'captain' ? '<button class="btn ghost sm" data-go="board">看成绩榜 →</button>' : ''}</div>

  ${rep ? `<div class="notice" style="margin-bottom:16px">
    <b>怎么把成绩交给队长（三步）</b><br>
    ① 下面把这次比赛/测速的成绩一条条填进来（填错可以删了重填）；<br>
    ② 拉到底点「复制成上报文本」，或者点「导出 CSV」存成一个小文件；<br>
    ③ 把这段文字（或那个文件）发到队群，或者直接发给队长。<br>
    <span class="tiny">不用登录、不用密码，填的内容只存在你自己手机里，不会自动上传任何东西。</span>
  </div>` : ''}

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
      <div class="field"><label>赛事名称 / 备注</label>
        <input id="f_meet" placeholder="例如 2026 杨凌马拉松" list="meetList" autocomplete="off">
        <datalist id="meetList">${meetCandidates().map(c => `<option value="${esc(c.label)}">`).join('')}</datalist>
        <div class="tiny" id="meetHint" style="margin-top:4px">打几个字就会自动对上已有的赛事名</div>
      </div>
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
        支持 .xlsx / .xls / .csv｜<b>整场成绩单（含非队员、外校选手）可以直接拖进来</b>：
        导入后在「数据管理 → 比赛成绩」新建一场比赛，点「把本机录入的成绩并进这场比赛」，就成了一张完整的榜；
        非队员只出现在这场榜里，不会进名册、也不会进个人最好成绩榜</div>
      <input type="file" id="fileInput" accept=".xlsx,.xls,.csv" style="display:none">
    </div>
    <div id="importArea"></div>
  </div>` : ''}

  ${batch ? `
  <div class="card sec">
    <h2>② 接收上报（成绩 / 资料都能贴）</h2>
    <div class="tiny" style="margin-bottom:8px">队员在「成绩上报」页复制给你的那几行，直接粘到下面就行：
      一行一条，<b>姓名,项目,成绩[,日期,赛事/名次]</b>（逗号、制表符都能认；带表头会自动按列名认列）。<br>
      名字不在名册里的（外校选手、跑团朋友）也能进来，只会出现在这场比赛的榜上。</div>
    <textarea class="ta" id="pasteBox" rows="5" placeholder="张三,5000米,18:35,2026.09.15,校运会&#10;李四,10公里,42:10"></textarea>
    <div class="chips" style="margin-top:10px"><button class="btn ghost" id="btnPasteGo">解析并预览</button>
      <span class="tiny">解析完点「加进来」，再去「数据管理 → 比赛成绩」并进某场比赛</span></div>
    <div id="pasteArea"></div>
    <div id="docAreaTop"></div>   <!-- 收到队员资料时在这里预览 -->
  </div>` : ''}

  ${batch ? `
  <div class="card sec">
    <h2>① 收件箱（队员直接提交的）</h2>
    <div class="tiny" style="margin-bottom:8px">队员在收集页点「⚡ 直接提交给队长」的内容都在这儿（存在仓库 data/inbox/）。
      <b>接收</b>后就写进你的本机，再去「数据管理 → 比赛成绩 / 队员名册」同步上线；<b>丢弃</b>会把这条从收件箱删掉。</div>
    <div class="chips"><button class="btn ghost" id="btnInboxLoad">读取收件箱</button>
      <span class="tiny">${relayCfg() ? '收件服务已配置' : '（还没配收件服务：去「数据管理 → 同步」填一次）'}</span></div>
    <div id="inboxArea"></div>
  </div>` : ''}

  <div class="card sec">
    <div class="sec-head"><h2>${rep ? '我填的成绩（' + L.length + ' 条）' : (batch ? '③' : '②') + ' 我录入的成绩'}</h2>
      <div class="chips">
        ${rep && relayCfg() ? `<button class="btn sm" id="btnSend" ${L.length ? '' : 'disabled'}>⚡ 直接提交给队长（不用发微信）</button>` : ''}
        ${rep ? `<button class="btn ${relayCfg() ? 'ghost' : ''} sm" id="btnShare" ${L.length ? '' : 'disabled'}>📤 发给队长（微信）</button>` : ''}
        <button class="btn ${rep ? 'ghost' : ''} sm" id="btnCopy" ${L.length ? '' : 'disabled'}>${rep ? '复制成上报文本（发队长）' : '复制成文本'}</button>
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
          <tr><td><b>${esc(r.name)}</b>${r.submitted ? ' <span class="tagbadge green">已提交</span>' : ''}${rosterNames.has(r.name) ? '' : ' <span class="tagbadge">非队员</span>'}</td>
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
  const addedList = (o.newMembers || []).filter(m => !state.mRosterQ || m.name.includes(state.mRosterQ));
  const editList = addedList.map(m => Object.assign({}, m, { _isNew: true }))
    .concat(ros.filter(m => !hiddenSet.has(m.name)).filter(m => state.mRosterQ
      ? m.name.includes(state.mRosterQ) : (m.level || []).some(l => l === '正式' || l === '预备')).slice(0, 60)
      .map(m => Object.assign({}, m, { _isNew: false })));
  const removed = ros.filter(m => hiddenSet.has(m.name));
  const added = o.results;
  const cfg = ghCfg();
  const pend = pendingCount();
  const lackSexCount = rosterList().filter(m => !String(m.sex || '').trim()).length;

  const SEC = [['sync', '同步'], ['comp', '比赛成绩'], ['team', '队伍信息'],
               ['honors', '荣誉'], ['hall', '优秀队员'], ['member', '队员名册'], ['table', '数据表'],
               ['photos', '照片'], ['results', '自由成绩']];
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
      <button class="btn ghost" id="btnTest">测试同步（会写一次测试标记）</button>
      <button class="btn ghost" id="btnTokenCheck">检查令牌权限（只看不改）</button>
    </div>
    <div class="tiny" style="margin:14px 0 6px;line-height:1.7">
      <b>收件中转（队员"直接提交"用，可选）</b>：照 云端中转/scf/部署说明.txt 把云函数建好后，
      把它的访问地址和队伍口令填在这里 → 保存设置 → 同步，队员端就会出现「⚡ 直接提交给队长」。
      地址和口令不含任何令牌，可以放心同步。
    </div>
    <div class="grid2">
      <div class="field"><label>收件服务地址</label><input id="rlUrl" value="${esc((ov().relay && ov().relay.url) || '')}" placeholder="https://xxx.apigw.tencentcs.com/release/"></div>
      <div class="field"><label>队伍口令</label><input id="rlCode" value="${esc((ov().relay && ov().relay.code) || '')}" placeholder="自己起一个，告诉队员"></div>
    </div>
    <div class="chips" style="margin-top:8px"><button class="btn ghost" id="btnRelaySave">保存收件设置</button>
      <button class="btn ghost" id="btnRelayTest">测试收件服务</button>
      <span class="tiny">测试只发一条"连接测试"，队长可在收件箱里丢掉</span>
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
      原始名册 ${ros.length} 人${(o.newMembers || []).length ? '，队长新增 ' + (o.newMembers || []).length + ' 人' : ''}
      （展示版显示正式/预备的 ${rosterList().length} 人）。改完记得去「同步」发布。
    </div>

    ${(LOCAL_OV && ((LOCAL_OV.newMembers || []).length + Object.keys(LOCAL_OV.memberEdits || {}).length)) ? `
    <div class="notice" style="border-color:var(--wheat);margin-bottom:16px;line-height:2">
      ⚠️ 名册有 <b>${(LOCAL_OV.newMembers || []).length + Object.keys(LOCAL_OV.memberEdits || {}).length}</b> 处修改
      还<b>只在这台设备上</b>（新增 ${(LOCAL_OV.newMembers || []).length} 人 / 修改 ${Object.keys(LOCAL_OV.memberEdits || {}).length} 人）。
      <b>不点同步，展示版的名册不会变。</b>
      ${ghCfg().token ? '<div class="chips" style="margin-top:10px"><button class="btn" id="btnRosterSync">立即同步到线上</button></div>'
                      : '<br>另外还没配「访问令牌」，去「同步」里填一次就能发布了。'}
    </div>` : ''}

    <div class="notice" style="margin-bottom:18px;border-color:var(--wheat)">
      <b>＋ 添加新队员</b>
      <div class="grid2" style="margin:10px 0 4px">
        <div class="field"><label>姓名 *</label><input id="nm_name" placeholder="例如 张三"></div>
        <div class="field"><label>性别</label>
          <select id="nm_sex"><option value="">未填</option><option value="男">男</option><option value="女">女</option></select></div>
        <div class="field"><label>学院</label><input id="nm_college" placeholder="例如 林学院"></div>
        <div class="field"><label>专业</label><input id="nm_major" placeholder="例如 林学2101"></div>
        <div class="field"><label>年级</label><input id="nm_grade" placeholder="例如 2023" class="w60"></div>
        <div class="field"><label>身份</label>
          <select id="nm_level"><option value="正式">正式</option><option value="预备">预备</option><option value="正式,预备">正式+预备</option></select></div>
      </div>
      <button class="btn" id="btnAddMember" style="margin-top:8px">添加到名册</button>
      <span class="tiny" style="margin-left:10px">添加完点「同步我的修改到线上」，全队名册立刻多这个人</span>
      <div id="nmAddBox"></div>
    </div>

    <div class="notice" style="margin-bottom:18px">
      <b>＋ 批量添加队员（一次加一批）</b>
      <div class="tiny" style="margin:8px 0">
        从 Excel / 微信表格里<b>复制几行直接粘到下面</b>（一行一个人）。列的默认顺序是
        <b>姓名、学院、专业、年级、性别、身份</b>；如果第一行是表头（含"姓名/学院/…"）会自动按表头认列。
        也可以点右边按钮选一个 Excel / CSV 文件。身份那列填「正式」或「预备」，空着按「正式」算。
      </div>
      <textarea class="ta" id="nmBatch" rows="5" placeholder="张伟&#9;林学院&#9;林学2101&#9;2023&#9;男&#9;正式&#10;李娜&#9;园艺学院&#9;园艺2102&#9;2023&#9;女&#9;预备"></textarea>
      <div class="chips" style="margin-top:10px">
        <button class="btn" id="btnNmPreview">解析并预览</button>
        <button class="btn ghost" id="btnNmFile">选 Excel / CSV 文件</button>
        <input type="file" id="nmFileInput" accept=".xlsx,.xls,.csv" style="display:none">
      </div>
      <div id="nmBatchBox"></div>
    </div>
    <div class="notice" style="margin-bottom:18px;border-color:var(--wheat)">
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

    <div class="notice" style="margin-bottom:18px">
      <b>＋ 完善队员信息（补齐 性别 / 学院 / 专业 / 年级）</b>
      <div class="tiny" style="margin:8px 0">
        当初只填了个名字、信息没填全的队员，在这里补齐就行。名册现在 ${rosterList().length} 人，
        其中 <b>${lackInfoList().length}</b> 人信息不全${lackSexCount ? '（缺性别 ' + lackSexCount + ' 人）' : ''}。
      </div>
      <div class="chips">
        <button class="btn" id="btnFillList">列出信息不全的 ${lackInfoList().length} 人</button>
        <button class="btn ghost" id="btnFillAll">列出名册全部 ${rosterList().length} 人</button>
        <button class="btn ghost" id="btnDocImport">＋ 导入队员资料（队员发来的文件）</button>
        <button class="btn ghost" id="btnDocSheet">＋ 导入收集表（Excel/CSV，一行一个人）</button>
        <input type="file" id="docSheetFile" accept=".xlsx,.xls,.csv" style="display:none">
        <span class="tiny" style="flex-basis:100%">收集表（腾讯文档 / 问卷星 等）导出的 Excel 直接选进来就行：
          列名认「姓名 / 性别 / 学院 / 专业 / 年级 / 800米 / 1500米 / 3000米 / 5000米 / 10000米 / 半马 / 全马」，
          「提交时间」「填写人」之类的列会自动忽略；没有的距离填「无」即可。</span>
        <div id="docSheetArea" style="flex-basis:100%"></div>
        ${(() => {
          const hid = ov().hidden || [];
          if (!hid.length) return '';
          return `<div class="notice" style="flex-basis:100%;margin-top:12px">
            <b>已隐藏 ${hid.length} 人</b>（不在名册和榜单里显示，所以搜不到、也改不了他们的信息）：
            <div style="margin-top:6px">${hid.map(n => `<span style="display:inline-block;margin:4px 10px 0 0;white-space:nowrap">${esc(n)}<button class="btn flat sm" style="margin-left:6px" data-unhide="${esc(n)}">恢复显示</button></span>`).join('')}</div>
            <div class="tiny" style="margin-top:6px">点「恢复显示」后，点「同步我的修改到线上」，他就会回到名册里（名单口径跟着变）。</div>
          </div>`;
        })()}
        <input type="file" id="docFile" accept=".json,.txt,.csv" style="display:none">
        <span class="tiny" style="flex-basis:100%">队员在「成绩上报 → 完善我的资料」里导出的 .json 小文件（连照片一起）直接选进来；
          队员发来的一段文字也可以粘在下面（每行「字段 值」，Tab 或冒号分隔，和导出的文本一致）。</span>
        <textarea class="ta" id="docText" rows="3" style="flex-basis:100%;width:100%"
          placeholder="姓名	张三&#10;性别	男&#10;学院	林学院&#10;专业	林学&#10;年级	2023&#10;5000米	18:35&#10;半马	无"></textarea>
        <button class="btn ghost" id="btnDocParse">解析这段文字</button>
        <div id="docArea" style="flex-basis:100%"></div>
      </div>
      <div id="fillBox">${state.mFillMode ? fillTableHtml(state.mFillMode) : ''}</div>
      <div class="tiny" style="margin-top:14px">批量补全：一行一条 <b>姓名,性别,学院,专业,年级</b>（不补的列就空着或少写；有表头会自动认列）</div>
      <textarea class="ta" id="fillBatch" rows="4" placeholder="阿巴小洛,男&#10;汪楷,男,水保所,水保2201,2020"></textarea>
      <div class="chips" style="margin-top:10px"><button class="btn ghost" id="btnFillPreview">解析并预览</button></div>
      <div id="fillBatchBox"></div>
    </div>

    <div class="mgrid">
      ${editList.map(m => {
        const e = m._isNew ? m : (o.memberEdits[m.name] || {});
        const k = m._isNew ? ('data-muid="' + esc(m.uid || m.name) + '"') : ('data-me="' + esc(m.name) + '"');
        return `
        <div class="mrow">
          <div class="mrow-h"><b>${esc(m.name)}</b>
            ${m._isNew ? '<span class="tagbadge green">新增</span>' : ''}
            <span class="tagbadge ${(m.level || []).some(l => l === '正式' || l === '预备') ? 'wheat' : ''}">${esc((m.level || []).join('/') || '未分级')}</span>
          </div>
          <div class="mrow-f">
            <select ${k} data-mf="sex">
              ${[['', '性别—'], ['男', '男'], ['女', '女']].map(([v, l]) =>
                `<option value="${v}" ${((e.sex != null ? e.sex : (m.sex || '')) || '') === v ? 'selected' : ''}>${l}</option>`).join('')}
            </select>
            <input ${k} data-mf="college" value="${esc(e.college != null ? e.college : (m.college || ''))}" placeholder="学院">
            <input ${k} data-mf="major" value="${esc(e.major != null ? e.major : (m.major || ''))}" placeholder="专业">
            <input ${k} data-mf="grade" value="${esc(e.grade != null ? e.grade : (m.grade || ''))}" placeholder="年级" class="w60">
            <select ${k} data-mf="level">
              ${[['', '未分级'], ['正式', '正式'], ['预备', '预备'], ['正式,预备', '正式+预备']].map(([v, l]) =>
                `<option value="${v}" ${(e.level ? e.level.join(',') : (m.level || []).join(',')) === v ? 'selected' : ''}>${l}</option>`).join('')}
            </select>
            ${m._isNew
              ? '<button class="btn danger sm" data-muiddel="' + esc(m.uid || m.name) + '">删除</button>'
              : '<button class="btn danger sm" data-mdel="' + esc(m.name) + '">删除</button>'}
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

  ${state.manageSec === 'table' ? `
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

  ${state.manageSec === 'photos' ? `
  <div class="card sec">
    <h2>照片管理</h2>
    <div class="tiny" style="margin-bottom:14px">手机相册里的照片可以直接选，浏览器会自动压缩后再上传（长边 1500px）。
      ${ghCfg().token
        ? '<br>已配好令牌：<b>选完就会直接传到线上</b>，不占用本机空间，可以一次选很多张。'
        : '<br>⚠️ 还没配令牌：照片先存在本机（浏览器只给约 5MB，约 10 张）。<br>建议先到「同步」里配好令牌，之后再传照片就会直接上线上。'}</div>
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
    ${(LOCAL_OV && (LOCAL_OV.photos || []).length) ? `
    <div style="margin-top:20px">
      <h3>还没同步的照片（${LOCAL_OV.photos.length} 张）</h3>
      <div class="tiny" style="margin:8px 0 12px">点「数据管理 → 同步 → 同步我的修改到线上」，这些照片就会出现在照片墙里。</div>
      <div class="pgrid">${LOCAL_OV.photos.map((p, i) => `
        <div class="pitem"><img src="${photoSrc(p)}">
          <button class="btn danger sm" data-pdel="${i}" style="position:absolute;top:6px;right:6px">删</button></div>`).join('')}
      </div>
    </div>` : ''}
    ${(CLOUD_OV && (CLOUD_OV.photos || []).length) ? `
    <div class="notice" style="margin-top:16px">
      ${(LOCAL_OV && (LOCAL_OV.photos || []).length)
        ? '已上线的照片：' + CLOUD_OV.photos.length + ' 张（上面那批同步后也会计入）'
        : '✅ 照片全部已同步上线：' + CLOUD_OV.photos.length + ' 张，在「照片墙」里可以看到'}
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
          <img src="${photoSrc(p)}" loading="lazy" alt="">
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
                manage: renderManage, photos: renderPhotos, about: renderAbout, me: renderMe };
  $('#page').innerHTML = (map[state.tab] || renderHome)()
    + `<div class="foot">${esc(teamInfo().name || '')} · 数据中心
         <br><a href="${ROOT}guide.txt" target="_blank">📖 ${MODE === 'view' ? '使用说明' : '使用说明（怎么上传 / 怎么改）'}</a>
         <br><span style="opacity:.7">数据更新于 ${esc(BASE.generated || '')}</span></div>`;
  if (state.tab === 'upload') bindUpload();
  if (state.tab === 'me') bindMe();
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

  const ibl = $('#btnInboxLoad');
  if (ibl) ibl.onclick = loadInbox;

  const pg = $('#btnPasteGo');
  if (pg) pg.onclick = () => {
    const ta = $('#pasteBox');
    const txt = ta ? ta.value : '';
    // 自动识别：队员资料（含「姓名」字段且带各项距离/教育信息）还是成绩上报
    const isDoc = /^\s*\{/.test(txt) && /maitian-member/.test(txt)
      || /队员资料|性别\s*[\t:：]|学院\s*[\t:：]|(800米|1500米|半马|全马)\s*[\t:：]/.test(txt);
    if (isDoc) {
      const doc = parseMemberDoc(txt);
      if (!doc) return toast('像是队员资料，但没解析出姓名，检查一下内容');
      memberDocQueue = { doc: doc };
      toast('识别为「队员资料」，确认下面这份就点导入', 6000);
      renderMemberDocPreview();
      return;
    }
    pasteRows = pasteParseText(txt);
    renderPasteArea();
  };



  const drop = $('#drop'), fi = $('#fileInput');
  if (drop && fi) {
    drop.onclick = () => fi.click();
    ['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('over'); }));
    ['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove('over'); }));
    drop.addEventListener('drop', e => { if (e.dataTransfer.files[0]) readTableFile(e.dataTransfer.files[0]); });
    fi.onchange = () => { if (fi.files[0]) readTableFile(fi.files[0]); };
  }

  const mi = $('#f_meet');
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

  const sd = $('#btnSend');
  if (sd) sd.onclick = async () => {
    sd.disabled = true; sd.textContent = '提交中…';
    const payload = { date: todayStr(), rows: myResults().map(r => ({ name: r.name, event: r.event,
      fmt: r.fmt || fmtSec(r.sec), sec: r.sec, date: r.date, meet: r.meet || '', rank: r.rank || '' })) };
    const res = await postToRelay('scores', payload);
    sd.disabled = false; sd.textContent = '⚡ 直接提交给队长（不用发微信）';
    if (res.ok) { toast('已提交给队长 ✅ 不用再发微信了（他想导入时在收件箱里就能看到）', 9000); }
    else { toast('直接提交没成功：' + res.error + '。已改用分享/复制，一样能交给队长', 11000); }
  };

  const sh = $('#btnShare');
  if (sh) sh.onclick = async () => {
    const lines = ['麦田守望 · 成绩上报（' + todayStr() + '）',
      '姓名\t项目\t成绩\t日期\t赛事/名次']
      .concat(myResults().map(r => [r.name, r.event, r.fmt || fmtSec(r.sec), r.date, r.meet || r.rank || ''].join('\t')));
    const txt = lines.join('\n');
    const json = JSON.stringify({ type: 'maitian-scores', date: todayStr(),
      rows: myResults().map(r => ({ name: r.name, event: r.event, fmt: r.fmt || fmtSec(r.sec),
        sec: r.sec, date: r.date, meet: r.meet || '', rank: r.rank || '' })) }, null, 1);
    const r = await shareToCaptain({ text: txt, json: json, fname: '麦田守望_成绩上报_' + todayStr() + '.json',
      tip: '麦田守望 成绩上报（' + myResults().length + ' 条），请队长导入' });
    shareToast(r, '成绩');
  };

  const cp = $('#btnCopy');
  if (cp) cp.onclick = () => {
    const txt = '麦田守望 · 成绩上报（' + todayStr() + '）\n'
      + '姓名\t项目\t成绩\t日期\t赛事/名次\n'
      + myResults().map(r => [r.name, r.event, r.fmt || fmtSec(r.sec), r.date, r.meet || r.rank || ''].join('\t')).join('\n');
    copyText(txt);
    toast('已复制，直接粘到队群里发给队长即可', 6000);
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

/** 成绩单元格 → 秒。支持：17:35 / 1:23:29 / 18'35" / 18.5（分钟）
    / Excel 里存成时间格式（显示 17:35，实际值 0.7326）/ 直接是秒数（1022 = 17:02） */
function secFromCell(v) {
  const t = String(v == null ? '' : v).trim();
  if (t === '') return 0;
  if (/^\d+(\.\d+)?$/.test(t)) {
    const n = parseFloat(t);
    if (n > 0 && n < 1) return Math.round(n * 86400);   // Excel 时间格式（一天的比例）
    if (n >= 60 && n <= 86400) return Math.round(n);    // 直接写秒数
  }
  return parseSec(v);
}

function readTableFile(file) {
  const isCsv = /\.csv$/i.test(file.name || '');
  const r = new FileReader();
  r.onload = e => {
    try {
      const buf = new Uint8Array(e.target.result);
      let wb;
      if (isCsv) {
        // CSV：先按 UTF-8 解；乱码（微信/国内软件导出的 GBK 表）就改按 GBK 解
        let txt;
        try { txt = new TextDecoder('utf-8', { fatal: true }).decode(buf); }
        catch (err) {
          try { txt = new TextDecoder('gbk').decode(buf); }
          catch (e2) { txt = new TextDecoder('utf-8').decode(buf); }
        }
        wb = XLSX.read(txt.replace(/^\ufeff/, ''), { type: 'string', raw: true });
      } else {
        wb = XLSX.read(buf, { type: 'array' });
      }
      const names = wb.SheetNames;
      const sheets = names.map(n => XLSX.utils.sheet_to_json(wb.Sheets[n], { header: 1, raw: true, defval: '' }));
      const first = sheets[0];
      const hIdx = guessHeaderRow(first);
      pendingFile = { name: file.name, sheetNames: names, sheets };
      const cols = colOptions(first, hIdx);
      importCfg = {
        sheet: 0, header: hIdx,
        nameCol: guessCol(cols, /姓名|名字|人员|队员|选手/),
        resCol: guessCol(cols, /成绩|用时|时间|结果|净计时/),
        sexCol: guessCol(cols, /性别/), colCol: guessCol(cols, /学院|院系|单位/),
        rankCol: guessCol(cols, /名次|排名|rank/i),
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

  const memberSet = new Set(rosterList().map(m => m.name));
  const prev = body.slice(0, 6).map(r => {
    const sec = secFromCell(r[rs]);
    const rn = String(r[nm] == null ? '' : r[nm]).replace(/[（(].*?[)）]/g, '').replace(/\s+/g, '');
    return `<tr><td>${esc(r[nm])}</td><td>${esc(r[rs])}</td>
      <td class="tm">${sec ? esc(fmtSec(sec)) : '<span style="color:var(--red)">认不出</span>'}</td>
      <td>${memberSet.has(rn) ? '<span class="tagbadge green">队员</span>' : '<span class="tagbadge">非队员</span>'}</td></tr>`;
  }).join('');

  const selBox = (label, key, allowNone, val) => `
    <div class="field"><label>${label}</label><select data-map="${key}">
      ${allowNone ? '<option value="-1">（不用）</option>' : ''}
      ${cols.map(c => `<option value="${c.idx}" ${c.idx === val ? 'selected' : ''}>${esc(c.label)}</option>`).join('')}
    </select></div>`;

  box.innerHTML = `
  <div style="margin-top:16px">
    <div class="tiny" style="margin-bottom:10px">已读取 <b>${esc(pendingFile.name)}</b>，${body.length} 行数据
      ${pendingFile.sheetNames.length > 1 ? '，共 ' + pendingFile.sheetNames.length + ' 个工作表' : ''}。<br>
      不认识的姓名（非本队队员）也可以一起导入：他们<b>只出现在这场比赛的榜上</b>，不会进名册、也不会进个人最好成绩榜。</div>
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
      ${selBox('名次列', 'rankCol', true, importCfg.rankCol)}
      <div class="field"><label>项目 / 距离</label><select data-map="event">
        ${IMPORT_EVENTS.map(e => `<option ${e === importCfg.event ? 'selected' : ''}>${esc(e)}</option>`).join('')}
      </select></div>
      <div class="field"><label>日期</label><input data-map="date" value="${esc(importCfg.date)}"></div>
      <div class="field"><label>赛事 / 备注</label><input data-map="meet" value="${esc(importCfg.meet)}"></div>
    </div>
    <div class="tiny" style="margin-bottom:8px">成绩认得出这些：<b>17:35</b>、1:23:29、18'35"、18.5（分钟），
      以及 Excel 里存成时间格式的（单元格显示 17:35 但实际是 0.7326）和直接写秒数的（1022 = 17:02）。</div>
    <div class="preview"><table class="tbl" style="min-width:auto">
      <thead><tr><th class="no-sort">姓名</th><th class="no-sort">原始成绩</th><th class="no-sort">识别为</th><th class="no-sort">是否队员</th></tr></thead>
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
        importCfg.nameCol = guessCol(c2, /姓名|名字|人员|队员|选手/);
        importCfg.resCol = guessCol(c2, /成绩|用时|时间|结果|净计时/);
        importCfg.sexCol = guessCol(c2, /性别/);
        importCfg.colCol = guessCol(c2, /学院|院系|单位/);
        importCfg.rankCol = guessCol(c2, /名次|排名|rank/i);
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
    // 姓名：去掉括号备注和空格；2~14 个字符，允许 中文 / 维吾尔名里的「·」/ 拼音或英文名
    const name = String(r[importCfg.nameCol] == null ? '' : r[importCfg.nameCol])
      .replace(/[（(].*?[)）]/g, '').replace(/\s+/g, '');
    if (!/^[\u4e00-\u9fa5·a-zA-Z][\u4e00-\u9fa5·a-zA-Z0-9]{1,13}$/.test(name)) { noName++; return; }
    const raw = r[importCfg.resCol];
    const sec = secFromCell(raw);
    if (!sec) { bad++; return; }
    let ev = importCfg.event;
    const m = String(raw == null ? '' : raw).match(/[（(]\s*(\d+)\s*k/i);
    if (m) ev = (parseInt(m[1], 10) * 1000) + '米';
    out.push({
      uid: newUid(), name, event: ev, raw: String(raw == null ? '' : raw),
      sec: Math.round(sec * 10) / 10, fmt: fmtSec(sec),
      sex: importCfg.sexCol >= 0 ? String(r[importCfg.sexCol] || '') : '',
      college: importCfg.colCol >= 0 ? String(r[importCfg.colCol] || '') : '',
      rank: importCfg.rankCol >= 0 ? String(r[importCfg.rankCol] == null ? '' : r[importCfg.rankCol]).trim() : '',
      date: importCfg.date, meet: importCfg.meet, ts: Date.now(),
    });
  });
  if (!out.length) return toast('一条都没导入成功，检查一下列对应关系');
  const memberSet = new Set(rosterList().map(m => m.name));
  const guests = out.filter(x => !memberSet.has(x.name)).length;
  addMyResults(out);
  pendingFile = null;
  toast('已导入 ' + out.length + ' 条' + (bad ? '，跳过 ' + bad + ' 条成绩认不出的' : '')
        + (noName ? '，跳过 ' + noName + ' 条姓名看不懂的' : '')
        + (guests ? '。其中 ' + guests + ' 位不在名册（非队员）：只会出现在这场比赛的榜上，不进名册、也不进个人最好成绩榜' : '')
        + (MODE === 'captain' ? '；点下面「发布并同步到线上」全队才能看到' : ''), 11000);
  state.tab = MODE === 'captain' ? 'upload' : 'board';   // 队长留在本页，才能看到发布按钮
  render();
}

/** 一键发给队长：手机原生分享面板（能带文件），不行再退回复制
    返回 'share-file' | 'share-text' | 'copy' | 'cancel' */
async function shareToCaptain(o) {
  const text = o.text || '';
  try {
    if (o.json && o.fname && navigator.canShare) {
      const f = new File([o.json], o.fname, { type: 'application/json' });
      if (navigator.canShare({ files: [f] })) {
        await navigator.share({ files: [f], title: '麦田守望 · 上报', text: o.tip || '队里上报，请队长导入' });
        return 'share-file';
      }
    }
    if (navigator.share) {
      await navigator.share({ title: '麦田守望 · 上报', text: text });
      return 'share-text';
    }
  } catch (e) {
    if (e && e.name === 'AbortError') return 'cancel';
  }
  copyText(text);
  return 'copy';
}

/** 统一的分享结果提示 */
function shareToast(r, what) {
  if (r === 'share-file') toast('已打开分享面板：选微信 → 发给队长就行（' + what + '已经打包好）', 8000);
  else if (r === 'share-text') toast('已打开分享面板：选微信 → 发给队长就行', 8000);
  else if (r === 'cancel') toast('已取消（数据还在本机，随时可以再发）');
  else toast('这个浏览器不支持直接分享，已经帮你复制好了：粘给队长即可', 8000);
}

/* ---------------- 队员「完善我的资料」收集页 ---------------- */

const ME_PB = ['800米', '1500米', '3000米', '5000米', '10000米', '半马', '全马'];
const LS_ME = 'mt_me_v1';

function meDraft() {
  const v = lsGet(LS_ME, null);                 // lsGet 已经 JSON.parse 过，别再 parse 一次
  return (v && typeof v === 'object') ? v : {};
}
function saveMeDraft(d) { lsSet(LS_ME, d); }

/** 资料文本（队长能直接粘贴导入） */
function meText(d) {
  const pb = d.pb || {};
  const lines = ['#麦田守望 队员资料',
    '姓名\t' + (d.name || ''),
    '性别\t' + (d.sex || ''),
    '学院\t' + (d.college || ''),
    '专业\t' + (d.major || ''),
    '年级\t' + (d.grade || '')];
  ME_PB.forEach(ev => { lines.push(ev + '\t' + ((pb[ev] || '').trim() || '无')); });
  lines.push('照片\t' + (d.photo ? '（在导出的资料文件里）' : '无'));
  return lines.join('\n');
}

function renderMe() {
  const d = meDraft();
  const pb = d.pb || {};
  const names = rosterList().map(m => m.name);
  const inRoster = d.name && names.indexOf(d.name) >= 0;
  return `
  <div class="sec-head"><h1>完善我的资料</h1>
    ${d.name ? `<button class="btn ghost sm" data-go="upload">去上报成绩 →</button>` : ''}</div>

  <div class="notice" style="margin-bottom:16px">
    <b>填完怎么交给队长</b><br>
    ① 把下面填好（最好成绩没有的就填「无」）；② 点「复制资料文本」或「导出资料文件（含照片）」；<br>
    ③ 发给队长，队长会把它写进队员名册和成绩榜。<br>
    <span class="tiny">不用登录、不会自动上传；照片只在你自己手机上，随资料文件发给队长。</span>
  </div>

  <div class="card sec">
    <h2>① 基本信息</h2>
    <div class="grid2" style="margin-bottom:14px">
      <div class="field"><label>姓名 *</label><input id="me_name" value="${esc(d.name || '')}" list="meNameList" placeholder="例如 张津浩">
        <datalist id="meNameList">${names.map(n => `<option value="${esc(n)}">`).join('')}</datalist>
        <div class="tiny" style="margin-top:4px">${d.name ? (inRoster ? '✅ 在名册里，队长会更新你的资料' : '❓ 名册里还没有这个名字，队长会新增一位') : '开始输入姓名'}</div>
      </div>
      <div class="field"><label>性别</label><select id="me_sex">
        ${['', '男', '女'].map(v => `<option value="${v}" ${(d.sex || '') === v ? 'selected' : ''}>${v || '未填'}</option>`).join('')}
      </select></div>
      <div class="field"><label>学院</label><input id="me_college" value="${esc(d.college || '')}" placeholder="例如 林学院"></div>
      <div class="field"><label>专业 / 班级</label><input id="me_major" value="${esc(d.major || '')}" placeholder="例如 林学 2301"></div>
      <div class="field"><label>年级</label><input id="me_grade" value="${esc(d.grade || '')}" placeholder="例如 2023"></div>
    </div>

    <h2 style="margin-top:6px">② 个人最好成绩（没有就填「无」）</h2>
    <div class="tiny" style="margin-bottom:10px">从 800 米到全马，跑过的就填最好一次（如 2:15、18:35、1:23:29）；没跑过的填「无」。</div>
    <div class="grid2">
      ${ME_PB.map(ev => `<div class="field"><label>${esc(ev)}</label>
        <div style="display:flex;gap:6px">
          <input id="me_pb_${esc(ev)}" value="${esc(pb[ev] || '')}" placeholder="无 / 成绩" style="flex:1">
          <button class="btn flat sm" data-menone="${esc(ev)}" style="white-space:nowrap">无</button>
        </div></div>`).join('')}
    </div>

    <h2 style="margin-top:18px">③ 个人照片（可选）</h2>
    <div class="tiny" style="margin-bottom:10px">选一张正脸照，会自动压小；没上传的，名册里先用队徽显示。</div>
    <div class="drop" id="mePhotoDrop">
      <div class="big">🖼</div>
      <div><b>点这里选照片</b>（手机可以从相册选）</div>
      <div class="tiny" style="margin-top:6px">jpg / png / heic 截图都行，会压到 360px 左右</div>
      <input type="file" id="mePhotoFile" accept="image/*" style="display:none">
    </div>
    ${d.photo ? `<div style="margin-top:12px;display:flex;align-items:center;gap:12px">
      <img class="avatar" style="width:72px;height:72px" src="${esc(d.photo)}">
      <button class="btn danger sm" id="mePhotoDel">删除照片</button></div>` : ''}

    <div class="chips" style="margin-top:20px">
      <button class="btn" id="meSave">保存资料</button>
      ${relayCfg() ? `<button class="btn" id="meSend" ${d.name ? '' : 'disabled'}>⚡ 直接提交给队长（不用发微信）</button>` : ''}
      <button class="btn ${relayCfg() ? 'ghost' : ''}" id="meShare" ${d.name ? '' : 'disabled'}>📤 发给队长（微信）</button>
      <button class="btn ghost" id="meCopy" ${d.name ? '' : 'disabled'}>复制资料文本</button>
      <button class="btn ghost" id="meExport" ${d.name ? '' : 'disabled'}>导出资料文件（含照片）</button>
    </div>
    <div class="tiny" style="margin-top:8px">「资料文件」是一个 .json 小文件，里面连照片一起打包，队长选这个文件就能一次导入。</div>
  </div>`;
}

function bindMe() {
  const g = id => { const el = $(id); return el ? el.value.trim() : ''; };
  const collect = () => {
    const d = meDraft();
    const pb = {};
    ME_PB.forEach(ev => { pb[ev] = g('#me_pb_' + ev); });
    return Object.assign({}, d, {
      type: 'maitian-member', name: g('#me_name'), sex: g('#me_sex'),
      college: g('#me_college'), major: g('#me_major'), grade: g('#me_grade'),
      pb: pb, updated: new Date().toISOString(),
    });
  };
  const save = () => { saveMeDraft(collect()); return meDraft(); };

  $$('[data-menone]').forEach(b => b.onclick = () => {
    const el = $('#me_pb_' + b.dataset.menone);
    if (el) el.value = '无';
    toast('已填「无」');
  });
  const sv = $('#meSave');
  if (sv) sv.onclick = () => { const d = save(); toast('已保存到本机：' + (d.name || '（还没填姓名）'), 5000); render(); };
  const sd2 = $('#meSend');
  if (sd2) sd2.onclick = async () => {
    sd2.disabled = true; sd2.textContent = '提交中…';
    const d3 = save();
    const res = await postToRelay('member', d3);
    sd2.disabled = false; sd2.textContent = '⚡ 直接提交给队长（不用发微信）';
    if (res.ok) toast('资料已提交给队长 ✅（含照片）', 9000);
    else toast('直接提交没成功：' + res.error + '。已改用分享/复制，一样能交给队长', 11000);
  };

  const sh2 = $('#meShare');
  if (sh2) sh2.onclick = async () => {
    const d2 = save();
    const n = String(d2.pb && (d2.pb['5000米'] || d2.pb['3000米'] || '') || '').trim();
    const r = await shareToCaptain({ text: meText(d2),
      json: JSON.stringify(d2, null, 1), fname: '麦田守望_我的资料_' + (d2.name || '未填') + '.json',
      tip: '麦田守望 队员资料：' + (d2.name || '') + (n ? '（5000米 ' + n + '）' : '') + '，请队长导入' });
    shareToast(r, '资料' + (d2.photo ? '和照片' : ''));
  };

  const cp = $('#meCopy');
  if (cp) cp.onclick = () => { copyText(meText(save())); toast('资料文本已复制，粘给队长即可', 6000); };
  const ex = $('#meExport');
  if (ex) ex.onclick = () => {
    const d = save();
    download('麦田守望_我的资料_' + (d.name || '未填') + '.json', JSON.stringify(d, null, 1));
    toast('已导出，把这个文件发给队长', 6000);
  };
  const drop = $('#mePhotoDrop'), fi = $('#mePhotoFile');
  if (drop && fi) {
    drop.onclick = () => fi.click();
    fi.onchange = () => { if (fi.files[0]) shrinkPhoto(fi.files[0]); };
  }
  const pd = $('#mePhotoDel');
  if (pd) pd.onclick = () => { const d = meDraft(); delete d.photo; saveMeDraft(d); toast('已删除照片'); render(); };

  const nm = $('#me_name');
  if (nm) nm.onblur = () => { const d = save(); if (d.name) render(); };
}

/** 照片压到 360px、JPEG 0.82，存成 dataURL（几十 KB） */
function shrinkPhoto(file) {
  const fr = new FileReader();
  fr.onload = () => {
    const img = new Image();
    img.onload = () => {
      const max = 360;
      const sc = Math.min(1, max / Math.max(img.width, img.height));
      const cv = document.createElement('canvas');
      cv.width = Math.round(img.width * sc); cv.height = Math.round(img.height * sc);
      cv.getContext('2d').drawImage(img, 0, 0, cv.width, cv.height);
      const url = cv.toDataURL('image/jpeg', 0.82);
      const d = meDraft();
      d.photo = url;
      saveMeDraft(d);
      toast('照片已就绪（' + Math.round(url.length / 1024) + ' KB），记得点「保存资料」', 6000);
      render();
    };
    img.onerror = () => toast('这张图读不了，换一张试试');
    img.src = fr.result;
  };
  fr.readAsDataURL(file);
}

/* ---------------- 赛事名匹配（上报时自动对到已有赛事）---------------- */

/** 归一化：去掉空格、标点、年月日等，方便比对 */
function meetNorm(t) {
  return String(t || '').toLowerCase()
    .replace(/[\s　]/g, '')
    .replace(/[（）()【】\[\]「」《》·,，.。、:：;；!！?？"'”“\-—_/\\|]/g, '')
    .replace(/20\d\d年?/g, '')
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

/* ---------------- 粘贴文本导入（队员上报的文字直接用）---------------- */

let pasteRows = null;

/** 一行一条：姓名,项目,成绩[,日期,赛事/名次]（默认按位置认列，有表头就按表头认） */
function pasteParseText(txt) {
  const rows = [], skip = [];
  const dir = { name: 0, event: 1, res: 2, date: 3, note: 4 };
  String(txt || '').split(/\r?\n/).forEach((line, i) => {
    const t = line.trim();
    if (!t) return;
    const p = t.split(/[\t,，、]+/).map(x => x.trim());
    if (/^麦田守望|成绩上报|上报时间/.test(t)) return;              // 忽略上报文本的标题行
    if (/姓名|名字/.test(p[0] || '')) {                            // 表头行（可能在第一行也可能在后面）
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
    const name = g('name').replace(/[（(].*?[)）]/g, '').replace(/\s+/g, '');
    if (!/^[\u4e00-\u9fa5·a-zA-Z][\u4e00-\u9fa5·a-zA-Z0-9]{1,13}$/.test(name)) { skip.push('第' + (i + 1) + '行姓名看不懂'); return; }
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
  const guestTxt = d.guests ? '，其中 <b>' + d.guests + '</b> 位不在名册（非队员，只进这场榜）' : '';
  const skipTxt = d.skip.length ? '；跳过 ' + d.skip.length + ' 条：' + esc(d.skip.slice(0, 3).join('；')) : '';
  box.innerHTML = `
    <div class="tiny" style="margin:12px 0 8px">解析出 <b>${d.rows.length}</b> 条${guestTxt}${skipTxt}</div>
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

/* ---------------- 收件箱（队员直传的内容，接收后写入本机） ---------------- */

let inboxItems = null;

async function loadInbox() {
  const box = $('#inboxArea');
  if (!box) return;
  const cfg = ghCfg();
  if (!cfg.token) {
    box.innerHTML = '<div class="notice" style="margin-top:12px">先配好访问令牌（上面「数据管理 → 同步」），才能读取收件箱。</div>';
    return;
  }
  box.innerHTML = '<div class="tiny" style="margin-top:12px">正在读取收件箱…</div>';
  try {
    const list = await ghList(cfg, 'data/inbox');
    const files = (list || []).filter(f => f && f.type === 'file' && /\.json$/.test(f.name));
    files.sort((a, b) => a.name < b.name ? 1 : -1);            // 新的在前
    const items = [];
    for (const f of files.slice(0, 30)) {
      try {
        const txt = await ghGetText(cfg, f.path);
        const j = JSON.parse(txt);
        items.push({ path: f.path, sha: f.sha, id: j.id || f.name, at: j.at || '', type: j.type || '', data: j.data || {} });
      } catch (e) { /* 单个读不了就跳过 */ }
    }
    inboxItems = items;
    renderInbox();
  } catch (e) {
    box.innerHTML = '<div class="notice" style="margin-top:12px">读取失败：' + esc(String((e && e.message) || e)) + '</div>';
  }
}

function inboxSummary(it) {
  if (it.type === 'maitian-member') {
    const pb = it.data.pb || {};
    const keys = Object.keys(pb);
    return '队员资料 · ' + esc(it.data.name || '') + (keys.length ? '（' + keys.map(k => esc(k) + ' ' + esc(pb[k])).join('、') + '）' : '')
      + (it.data.photo ? ' · 含照片' : '');
  }
  const rows = (it.data.rows || []);
  const names = rows.slice(0, 3).map(r => esc(r.name)).join('、');
  return '成绩 · ' + rows.length + ' 条：' + names + (rows.length > 3 ? ' 等' : '');
}

function renderInbox() {
  const box = $('#inboxArea');
  if (!box) return;
  const items = inboxItems || [];
  if (!items.length) { box.innerHTML = '<div class="empty" style="margin-top:12px">收件箱是空的</div>'; return; }
  box.innerHTML = `
    <div class="tiny" style="margin:12px 0 8px">待接收 <b>${items.length}</b> 条</div>
    ${items.map((it, i) => `<div class="comp-row" style="cursor:default">
      <div class="l"><div class="t">${inboxSummary(it)}</div>
        <div class="tiny">${esc(String(it.at || '').replace('T', ' ').slice(0, 16))}${it.type === 'maitian-member' ? ' <span class="tagbadge green">资料</span>' : ' <span class="tagbadge wheat">成绩</span>'}</div></div>
      <div style="display:flex;gap:8px;flex:0 0 auto">
        <button class="btn sm" data-inboxok="${i}">接收</button>
        <button class="btn flat sm" data-inboxdel="${i}">丢弃</button>
      </div></div>`).join('')}`;
  $$('[data-inboxok]').forEach(b => b.onclick = () => acceptInbox(+b.dataset.inboxok));
  $$('[data-inboxdel]').forEach(b => b.onclick = () => dropInbox(+b.dataset.inboxdel));
}

async function acceptInbox(i) {
  const it = (inboxItems || [])[i];
  if (!it) return;
  const cfg = ghCfg();
  if (it.type === 'maitian-member') {
    const r = await applyMemberDoc(it.data);
    if (r) toast('已接收「' + r.name + '」的资料：信息 ' + r.info + ' 项、成绩 ' + r.pbs + ' 条' + r.photoNote, 11000);
  } else {
    const rows = (it.data.rows || []).map(r => ({
      uid: newUid(), name: r.name, event: r.event || '5000米',
      sec: r.sec || secFromCell(r.fmt) || 0, fmt: r.fmt || fmtSec(r.sec || 0),
      date: r.date || it.data.date || '', meet: r.meet || '', rank: r.rank || '', ts: Date.now(),
    })).filter(r => r.name && r.sec);
    addMyResults(rows);
    toast('已接收 ' + rows.length + ' 条成绩（在下面「我录入的成绩」里，接着并进某场比赛）', 11000);
  }
  try { if (cfg.token) await ghDelete(cfg, it.path, '接收上报 ' + it.id); } catch (e) { toast('接收了，但收件箱里的这条没删掉：' + String((e && e.message) || e), 9000); }
  inboxItems.splice(i, 1);
  renderInbox(); render();
}

async function dropInbox(i) {
  const it = (inboxItems || [])[i];
  if (!it) return;
  if (!confirm('丢掉这条上报？（会从收件箱里删掉）')) return;
  try { await ghDelete(ghCfg(), it.path, '丢弃上报 ' + it.id); } catch (e) { toast('删不掉：' + String((e && e.message) || e), 9000); return; }
  inboxItems.splice(i, 1); renderInbox(); toast('已丢掉');
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
/* ---------------- 队员资料导入（队长版）---------------- */

/** 文件名用名字的哈希，避免中文文件名 */
function avatarPathFor(name) {
  let h = 0;
  const t = String(name || '');
  for (let i = 0; i < t.length; i++) { h = (h * 31 + t.charCodeAt(i)) % 1000000007; }
  return 'images/avatars/m' + h.toString(36) + '.jpg';
}

function parseMemberDoc(text) {
  const t = String(text || '').trim();
  const out = { pb: {} };
  if (t.charAt(0) === '{') {
    try {
      const j = JSON.parse(t);
      if (j && (j.type === 'maitian-member' || j.name)) return j;
    } catch (e) { /* 不是 JSON 就按文本解析 */ }
  }
  t.split(/\r?\n/).forEach(line => {
    const s2 = line.replace(/^#.*$/, '').trim();
    if (!s2) return;
    const p = s2.split(/[\t:：]+/).map(x => x.trim());
    if (p.length < 2) return;
    const k = p[0], v = p.slice(1).join(' ').trim();
    if (k === '姓名' || k === '名字') out.name = v;
    else if (k === '性别') out.sex = v;
    else if (k === '学院') out.college = v;
    else if (k === '专业' || k === '专业班级') out.major = v;
    else if (k === '年级') out.grade = v;
    else if (ME_PB.indexOf(k) >= 0) out.pb[k] = v;
  });
  if (!out.name && !Object.keys(out.pb).length) return null;
  return out;
}

async function applyMemberDoc(doc) {
  if (!doc || !doc.name) return toast('这份资料里没有姓名，导入不了');
  const o = ovLocal();
  o.memberEdits = o.memberEdits || {};
  const e = o.memberEdits[doc.name] || {};
  ['sex', 'college', 'major', 'grade'].forEach(k => {
    const v = String(doc[k] || '').trim();
    if (v && v !== '无') e[k] = v;
  });
  // 照片：有令牌就直接传成仓库里的头像；没有就先存 dataURL（下次同步一起带上）
  let photoNote = '';
  if (doc.photo && /^data:image\//.test(doc.photo)) {
    const cfg = ghCfg();
    const path = avatarPathFor(doc.name);
    if (cfg.token) {
      try {
        const b64 = doc.photo.split(',')[1];
        await ghPut(cfg, path, b64, '头像：' + doc.name);
        e.photo = path;
        photoNote = '，头像已上传';
      } catch (err) {
        e.photo = doc.photo;
        photoNote = '，头像暂时存在本机（' + String(err.message || err).slice(0, 40) + '）';
      }
    } else {
      e.photo = doc.photo;
      photoNote = '，头像先存本机（配好令牌后重新导入就会传上去）';
    }
  }
  o.memberEdits[doc.name] = e;
  saveLocalOv();

  // 最好成绩：非「无」的进个人最好成绩榜
  const pbs = doc.pb || {};
  const add = [];
  ME_PB.forEach(ev => {
    const v = String(pbs[ev] || '').trim();
    if (!v || v === '无' || v === '-') return;
    const sec = secFromCell(v);
    if (!sec) return;
    add.push({ uid: newUid(), name: doc.name, event: ev, sec: Math.round(sec * 10) / 10,
      fmt: fmtSec(sec), date: '', meet: '队员自报', rank: '', ts: Date.now(),
      sex: e.sex || '', college: e.college || '' });
  });
  if (add.length) {
    o.pbAdded = mergePbAdded(o.pbAdded || [], add);
    saveLocalOv();
  }
  return { name: doc.name, info: ['sex', 'college', 'major', 'grade'].filter(k => e[k]).length,
    pbs: add.length, photo: !!e.photo, photoNote: photoNote };
}

/** 收集表（一行一个人）→ 多份队员资料 */
function parseMemberSheet(rows) {
  if (!rows || !rows.length) return { docs: [], skip: ['文件是空的'] };
  let hIdx = -1;
  for (let i = 0; i < Math.min(rows.length, 8); i++) {
    const line = (rows[i] || []).map(c => String(c == null ? '' : c));
    if (line.some(c => /姓名|名字/.test(c))) { hIdx = i; break; }
  }
  if (hIdx < 0) return { docs: [], skip: ['没找到表头行（要有一列叫「姓名」）'] };
  const head = (rows[hIdx] || []).map(c => String(c == null ? '' : c).trim());
  const colOf = re => { for (let c = 0; c < head.length; c++) if (re.test(head[c])) return c; return -1; };
  const cName = colOf(/姓名|名字/), cSex = colOf(/性别/), cCol = colOf(/学院|院系/),
    cMaj = colOf(/专业/), cGrd = colOf(/年级/);
  const pbCols = {};
  ME_PB.forEach(ev => { for (let c = 0; c < head.length; c++) if (head[c].indexOf(ev) >= 0) { pbCols[ev] = c; break; } });
  const docs = [], skip = [];
  rows.slice(hIdx + 1).forEach((r, i) => {
    if (!r || !r.some(c => c !== '' && c != null)) return;
    const g = c => (c >= 0 && r[c] != null) ? String(r[c]).trim() : '';
    const name = g(cName).replace(/[（(].*?[)）]/g, '').replace(/\s+/g, '');
    if (!/^[\u4e00-\u9fa5·a-zA-Z][\u4e00-\u9fa5·a-zA-Z0-9]{1,13}$/.test(name)) { skip.push('第 ' + (hIdx + 2 + i) + ' 行：姓名「' + g(cName).slice(0, 8) + '」看不懂'); return; }
    const pb = {};
    ME_PB.forEach(ev => { const v = g(pbCols[ev]); pb[ev] = v || '无'; });
    docs.push({ type: 'maitian-member', name: name, sex: g(cSex), college: g(cCol),
      major: g(cMaj), grade: g(cGrd), pb: pb, source: '收集表' });
  });
  return { docs: docs, skip: skip };
}

let docSheetQueue = null;

function renderSheetPreview() {
  const box = $('#docSheetArea');
  if (!box) return;
  const q = docSheetQueue;
  if (!q) { box.innerHTML = ''; return; }
  const mem = new Set(rosterList().map(m => m.name));
  const shown = q.docs.slice(0, 12);
  box.innerHTML = `
    <div class="notice" style="margin-top:12px">
      收集表里读到 <b>${q.docs.length}</b> 个人${q.skip.length ? '，跳过 ' + q.skip.length + ' 行' + (q.skip.length ? '（' + esc(q.skip.slice(0, 3).join('；')) + '）' : '') : ''}；
      其中 <b>${q.docs.filter(d => !mem.has(d.name)).length}</b> 位名册里没有（会新增）。
    </div>
    <div class="tbl-wrap" style="max-height:240px;overflow:auto;margin-top:10px">
      <table class="tbl" style="min-width:auto">
        <thead><tr><th class="no-sort">姓名</th><th class="no-sort hide-sm">性别</th>
          <th class="no-sort hide-sm">学院</th><th class="no-sort">会有成绩项</th><th class="no-sort">在名册</th></tr></thead>
        <tbody>${shown.map(d => {
          const pbs = ME_PB.filter(ev => d.pb[ev] && d.pb[ev] !== '无');
          return `<tr><td><b>${esc(d.name)}</b></td><td class="tiny hide-sm">${esc(d.sex || '')}</td>
            <td class="tiny hide-sm">${esc(d.college || '')}</td>
            <td class="tiny">${pbs.length ? pbs.map(ev => esc(ev) + ' ' + esc(d.pb[ev])).join('、') : '（全填无）'}</td>
            <td>${mem.has(d.name) ? '<span class="tagbadge green">在</span>' : '<span class="tagbadge">新增</span>'}</td></tr>`;
        }).join('')}</tbody>
      </table>
    </div>
    ${q.docs.length > 12 ? `<div class="tiny">（只预览前 12 位，导入时会全部处理）</div>` : ''}
    <div class="chips" style="margin-top:12px">
      <button class="btn" id="btnSheetDo">全部导入这 ${q.docs.length} 位</button>
      <button class="btn flat sm" id="btnSheetCancel">取消</button>
    </div>`;
  const no = $('#btnSheetCancel'), ok = $('#btnSheetDo');
  if (no) no.onclick = () => { docSheetQueue = null; render(); };
  if (ok) ok.onclick = async () => {
    ok.disabled = true; ok.textContent = '导入中…';
    let added = 0, updated = 0, pbs = 0;
    for (const d of q.docs) {
      const before = (ovLocal().memberEdits || {})[d.name];
      const r = await applyMemberDoc(d);
      if (r) { pbs += r.pbs || 0; if (before) updated++; else added++; }
    }
    docSheetQueue = null;
    toast('收集表导入完成：名册更新 ' + updated + ' 人、新增 ' + added + ' 人、最好成绩 ' + pbs + ' 条。'
      + '记得点「同步我的修改到线上」', 12000);
    render();
  };
}

/** 读收集表文件（Excel/CSV）→ 预览 */
function readSheetFile(file) {
  const isCsv = /\.csv$/i.test(file.name || '');
  const fr = new FileReader();
  fr.onload = (e) => {
    try {
      const buf = new Uint8Array(e.target.result);
      let wb;
      if (isCsv) {
        let txt;
        try { txt = new TextDecoder('utf-8', { fatal: true }).decode(buf); }
        catch (err) { try { txt = new TextDecoder('gbk').decode(buf); } catch (e2) { txt = new TextDecoder('utf-8').decode(buf); } }
        wb = XLSX.read(txt.replace(/^\ufeff/, ''), { type: 'string', raw: true });
      } else {
        wb = XLSX.read(buf, { type: 'array' });
      }
      const first = XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], { header: 1, raw: true, defval: '' });
      const r = parseMemberSheet(first);
      if (!r.docs.length) return toast('没读出行：' + (r.skip[0] || '检查一下表头有没有「姓名」列'), 9000);
      docSheetQueue = r;
      toast('已读取 ' + file.name + '：' + r.docs.length + ' 位，确认下面这份再点导入');
      renderSheetPreview();
    } catch (err) { toast('这个文件读不了：' + (err && err.message), 9000); }
  };
  fr.readAsArrayBuffer(file);
}

function renderMemberDocPreview() {
  const box = $('#docAreaTop') || $('#docArea');   // 上传页 / 名册页各有一个位置
  if (!box) return;
  const d = memberDocQueue;
  if (!d) { box.innerHTML = ''; return; }
  const memNames = new Set(rosterList().map(m => m.name));
  const pbRows = Object.keys(d.doc.pb || {}).filter(k => d.doc.pb[k] && d.doc.pb[k] !== '无');
  box.innerHTML = `
    <div class="notice" style="margin-top:12px">
      <b>${esc(d.doc.name)}</b>　${memNames.has(d.doc.name) ? '<span class="tagbadge green">在名册里</span>' : '<span class="tagbadge">名册里没有 → 会新增一位</span>'}<br>
      信息：${['sex', 'college', 'major', 'grade'].filter(k => d.doc[k]).map(k => esc(d.doc[k])).join(' / ') || '（没填）'}<br>
      最好成绩：${pbRows.length ? pbRows.map(k => esc(k) + ' ' + esc(d.doc.pb[k])).join('　') : '（全填了无）'}<br>
      照片：${d.doc.photo ? '有（' + Math.round(String(d.doc.photo).length / 1024) + ' KB）' : '没有'}
    </div>
    <div class="chips" style="margin-top:10px">
      <button class="btn" id="btnDocApply">导入这份资料</button>
      <button class="btn flat sm" id="btnDocCancel">取消</button>
    </div>`;
  const a = $('#btnDocApply'), c2 = $('#btnDocCancel');
  if (c2) c2.onclick = () => { memberDocQueue = null; render(); };
  if (a) a.onclick = async () => {
    a.disabled = true; a.textContent = '导入中…';
    const r = await applyMemberDoc(d.doc);
    memberDocQueue = null;
    render();
    if (r) toast('已导入「' + r.name + '」：信息 ' + r.info + ' 项、最好成绩 ' + r.pbs + ' 条' + r.photoNote, 10000);
  };
}

let memberDocQueue = null;

function addCompRecords(compId, recs) {
  const l = ovLocal();
  l.compRecords = l.compRecords || {};
  l.compRecords[compId] = (l.compRecords[compId] || []).concat(recs);
  saveLocalOv();
  return l;
}
/**
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
  // 「完善队员信息」表的值优先级更高：同一个人的两个编辑区同时存在时，以补全表填的为准
  // （只覆盖非空值，避免补全表里空着的一项把列表里已有的内容清掉）
  const fByName = {};
  $$('[data-fme]').forEach(el => {
    const n = el.dataset.fme, f = el.dataset.mf;
    fByName[n] = fByName[n] || {};
    fByName[n][f] = el.value;
  });
  Object.entries(fByName).forEach(([n, f]) => {
    const prev = edits[n] || (edits[n] = {});
    FILL_FIELDS.forEach(k => {
      if (f[k] !== undefined && String(f[k]).trim() !== '') prev[k] = String(f[k]).trim();
    });
  });
  const fByUid = {};
  $$('[data-fmuid]').forEach(el => {
    const u = el.dataset.fmuid, f = el.dataset.mf;
    fByUid[u] = fByUid[u] || {};
    fByUid[u][f] = el.value;
  });
  Object.entries(fByUid).forEach(([u, f]) => {
    const nm = (l.newMembers || []).find(m => (m.uid || m.name) === u);
    if (!nm) return;
    FILL_FIELDS.forEach(k => {
      if (f[k] !== undefined && String(f[k]).trim() !== '') nm[k] = String(f[k]).trim();
    });
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
        const k = isNewMember(m) ? ('data-fmuid="' + esc(m.uid || m.name) + '"') : ('data-fme="' + esc(m.name) + '"');
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
  // 默认按位置认列：姓名,性别,学院,专业,年级；第一行是表头时再按表头认列
  const dir = { name: 0, sex: 1, college: 2, major: 3, grade: 4 };
  String(txt || '').split(/\r?\n/).forEach((line, i) => {
    const t = line.trim();
    if (!t) return;
    const p = t.split(/[\t,，、]+/).map(x => x.trim());
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
  const skipTxt = d.skip.length ? '；跳过 ' + d.skip.length + ' 条：' + esc(d.skip.slice(0, 3).join('；')) : '';
  box.innerHTML = `
    <div class="tiny" style="margin:12px 0 8px">
      解析出 <b>${d.rows.length}</b> 行，其中 <b>${d.matched}</b> 行能在名册里找到人${skipTxt}</div>
    <div class="tbl-wrap" style="max-height:280px;overflow:auto">
      <table class="tbl" style="min-width:auto"><thead><tr>
        <th class="no-sort">姓名</th><th class="no-sort">要补的</th><th class="no-sort hide-sm">说明</th>
      </tr></thead><tbody>
      ${d.rows.slice(0, 80).map(r => `<tr>
        <td><b>${esc(r.name)}</b>${r._hit ? '' : '<span class="tiny" style="color:#c0392b;margin-left:6px">不在名册里</span>'}</td>
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

function pendingCount() {
  const l = LOCAL_OV || {};
  let n = 0;
  if (l.team && Object.keys(l.team).length) n += Object.keys(l.team).length;
  if (l.honors) n += 1;
  if (l.activities) n += 1;
  if (l.hidden && l.hidden.length) n += l.hidden.length;
  if (l.memberEdits) n += Object.keys(l.memberEdits).length;
  if (l.newMembers && l.newMembers.length) n += l.newMembers.length;
  if (l.results && l.results.length) n += l.results.length;
  if (l.photos && l.photos.length) n += l.photos.length;
  if (l.competitions && l.competitions.length) n += l.competitions.length;
  if (l.compRecords) n += Object.keys(l.compRecords).reduce((a, k) => a + l.compRecords[k].length, 0);
  if (l.hiddenRecords && l.hiddenRecords.length) n += l.hiddenRecords.length;
  if (l.pbAdded) n += l.pbAdded.length;
  if (l.pbHidden) n += l.pbHidden.length;
  if (l.hall) n += 1;
  if (l.queue) n += 1;
  return n;
}
function saveLocalOv() {
  LOCAL_OV = LOCAL_OV || {};
  return lsSet(LS_LOCAL, LOCAL_OV);
}

const GH_DEF = { owner: 'zl4639574-bit', repo: 'maitian-running', branch: 'master' };
/** 读同步配置：没填的用默认值补齐，避免"未填写"卡住 */
function ghCfg() {
  const c = lsGet(LS_CFG, {}) || {};
  return { owner: c.owner || GH_DEF.owner, repo: c.repo || GH_DEF.repo,
           branch: c.branch || GH_DEF.branch, token: c.token || '' };
}

/* ---------------- 队员数据表：导出 / 改好导回（批量修正） ---------------- */

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
  // 返回 [] = 明确"不进公开名册"；返回 null = 这个值看不懂（例如「队员」），保持原样别动
  const normLevel = v => {
    const t = String(v == null ? '' : v).trim();
    if (!t || t === '未分级' || t === '-' || t === '无' || t === '否' || t === '0') return [];
    const hit = t.split(/[,，、+/]/).map(x => x.trim()).filter(x => x === '正式' || x === '预备');
    return hit.length ? hit : null;
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
      if (info.level && !sameLv(cur.level, info.level)) diff.push('身份');
      if (info.level === null) delete info.level;          // 看不懂就不改身份
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
        const comp = comps.filter(c => c.id === cid)[0] || {};
        const expDate = orig.date || comp.date || '';            // 导出时写进"日期"列的值
        const expNote = orig.rank || orig.note || '';            // 导出时写进"名次/备注"列的值
        if (Math.abs(sec - oldSec) > 0.05 || (ev && String(ev) !== String(orig.event || ''))
            || String(date) !== String(expDate) || String(note) !== String(expNote)) {
          plan.recFix.push({
            cid: cid, hideKey: cid + '|' + name + '|' + oldSec,
            desc: name + ' ' + (orig.event || '') + ' ' + (orig.fmt || fmtSec(orig.sec))
                  + ' → ' + (ev || orig.event) + ' ' + fmtSec(sec),
            rec: { name: name, event: ev || orig.event, raw: rawRes, sec: sec, fmt: fmtSec(sec),
                   sex: orig.sex || '', college: orig.college || '',
                   date: (date && String(date) !== String(expDate)) ? date : (orig.date || ''),
                   note: (note && String(note) !== String(expNote)) ? note : (orig.note || orig.rank || ''), keep: true },
          });
        }
        return;
      }
      if (key.indexOf('res:') === 0) {
        const uid = key.slice(4);
        const allRes = (ov().results || []);
        const cur = allRes.find(r => (r.uid || (r.name + '|' + r.sec)) === uid);
        if (!cur) { plan.skip.push('找不到自由成绩：' + name); return; }
        const inLocal = (ovLocal().results || []).some(r => (r.uid || (r.name + '|' + r.sec)) === uid);
        if (!inLocal) cur._cloud = true;            // 云端发布过的：改/删都靠 hiddenResults
        if (isDel) { plan.recDel.push({ uid: uid, desc: name + ' ' + (cur.event || '') + ' ' + (cur.fmt || fmtSec(cur.sec)), cloud: !inLocal }); return; }
        if (sec && (Math.abs(sec - Number(cur.sec)) > 0.05 || (ev && String(ev) !== String(cur.event || ''))
            || String(date) !== String(cur.date || ''))) {
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
    const info = Object.assign({}, x.info);
    if (!info.level || !info.level.length) info.level = ['正式'];
    l.newMembers.push(Object.assign({ uid: nmUid(), name: x.name, addedAt: new Date().toISOString().slice(0, 10) }, info));
  });
  p.recHide.forEach(x => { l.hiddenRecords.push(x.hideKey); });
  p.recFix.forEach(x => {
    l.hiddenRecords.push(x.hideKey);
    (l.compRecords[x.cid] = l.compRecords[x.cid] || []).push(x.rec);
  });
  p.recDel.forEach(x => {
    l.results = (l.results || []).filter(r => (r.uid || (r.name + '|' + r.sec)) !== x.uid);
    if (x.cloud) l.hiddenResults = (l.hiddenResults || []).concat([x.uid]);      // 云端那条也要屏蔽
  });
  p.recEdit.forEach(x => {
    let hit = (l.results = l.results || []);
    let found = false;
    hit.forEach(r => { if ((r.uid || (r.name + '|' + r.sec)) === x.uid) { Object.assign(r, x.rec); found = true; } });
    if (!found) {                                    // 改的是云端那条 → 屏蔽旧的 + 本机加新的
      l.hiddenResults = (l.hiddenResults || []).concat([x.uid]);
      l.results.push(x.rec);
    }
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

/* ---------------- 批量添加队员：粘贴表格或选文件 → 解析预览 → 一次入库 ---------------- */

let nmBatchRows = null;
function nmUid() { return 'nm' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }
const NM_COLS = [['name', /姓名|名字|人员|队员/], ['college', /学院|院系/], ['major', /专业|班级/],
                 ['grade', /年级|入学|届/], ['sex', /性别/], ['level', /身份|级别|状态/]];

function parseRosterText(txt) {
  const lines = String(txt || '').split(/\r?\n/).map(x => x.trim()).filter(Boolean);
  if (!lines.length) return { rows: [], skip: [] };
  const splitLine = (l) => l.indexOf('\t') >= 0 ? l.split('\t')
                        : (l.indexOf(',') >= 0 || l.indexOf('，') >= 0 ? l.split(/[,，]/) : l.split(/\s+/));
  let rows = lines.map(splitLine);
  const head = rows[0].map(x => String(x).trim());
  let map;
  if (/姓名|名字|人员|队员/.test(head.join(' '))) {          // 第一行是表头 → 按表头认列
    map = {};
    NM_COLS.forEach(([k, re]) => { const i = head.findIndex(h => re.test(h)); if (i >= 0) map[k] = i; });
    rows = rows.slice(1);
  } else {                                                   // 没表头 → 用默认顺序
    map = { name: 0, college: 1, major: 2, grade: 3, sex: 4, level: 5 };
  }
  const out = [], skip = [], same = [], seenRow = new Set();
  const existing = new Set([].concat((BASE.roster || []).map(m => m.name), (rosterList().map(m => m.name))));
  rows.forEach((r, li) => {
    const get = (k) => (map[k] == null || r[map[k]] == null) ? '' : String(r[map[k]]).trim();
    const nm = get('name').replace(/\s/g, '');
    if (!nm) return;
    if (!/^[\u4e00-\u9fa5·]{2,6}$/.test(nm)) { skip.push('第' + (li + 1) + '行「' + nm.slice(0, 10) + '」姓名不规范'); return; }
    const rowKey = [nm, get('college'), get('major'), get('grade')].join('|');
    if (seenRow.has(rowKey)) { skip.push('第' + (li + 1) + '行「' + nm + '」与本批前面某行完全相同'); return; }
    seenRow.add(rowKey);
    if (existing.has(nm)) same.push(nm);            // 同名的照加，只做个提醒
    let lv = get('level').split(/[,，、/]/).map(x => x.trim()).filter(x => x === '正式' || x === '预备');
    if (!lv.length) lv = ['正式'];
    const sx = get('sex');
    out.push({
      uid: nmUid(),
      name: nm, college: get('college'), major: get('major'), grade: get('grade'),
      sex: /男/.test(sx) ? '男' : (/女/.test(sx) ? '女' : ''),
      level: lv, addedAt: new Date().toISOString().slice(0, 10),
    });
  });
  return { rows: out, skip: skip, same: same };
}

/** 单独录入的个人最好成绩：云端 + 本机（去掉已删的） */
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
  String(txt || '').split(/\r?\n/).forEach((line, i) => {
    const t = line.trim();
    if (!t) return;
    const p = t.split(/[\t,，、]+/).map(x => x.trim());
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
  const skipTxt = d.skip.length ? '；跳过 ' + d.skip.length + ' 条：' + esc(d.skip.slice(0, 3).join('；')) : '';
  box.innerHTML = `
    <div class="tiny" style="margin:12px 0 8px">解析出 <b>${d.rows.length}</b> 条${skipTxt}</div>
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

function renderNmBatch() {
  const box = $('#nmBatchBox');
  if (!box) return;
  const data = nmBatchRows || { rows: [], skip: [], same: [] };
  if (!data.rows.length) {
    box.innerHTML = '<div class="notice" style="margin-top:12px">没解析出可用的人'
      + (data.skip.length ? '：' + esc(data.skip.slice(0, 3).join('；')) + (data.skip.length > 3 ? ' 等' : '') : '')
      + '。检查一下粘贴的内容（至少要有一列姓名）。</div>';
    return;
  }
  box.innerHTML = `
    <div class="tiny" style="margin:12px 0 8px">
      解析出 <b>${data.rows.length}</b> 人${data.skip.length ? '；跳过 ' + data.skip.length + ' 条：' + esc(data.skip.slice(0, 3).join('；')) + (data.skip.length > 3 ? ' 等' : '') : ''}
      ${(data.same || []).length ? '；其中 <b>' + data.same.length + '</b> 人与名册里现有的人同名（同名可以并存，若其实是同一人，加入后到列表里删掉即可）' : ''}
      ${ghCfg().token ? '。点下面按钮一次加入，再去「同步」发布。' : '。点下面按钮加入本机，然后去「同步」配好令牌再发布。'}
    </div>
    <div class="tbl-wrap" style="max-height:300px;overflow:auto">
      <table class="tbl" style="min-width:auto"><thead><tr>
        <th class="no-sort">姓名</th><th class="no-sort hide-sm">学院</th><th class="no-sort hide-sm">专业</th>
        <th class="no-sort hide-sm">年级</th><th class="no-sort hide-sm">性别</th><th class="no-sort">身份</th>
      </tr></thead><tbody>
      ${data.rows.slice(0, 80).map(r => `<tr><td><b>${esc(r.name)}</b></td>
        <td class="tiny hide-sm">${esc(r.college)}</td><td class="tiny hide-sm">${esc(r.major)}</td>
        <td class="tiny hide-sm">${esc(r.grade)}</td><td class="tiny hide-sm">${esc(r.sex)}</td>
        <td class="tiny">${esc(r.level.join('+'))}</td></tr>`).join('')}
      </tbody></table>
    </div>
    <div class="chips" style="margin-top:12px">
      <button class="btn" id="btnNmConfirm">把这 ${data.rows.length} 人加入名册</button>
      <button class="btn ghost" id="btnNmCancel">取消</button>
    </div>`;
  const ok = $('#btnNmConfirm'), no = $('#btnNmCancel');
  if (no) no.onclick = () => { nmBatchRows = null; render(); };
  if (ok) ok.onclick = () => {
    const l = ovLocal();
    l.newMembers = l.newMembers || [];
    let added = 0;
    const dupSame = [];
    data.rows.forEach(r => {
      if (l.newMembers.some(m => (m.uid || m.name) === (r.uid || r.name)
            || (m.name === r.name && (m.college || '') === (r.college || '') && (m.major || '') === (r.major || '')))) {
        dupSame.push(r.name); return;               // 完全一样的人（防手抖重复加入）
      }
      if (!r.uid) r.uid = nmUid();
      l.newMembers.push(r); added++;
    });
    saveLocalOv();
    nmBatchRows = null;
    state.mRosterQ = '';
    toast('已把 ' + added + ' 人加进名册'
          + (dupSame.length ? '（' + dupSame.length + ' 人之前已经加过，跳过：' + dupSame.slice(0, 3).join('、') + '）' : '')
          + ' —— 记得点「同步我的修改到线上」发布', 11000);
    render();
  };
}

function bindManage() {

  $$('[data-unhide]').forEach(b => b.onclick = () => {
    const n = b.dataset.unhide;
    const l = ovLocal();
    l.shown = Array.from(new Set((l.shown || []).concat([n])));
    if ((l.hidden || []).indexOf(n) >= 0) l.hidden = l.hidden.filter(x => x !== n);
    saveLocalOv();
    toast('已恢复显示「' + n + '」：他会出现回名册里。记得点「同步我的修改到线上」', 11000);
    render();
  });

  const sF = $('#docSheetFile'), sI = $('#btnDocSheet');
  if (sI && sF) sI.onclick = () => sF.click();
  if (sF) sF.onchange = () => { const f = sF.files[0]; sF.value = ''; if (f) readSheetFile(f); };

  const dF = $('#docFile'), dI = $('#btnDocImport');
  if (dI && dF) dI.onclick = () => dF.click();
  if (dF) dF.onchange = () => {
    const f = dF.files[0];
    dF.value = '';
    if (!f) return;
    const fr = new FileReader();
    fr.onload = () => {
      const doc = parseMemberDoc(fr.result);
      if (!doc) return toast('没看懂这份资料：应该包含「姓名」和各项成绩');
      memberDocQueue = { doc: doc };
      toast('已读取 ' + f.name + '，确认下面这份就点导入');
      renderMemberDocPreview();
    };
    fr.readAsText(f);
  };
  const dP = $('#btnDocParse');
  if (dP) dP.onclick = () => {
    const ta = $('#docText');
    const doc = parseMemberDoc(ta ? ta.value : '');
    if (!doc) return toast('没看懂：每行写成「字段 值」，比如 姓名 张三');
    memberDocQueue = { doc: doc };
    renderMemberDocPreview();
  };
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

  const bChk = $('#btnTokenCheck');
  if (bChk) bChk.onclick = checkToken;

  const rSv = $('#btnRelaySave');
  if (rSv) rSv.onclick = () => {
    const l = ovLocal();
    const url = ($('#rlUrl') || {}).value ? $('#rlUrl').value.trim() : '';
    const code = ($('#rlCode') || {}).value ? $('#rlCode').value.trim() : '';
    if (!url) { delete l.relay; } else { l.relay = { url: url, code: code }; }
    saveLocalOv();
    toast(url ? '已保存收件设置（记得点「同步我的修改到线上」队员端才会生效）' : '已清空收件设置', 9000);
  };
  const rTs = $('#btnRelayTest');
  if (rTs) rTs.onclick = async () => {
    rTs.disabled = true; rTs.textContent = '测试中…';
    const l = ovLocal();
    const url = ($('#rlUrl') || {}).value ? $('#rlUrl').value.trim() : '';
    const code = ($('#rlCode') || {}).value ? $('#rlCode').value.trim() : '';
    l.relay = { url: url, code: code }; saveLocalOv();
    const res = await postToRelay('scores', { date: todayStr(), rows: [{ name: '连接测试', event: '5000米', fmt: '20:00', date: todayStr(), meet: '中转测试' }] });
    rTs.disabled = false; rTs.textContent = '测试收件服务';
    toast(res.ok ? '收件服务正常 ✅ 手机上也能直接提交了（这条测试去收件箱丢掉即可）' : ('收件服务不通：' + res.error), 12000);
  };

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
    const n = saveRosterEdits();
    toast('名册修改已保存（' + n + ' 人）—— 记得点「同步我的修改到线上」发布', 9000);
    render();
  };
  $$('[data-muiddel]').forEach(b => b.onclick = () => {
    const u = b.dataset.muiddel, l = ovLocal();
    l.newMembers = (l.newMembers || []).filter(m => (m.uid || m.name) !== u);
    saveLocalOv(); toast('已删除这个新增队员'); render();
  });
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
  const rsy = $('#btnRosterSync');
  if (rsy) rsy.onclick = () => pushToGitHub();
  // —— 单独添加个人最好成绩 ——
  const addPb = $('#btnAddPb');
  if (addPb) addPb.onclick = () => {
    const name = ($('#pb_name').value || '').trim().replace(/\s/g, '');
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
  const bfl = $('#btnFillList');
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
  });
  const am = $('#btnAddMember');
  if (am) am.onclick = () => {
    const name = ($('#nm_name').value || '').trim().replace(/\s/g, '');
    if (!name) return toast('请填姓名');
    if (!/^[\u4e00-\u9fa5·]{2,6}$/.test(name)) return toast('姓名请填 2~6 个汉字');
    const l = ovLocal();
    l.newMembers = l.newMembers || [];
    const doAdd = (note) => {
      l.newMembers.push({
        uid: nmUid(),
        name,
        sex: $('#nm_sex').value,
        college: ($('#nm_college').value || '').trim(),
        major: ($('#nm_major').value || '').trim(),
        grade: ($('#nm_grade').value || '').trim(),
        level: $('#nm_level').value.split(',').map(x => x.trim()).filter(Boolean),
        addedAt: new Date().toISOString().slice(0, 10),
      });
      saveLocalOv();
      toast('已把 ' + name + ' 加进名册' + (note || '') + ' —— 记得点「同步我的修改到线上」发布', 8000);
      render();
    };
    const base = (BASE.roster || []).find(m => m.name === name);
    const vis = base && (base.level || []).some(x => x === '正式' || x === '预备');
    const dupNew = l.newMembers.some(m => m.name === name);
    if (base || dupNew) {
      const box = $('#nmAddBox');
      const why = base
        ? (vis
            ? '「' + name + '」已经在名册里了（' + esc(base.college || '未填学院') + '，身份 ' + esc((base.level || []).join('/') || '未分级') + '）。'
            : '「' + name + '」<b>在原始名册里，但身份是「' + esc((base.level || []).join('/') || '未分级') + '」</b>，'
              + '而展示版只显示「正式 / 预备」，所以他没出现在公开名册里 —— 不是没录进来，是身份没定。')
        : '你已经加过一个叫「' + name + '」的人了（同名可以并存，确认不是同一个人就继续）。';
      if (box) {
        box.innerHTML = '<div class="notice" style="margin-top:12px">' + why
          + ((base && !vis) ? '<br><br>👉 想让他出现在公开名册：点「搜出来改他的身份」，把那个人的「身份」改成 正式 或 预备，'
                             + '再点「保存名册修改」（不用新加一个人，也不用同步两次）。' : '')
          + '<div class="chips" style="margin-top:10px">'
          + ((base && !vis) ? '<button class="btn sm" id="btnNmFindIt">搜出来改他的身份</button>' : '')
          + '<button class="btn ghost sm" id="btnNmForce">是另一个人，仍然添加</button></div></div>';
        const b1 = $('#btnNmFindIt'), b2 = $('#btnNmForce');
        if (b1) b1.onclick = () => { state.mRosterQ = name; render(); };
        if (b2) b2.onclick = () => { am.dataset.force = '1'; am.click(); };
      }
      if (am.dataset.force !== '1') return;
      delete am.dataset.force;
    }
    doAdd(dupNew ? '（同名，已有 ' + l.newMembers.filter(m => m.name === name).length + ' 个同名的人）' : '');
  };
  const dte = $('#btnDtExport');
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
  const nbp = $('#btnNmPreview');
  if (nbp) nbp.onclick = () => {
    nmBatchRows = parseRosterText($('#nmBatch').value);
    renderNmBatch();
  };
  const nbf = $('#btnNmFile'), nbfi = $('#nmFileInput');
  if (nbf && nbfi) {
    nbf.onclick = () => nbfi.click();
    nbfi.onchange = () => {
      const f = nbfi.files && nbfi.files[0];
      if (!f) return;
      const fr = new FileReader();
      fr.onerror = () => toast('文件读不出来，换一个试试', 8000);
      fr.onload = () => {
        try {
          const wb = XLSX.read(new Uint8Array(fr.result), { type: 'array' });
          const ws = wb.Sheets[wb.SheetNames[0]];
          const aoa = XLSX.utils.sheet_to_json(ws, { header: 1, raw: false, defval: '' });
          const txt = aoa.map(r => r.map(c => String(c == null ? '' : c).trim()).join('\t')).join('\n');
          $('#nmBatch').value = txt.slice(0, 30000);
          nmBatchRows = parseRosterText(txt);
          renderNmBatch();
        } catch (e) {
          toast('这个文件读不出来：' + String((e && e.message) || e).slice(0, 40), 9000);
        }
      };
      fr.readAsArrayBuffer(f);
    };
  }
  const mq = $('#mRosterQ');
  if (mq) mq.oninput = () => {
    if (window._imeOn) return;                    // 拼音组词中，不检索
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
  const cfg = ghCfg();
  const direct = !!cfg.token;                 // 有令牌：压完直接传线上，不占本机那 5MB
  const l = ovLocal();
  l.photos = l.photos || [];
  let ok = 0, skipped = 0, full = 0;
  const bad = [];
  let seen = 0;
  const finish = () => {
    seen++;
    if (seen < list.length) return;
    render();
    const parts = [];
    if (ok) parts.push('已加入 ' + ok + ' 张到「' + album + '」' + (direct ? '（已直接传到线上，再点「同步」照片墙就显示）' : '（待同步）'));
    if (bad.length) parts.push(bad.length + ' 张打不开被跳过：' + bad.slice(0, 2).join('、') + (bad.length > 2 ? ' 等' : '')
      + ' —— iPhone 的 HEIC 格式浏览器认不了，先在手机相册里转成 JPG（或微信发给自己会自动转码）再传');
    if (full) parts.push(full + ' 张没存住：本机存储满了，先点「同步」把已有照片传到线上腾出空间');
    if (skipped) parts.push(skipped + ' 个文件不是图片，已跳过');
    toast(parts.join('；') || '没有可用的图片', 12000);
  };
  list.forEach((f, i) => {
    if (!/^image\//.test(f.type) && !/\.(jpe?g|png|webp|gif|bmp|heic|heif)$/i.test(f.name)) { skipped++; finish(); return; }
    const img = new Image();
    const fr = new FileReader();
    fr.onerror = () => { bad.push(f.name); finish(); };
    fr.onload = () => {
      img.onerror = () => { bad.push(f.name); finish(); };       // HEIC 等解不开的格式走这里
      img.onload = async () => {
        try {
          const MAX = 1500;
          let w = img.width, h = img.height;
          if (w > MAX) { h = Math.round(h * MAX / w); w = MAX; }
          const cv = document.createElement('canvas');
          cv.width = w; cv.height = h;
          cv.getContext('2d').drawImage(img, 0, 0, w, h);
          const data = cv.toDataURL('image/jpeg', 0.8);
          const rec = {
            album, albumDate: (album.match(/\d{4}/) || [todayStr().slice(0, 4)])[0],
            file: 'up_' + Date.now() + '_' + i + '.jpg',
            caption: f.name.replace(/\.[^.]+$/, '').slice(0, 18),
            size: Math.round(data.length * 0.75),
          };
          if (direct) {
            await ghPut(cfg, 'images/' + rec.file, String(data).split(',')[1],
                        '上传照片 ' + album + ' / ' + rec.file);
            PHOTO_PREVIEW[rec.file] = data;        // 本机先能预览
            l.photos.push(rec);                    // 只存元数据（很小）
            saveLocalOv();
          } else {
            l.photos.push(Object.assign({ data }, rec));
            if (!saveLocalOv()) { l.photos.pop(); full++; finish(); return; }   // 没存住就回退，别骗人
          }
          ok++;
        } catch (e) {
          bad.push(f.name + '（' + String((e && e.message) || e).slice(0, 24) + '）');
        }
        finish();
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

/** 把 GitHub 返回的状态码翻成中文提示（读写共用） */
function ghHint(status) {
  return (status === 401) ? '｜令牌无效或已过期：重新生成一个再粘一次'
    : (status === 403) ? '｜权限不够：令牌的 Contents 要选 Read and write（或访问太频繁，稍等再试）'
      : (status === 404) ? '｜仓库名/分支名不对，或这个令牌没有该仓库的权限（最常见：自己还没被加为协作者）'
        : (status === 409) ? '｜文件刚好被别处改过，等 10 秒重试一次即可'
          : (status === 0) ? '｜网络不通：检查一下系统代理（开 Clash 就点「打开」，关了就点「关闭」）' : '';
}

/** 列出某个目录（收件箱用） */
async function ghList(cfg, dir) {
  const r = await fetch(`${GH}/repos/${cfg.owner}/${cfg.repo}/contents/${encodeURI(dir)}?ref=${encodeURIComponent(cfg.branch || 'master')}`, { headers: ghHeaders(cfg), cache: 'no-store' });
  if (r.status === 404) return [];                       // 目录还不存在 = 空
  if (!r.ok) throw new Error('读取 ' + dir + ' 失败 ' + r.status + ghHint(r.status));
  const j = await r.json();
  return Array.isArray(j) ? j : [];
}

/** 删除仓库里的某个文件（接收完的上报就删掉） */
async function ghDelete(cfg, path, message) {
  const sha = await ghGetSha(cfg, path);
  if (!sha) return true;
  const r = await fetch(`${GH}/repos/${cfg.owner}/${cfg.repo}/contents/${encodeURI(path)}`, {
    method: 'DELETE', headers: ghHeaders(cfg),
    body: JSON.stringify({ message: message || ('删除 ' + path), sha: sha, branch: cfg.branch || 'master' }),
  });
  if (!r.ok) throw new Error('删除 ' + path + ' 失败 ' + r.status);
  return true;
}

/** 中转配置（队员端靠它直传；存在 overrides.js 里同步下去，不含任何令牌） */
function relayCfg() {
  const r = ov().relay;
  return (r && String(r.url || '').trim()) ? { url: String(r.url).trim(), code: String(r.code || '') } : null;
}

/** 提交到中转（队员端用）。用 text/plain 发，避免浏览器跨域预检（函数 URL / API 网关都可能不支持 OPTIONS）。返回 {ok, error} */
async function postToRelay(type, payload) {
  const rc = relayCfg();
  if (!rc) return { ok: false, error: '队长还没配置收件地址' };
  try {
    const ac = (typeof AbortController !== 'undefined') ? new AbortController() : null;
    const timer = ac ? setTimeout(() => ac.abort(), 25000) : null;
    const r = await fetch(rc.url, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain;charset=UTF-8' },   // 故意用 text/plain：简单请求，不触发预检
      body: JSON.stringify({ code: rc.code, type: type, payload: payload }),
      signal: ac ? ac.signal : undefined,
    });
    if (timer) clearTimeout(timer);
    const j = await r.json().catch(() => ({}));
    if (r.ok && j && j.ok) return { ok: true, id: j.id };
    return { ok: false, error: (j && j.error) || ('提交失败 ' + r.status) };
  } catch (e) {
    const msg = String((e && e.message) || e);
    return { ok: false, error: /abort/i.test(msg) ? '收件服务超时（看看云函数日志）' : ('连不上收件服务（' + msg.slice(0, 40) + '）') };
  }
}

async function ghGetSha(cfg, path) {
  const r = await fetch(`${GH}/repos/${cfg.owner}/${cfg.repo}/contents/${encodeURI(path)}?ref=${encodeURIComponent(cfg.branch || 'master')}`, { headers: ghHeaders(cfg), cache: 'no-store' });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error('读取 ' + path + ' 失败 ' + r.status + ghHint(r.status));
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
    throw new Error('写入 ' + path + ' 失败 ' + r.status + ghHint(r.status) + '　' + msg.slice(0, 140));
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
/** 令牌体检：只用 GET，不写任何数据。判据 = 仓库接口返回的 permissions.push */
async function checkToken() {
  const cfg = ghCfg();
  const box = $('#tokenCheckBox') || (function () {
    const c = $('#tokenCheck') || (function () {
      const d = document.createElement('div'); d.id = 'tokenCheck';
      const b = $('#btnTokenCheck'); if (b && b.parentNode) b.parentNode.parentNode.appendChild(d);
      return d;
    })();
    const d2 = document.createElement('div'); d2.id = 'tokenCheckBox'; c.appendChild(d2);
    return d2;
  })();
  if (!box) return;
  if (!cfg.token) {
    box.innerHTML = '<div class="notice" style="margin-top:12px">还没填令牌。先在下面「访问令牌」里粘一个 → 点「保存设置」→ 再点这里检查。</div>';
    return;
  }
  const btn = $('#btnTokenCheck');
  if (btn) { btn.disabled = true; btn.textContent = '检查中…'; }
  const lines = [];
  const add = (ok, t) => lines.push((ok === null ? '· ' : (ok ? '✅ ' : '❌ ')) + t);
  const mask = cfg.token.slice(0, 11) + '…' + cfg.token.slice(-4);
  add(null, '仓库 ' + cfg.owner + '/' + cfg.repo + '　分支 ' + (cfg.branch || 'master') + '　令牌 ' + mask);
  let who = null, push = null, repoOk = false;
  try {
    const r1 = await fetch(GH + '/user', { headers: ghHeaders(cfg), cache: 'no-store' });
    if (r1.ok) {
      const j1 = await r1.json();
      who = j1.login;
      add(true, '令牌属于账号：' + j1.login + '（' + (j1.type || 'User') + '）');
    } else {
      add(false, '令牌本身有问题：HTTP ' + r1.status + ghHint(r1.status) + '｜GitHub 原话：' + (await safeMsg(r1)));
    }
  } catch (e) { add(false, '网络不通（先看系统代理开关）：' + (e && e.message)); }

  try {
    const r2 = await fetch(GH + '/repos/' + cfg.owner + '/' + cfg.repo, { headers: ghHeaders(cfg), cache: 'no-store' });
    const need = r2.headers.get('x-accepted-github-permissions');
    const scope = r2.headers.get('x-accepted-oauth-scopes');
    if (r2.ok) {
      const j2 = await r2.json();
      const p = j2.permissions || {};
      push = !!p.push; repoOk = true;
      add(true, '能读到仓库：' + j2.full_name + '　这个令牌的权限：' + (p.pull ? '可读 ' : '不可读 ') + (p.push ? '可写' : '（不能写）'));
      if (push) {
        add(true, '结论：令牌可以写 ✅ 直接点「同步我的修改到线上」即可。');
        if (j2.private === false) add(null, '提示：这是公开仓库，任何人对网页都是只读的，写权限只属于有令牌的人。');
      } else {
        add(false, '结论：令牌能读到仓库，但没有写入权限 → 这就是 403「Resource not accessible by permission token」的原因。');
        add(null, '要改两处（改完必须重新生成令牌，旧令牌不会自动升级）：');
        add(null, '① 令牌页面 → Repository access → 选 Only select repositories → 勾上 ' + cfg.owner + '/' + cfg.repo);
        add(null, '② 同一页面 → Permissions → Repository permissions → 找到 Contents → 选 Read and write');
        if (who && who !== cfg.owner) add(null, '③ 这个令牌属于「' + who + '」，不是仓库主人 → 还要让仓库主人在 Settings → Collaborators 里把你加为协作者');
      }
    } else {
      add(false, '读不到仓库：HTTP ' + r2.status + ghHint(r2.status) + '｜GitHub 原话：' + (await safeMsg(r2)));
      if (need) add(null, 'GitHub 说需要这个权限：' + need);
      if (scope) add(null, '经典令牌需要勾的 scope：' + scope);
      add(null, '常见原因：① 令牌的 Repository access 里没勾这个仓库　② 令牌账号还不是仓库协作者　③ 用户名/仓库名写错了');
      if (r2.status === 404 && who) add(null, '你现在用的是「' + who + '」的令牌，仓库主人是「' + cfg.owner + '」' + (who === cfg.owner ? '' : '：先去加协作者，再重新生成令牌'));
    }
  } catch (e) { add(false, '网络不通：' + (e && e.message)); }

  if (btn) { btn.disabled = false; btn.textContent = '检查令牌权限（只看不改）'; }
  box.innerHTML = '<div class="notice" style="margin-top:12px;border-color:var(--wheat)">'
    + lines.map(t => esc(t)).join('<br>') + '</div>';
}

/** 读 GitHub 报错的原始 message（如 Resource not accessible by permission token） */
async function safeMsg(r) {
  try {
    const t = await r.text();
    const m = t.match(/"message"\s*:\s*"([^"]+)"/);
    return m ? m[1] : (t || '').slice(0, 80);
  } catch (e) { return ''; }
}

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
      newMembers: (function () {
        const m = {};
        (cloud.newMembers || []).forEach(x => { if (x && x.name) m[x.name] = x; });
        (l.newMembers || []).forEach(x => { if (x && x.name) m[x.name] = x; });
        return Object.keys(m).map(k => {
          const x = m[k];
          return (x.level || []).length ? x : Object.assign({}, x, { level: ['正式'] });
        });
      })(),
      results: (function () {
        const hid = new Set((cloud.hiddenResults || []).concat(l.hiddenResults || []));
        return (cloud.results || []).concat(l.results || [])
          .filter(r => !hid.has(r.uid || (r.name + '|' + r.sec)));
      })(),
      hiddenResults: (cloud.hiddenResults || []).concat(l.hiddenResults || []),
      competitions: (cloud.competitions || []).concat(l.competitions || []),
      compRecords: mergeCompRecords(cloud.compRecords, l.compRecords),
      pbAdded: (function () {
        const hid = new Set((cloud.pbHidden || []).concat(l.pbHidden || []));
        return mergePbAdded(cloud.pbAdded, l.pbAdded)
          .filter(p => !hid.has(p.uid || (p.name + '|' + p.event)));
      })(),
      pbHidden: Array.from(new Set((cloud.pbHidden || []).concat(l.pbHidden || []))),
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
      if (!p.data) continue;                    // 选照片时已直传线上，这里只写清单
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

/* 双击本地文件打开时（file://）浏览器不允许 fetch 本地文件；此时用 <script> 载入的
   window.TEAM_OVERRIDES 兜底，保证本地打开的页面也显示同步过的数据 */
function cloudFromScriptTag() {
  if (window.TEAM_OVERRIDES && typeof window.TEAM_OVERRIDES === 'object') {
    CLOUD_OV = window.TEAM_OVERRIDES;
    SYNC_STATE = 'cloud';
    return true;
  }
  return false;
}

async function loadCloud(force) {
  try {
    const r = await fetch(ROOT + 'data/overrides.js?t=' + Date.now(), { cache: force ? 'reload' : 'no-store' });
    if (!r.ok) { if (cloudFromScriptTag()) return true; SYNC_STATE = 'local'; return false; }
    const txt = await r.text();
    const m = txt.match(/window\.TEAM_OVERRIDES\s*=\s*([\s\S]*?);\s*$/);
    CLOUD_OV = m ? JSON.parse(m[1]) : null;
    SYNC_STATE = CLOUD_OV ? 'cloud' : 'local';
    return true;
  } catch (e) {
    if (cloudFromScriptTag()) return true;
    SYNC_STATE = 'offline';
    return false;
  }
}

document.addEventListener('click', e => {
  const t = e.target.closest('[data-tab],[data-go],[data-album],[data-lvl],[data-ev],[data-sex],[data-msec],[data-comp],[data-complist],[data-ty],[data-photo],[data-lb]');
  if (!t) return;
  const d = t.dataset;
  if (d.tab) return goTab(d.tab);
  if (d.go) return goTab(d.go, { msec: d.msec });
  if (d.msec) { state.manageSec = d.msec; return render(); }
  if (d.complist !== undefined) { state.compList = true; state.comp = ''; state.pbQ = ''; state.pbSex = ''; return render(); }
  if (d.comp !== undefined && (t.classList.contains('chip') || t.classList.contains('comp-row')
      || t.closest('.comp-row') || t.classList.contains('l') || t.classList.contains('t') || t.classList.contains('r'))) {
    const row = t.closest('.comp-row');
    state.comp = row ? row.dataset.comp : d.comp;
    state.compList = false; state.pbQ = ''; state.pbSex = ''; return render();
  }
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

/* 中文输入法（拼音）正在组词时不要触发检索 —— 否则会打断输入、边打边搜 */
const IME_IDS = ['boardQ', 'rosterQ', 'mRosterQ', 'nm_name', 'nm_college', 'nm_major', 'nm_grade'];
document.addEventListener('compositionstart', e => {
  if (e.target && IME_IDS.indexOf(e.target.id || '') >= 0) window._imeOn = true;
}, true);
document.addEventListener('compositionend', e => {
  if (e.target && IME_IDS.indexOf(e.target.id || '') >= 0) {
    window._imeOn = false;
    try { e.target.dispatchEvent(new Event('input', { bubbles: true })); } catch (err) {}
  }
}, true);

document.addEventListener('input', e => {
  if (window._imeOn) return;                      // 组词中，先不管
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
  $('#lbCap').textContent = (lbIdx + 1) + ' / ' + lbList.length;
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

/** ISO 时间 → "09-15 08:12"（本地时间，页头显示用） */
function fmtUpd(s) {
  const d = new Date(s);
  if (isNaN(d.getTime())) return String(s || '').slice(0, 16).replace('T', ' ');
  const p = n => (n < 10 ? '0' : '') + n;
  return p(d.getMonth() + 1) + '-' + p(d.getDate()) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
}

/** 展示版：每 30 秒悄悄看一眼线上数据有没有更新（只读、不上传；切到后台不查）
    队长一同步，别人已经开着的页面会在半分钟内自己变成最新 */
let AUTO_TICK = null;
function startAutoRefresh() {
  if (AUTO_TICK || MODE !== 'view') return;
  AUTO_TICK = setInterval(async () => {
    if (document.hidden) return;
    const lb = $('#lightbox');
    if (lb && lb.classList.contains('on')) return;          // 正在看大图，别打断
    try {
      const r = await fetch(ROOT + 'data/overrides.js?t=' + Date.now(), { cache: 'no-store' });
      if (!r.ok) return;
      const m = (await r.text()).match(/window\.TEAM_OVERRIDES\s*=\s*([\s\S]*?);\s*$/);
      if (!m) return;
      const o = JSON.parse(m[1]);
      if ((o.updated || '') !== ((CLOUD_OV && CLOUD_OV.updated) || '')) {
        const y = window.scrollY;
        CLOUD_OV = o; SYNC_STATE = 'cloud';
        render();
        window.scrollTo(0, y);
        toast('数据已更新 · ' + fmtUpd(o.updated), 4000);
      }
    } catch (e) { /* 网络抖动就算了，下一轮再试 */ }
  }, 30000);
}

(async function init() {
  if (typeof XLSX === 'undefined' && MODE === 'captain') console.warn('SheetJS 未加载，Excel 导入不可用');
  const h = (location.hash || '').replace('#', '');
  if ((TABS[MODE] || []).some(t => t[0] === h)) state.tab = h;
  // 这个模式里没有「总览」这类默认页（比如成绩上报页只有一个 tab）→ 落到第一个可用 tab
  if (!(TABS[MODE] || []).some(t => t[0] === state.tab)) state.tab = (TABS[MODE] || [['home']])[0][0];
  await loadCloud(false);
  await loadQueueCfg();
  if (MODE === 'captain' && loadCfgFromHash()) toast('已用链接里的账号自动填好，可以直接同步', 4000);
  render();
  startAutoRefresh();
})();
