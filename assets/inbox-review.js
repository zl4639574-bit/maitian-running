/* ============================================================================
   麦田守望 · 待审台（审核 + 一键上线）
   ----------------------------------------------------------------------------
   这是一个【完全独立】的文件：它不改动 assets/app.js 里的任何一个字。
   加载方式：captain/index.html 里在 app.js 之后多加载这一行（见 安装说明.txt）
   卸载方式：把那行 <script> 删掉，队长版立刻回到原样（本文件可以留着不删）。

   它做两件事：
     1. 把「① 收件箱」的显示换成待审台：逐条展开看明细、与线上现状对比、标出风险
     2. 把原来分离的两步（接收 → 再去「数据管理 → 同步」）并成一颗「通过并上线」

   数据写入一律调用 app.js 里现成的函数（applyMemberDoc / addMyResults / publishMine /
   pushToGitHub / ghDelete / ghPut），本文件不自己拼数据结构 —— 避免写坏数据。
   ============================================================================ */

(function () {
  'use strict';
  if (window.__mtInboxReview) return;      // 防重复加载
  window.__mtInboxReview = { version: '1.0' };

  var FNAME = { sex: '性别', college: '学院', major: '专业', grade: '年级', level: '身份' };
  var LS_REVIEWER = 'mt_reviewer_v1';
  var S = function (v) { return String(v == null ? '' : v).trim(); };

  /* ------------------------------ 判定表 ------------------------------ */

  var V = {
    fill:     { k: 'fill',     text: '补全资料',       tone: 'green', safe: true,  desc: '只填了原来空着的字段，不覆盖任何现有内容' },
    pbOnly:   { k: 'pbOnly',   text: '只补了成绩/头像', tone: 'green', safe: true,  desc: '资料字段没变，只是补了个人最好成绩或头像' },
    newRec:   { k: 'newRec',   text: '新增成绩',       tone: 'green', safe: true,  desc: '这个项目原来没有记录，属于新增' },
    pb:       { k: 'pb',       text: '刷新最好成绩',    tone: 'green', safe: true,  desc: '比现有最好成绩更快，会更新个人最好成绩' },
    notPb:    { k: 'notPb',    text: '不是最好成绩',    tone: 'wheat', safe: true,  desc: '已有更快的成绩，这条作为记录保留，不改个人最好成绩' },
    noChange: { k: 'noChange', text: '没有任何变化',    tone: 'wheat', safe: false, desc: '和现在一模一样，没有可改的内容，建议驳回' },
    conflict: { k: 'conflict', text: '改动已有资料',    tone: 'wheat', safe: false, desc: '提交的值和现在不一样，需要你判断哪个对' },
    memberNew:{ k: 'memberNew',text: '新增队员',       tone: 'wheat', safe: false, desc: '公开名册里没有这个人，通过后要确认身份与年级' },
    wasHidden:{ k: 'wasHidden',text: '曾在「已移除」',  tone: 'wheat', safe: false, desc: '这人之前被移出过名单，确认是否要放回' },
    dup:      { k: 'dup',      text: '重复提交',       tone: 'red',   safe: false, desc: '和现有记录完全一样，建议驳回' },
    dayClash: { k: 'dayClash', text: '同日成绩不一致',  tone: 'red',   safe: false, desc: '同一天同一个项目有不同成绩，需要人工判断' },
    noMember: { k: 'noMember', text: '名册里没有此人',  tone: 'red',   safe: false, desc: '通常是名字写错，或人还没进名册' },
    parseBad: { k: 'parseBad', text: '成绩看不清',     tone: 'red',   safe: false, desc: '成绩格式无法解析，需要人工修正' }
  };

  /** 只看「已经在线上的」成绩，用来和提交内容对比（本机还没上线的草稿不算） */
  function onlineResults() {
    try {
      return allResults().filter(function (r) { return !r.local && r.sec > 0; });
    } catch (e) { return []; }
  }

  /** 一条成绩，和现状对比之后的结论 */
  function judgeRow(row, online, st) {
    var ev = row.event || '5000米';
    var reasons = [], notes = [];
    st = st || rosterStatus(row.name);
    if (!st.inRoster) {
      reasons.push('noMember');
      try { var h = rosterHint(row.name); if (h) notes.push(h); } catch (e) {}
    }
    if (!row.sec) reasons.push('parseBad');
    try { if (row.sec) { var sp = secSuspicion(row.sec, ev); if (sp) notes.push(sp); } } catch (e) {}
    // 「半马 1:23」这种只写「时:分」的，最容易把秒写丢（历史上出过 1:24:00 被吞成 1:24 的事），
    // 所以这里明确把解析结果念出来，让人一眼能核对
    try {
      var parts = S(row.fmt).split(':').filter(function (x) { return x !== ''; });
      if (parts.length === 2 && /^(半马|全马|马拉松)$/.test(ev)) {
        notes.push('只写了「时:分」，已按 ' + parts[0] + ' 小时 ' + parts[1] + ' 分 ＝ ' + fmtSec(row.sec) + ' 解析，请核对是否漏写秒');
      }
    } catch (e) {}

    var same = online.filter(function (r) { return r.name === row.name && (r.event || '') === ev; });
    if (row.sec && same.length) {
      var exact = same.filter(function (r) { return Math.abs(r.sec - row.sec) < 0.5; })[0];
      var faster = same.filter(function (r) { return r.sec < row.sec - 0.5; });
      var clash = same.filter(function (r) { return r.date && row.date && r.date === row.date && Math.abs(r.sec - row.sec) >= 0.5; });
      if (exact) reasons.push('dup');
      else if (clash.length) { reasons.push('dayClash'); notes.push('同一天已有：' + clash.map(function (x) { return (x.fmt || fmtSec(x.sec)) + '（' + (x.srcLabel || x.src || '') + '）'; }).join('、')); }
      else if (faster.length) { reasons.push('notPb'); notes.push('已有更快：' + faster.map(function (x) { return (x.fmt || fmtSec(x.sec)) + '（' + (x.srcLabel || x.src || '') + '）'; }).join('、')); }
      else { reasons.push('pb'); notes.push('原成绩：' + same.map(function (x) { return x.fmt || fmtSec(x.sec); }).join('、') + ' → 现在 ' + fmtSec(row.sec)); }
    } else if (row.sec) reasons.push('newRec');
    return { key: reasons[0] || 'newRec', all: reasons, notes: notes, same: same };
  }

  /** 队员现在（线上）的档案：原始名册 + 队长新增 + 队长改过的 */
  function effMember(name) {
    var base = {}, nw = {}, e = {};
    try { base = ((typeof BASE !== 'undefined' && BASE.roster) || []).filter(function (m) { return m.name === name; })[0] || {}; } catch (err) {}
    try { nw = (ov().newMembers || []).filter(function (m) { return m.name === name; })[0] || {}; } catch (err) {}
    try { e = (ov().memberEdits || {})[name] || {}; } catch (err) {}
    return Object.assign({}, base, nw, e);
  }

  /** 一份队员资料提交，和现状对比之后的结论 */
  function judgeItem(it, online) {
    var res = { verdicts: [], notes: [], fields: [], rows: [], isNew: false };
    if (it.type === 'maitian-member') {
      var d = it.data || {}, name = S(d.name);
      var st = rosterStatus(name);
      var cur = effMember(name);
      if (st.removed) res.verdicts.push(V.wasHidden);
      if (!st.inRoster) {
        res.isNew = true;
        res.verdicts.push(V.memberNew);
        try { var h = rosterHint(name); if (h) res.notes.push(h); } catch (e) {}
      }
      ['sex', 'college', 'major', 'grade'].forEach(function (f) {
        var want = S(d[f]), now = S(cur[f]);
        if (!want || want === now) return;
        res.fields.push({ f: f, now: now, want: want, kind: now ? 'edit' : 'new' });
      });
      var lvNow = (cur.level || []).join('/');
      var lvWant = S(d.level);
      if (lvWant && lvWant !== lvNow) res.fields.push({ f: 'level', now: lvNow, want: lvWant, kind: lvNow ? 'edit' : 'new' });

      var pbKeys = Object.keys(d.pb || {}).filter(function (k) { return S(d.pb[k]) && S(d.pb[k]) !== '无' && S(d.pb[k]) !== '-'; });
      pbKeys.forEach(function (ev) {
        var sec = secFromCell(d.pb[ev], ev);
        var v = judgeRow({ name: name, event: ev, sec: sec, date: '' }, online, st);
        res.notes.push('最好成绩 ' + ev + ' ' + d.pb[ev] + ' → ' + V[v.key].text + (v.notes.length ? '（' + v.notes.join('；') + '）' : ''));
      });
      if (d.photo) res.notes.push('带了 1 张头像（通过后传到 images/avatars/）');

      if (res.fields.some(function (x) { return x.kind === 'edit'; })) res.verdicts.push(V.conflict);
      if (!res.fields.length) {
        if (res.verdicts.length) res.verdicts.push(V.noChange);
        else if (pbKeys.length || d.photo) res.verdicts.push(V.pbOnly);
        else res.verdicts.push(V.noChange);
      } else if (!res.verdicts.length) res.verdicts.push(V.fill);
    } else {
      var rows = (it.data && it.data.rows) || [];
      rows.forEach(function (r) {
        var ev = r.event || '5000米';
        var sec = Number(r.sec) || secFromCell(r.fmt, ev) || 0;
        var o = { name: S(r.name), event: ev, fmt: S(r.fmt) || fmtSec(sec), sec: sec,
                  date: S(r.date) || S(it.data && it.data.date), meet: S(r.meet), rank: S(r.rank), _src: r };
        var j = judgeRow(o, online);
        o.verdict = V[j.key]; o.all = j.all; o.notes = j.notes;
        o.same = j.same.map(function (x) { return { fmt: x.fmt || fmtSec(x.sec), src: x.srcLabel || x.src || '' }; });
        res.rows.push(o);
        if (!res.verdicts.some(function (v) { return v.k === o.verdict.k; })) res.verdicts.push(o.verdict);
      });
    }
    res.safe = res.verdicts.length > 0 && res.verdicts.every(function (v) { return v.safe; });
    return res;
  }

  function toneCls(tone) {
    return tone === 'green' ? 'tagbadge green' : (tone === 'red' ? 'tagbadge red' : 'tagbadge wheat');
  }
  function toneColor(tone) {
    return tone === 'green' ? '#3B6D11' : (tone === 'red' ? '#A32D2D' : '#854F0B');
  }
  function escv(v) { try { return esc(v); } catch (e) { return String(v == null ? '' : v); } }

  /* ------------------------------ 渲染 ------------------------------ */

  function renderBoard() {
    var box = document.getElementById('inboxArea');
    if (!box) return;
    var items = (typeof inboxItems !== 'undefined' && inboxItems) || [];

    if (!items.length) {
      box.innerHTML = '<div class="empty" style="margin-top:12px">待审队列是空的。<br>' +
        '<span class="tiny">队员在收集页点「⚡ 直接提交给队长」之后，内容会出现在这里。</span></div>';
      return;
    }

    var online = onlineResults();
    var judged = items.map(function (it) { return judgeItem(it, online); });
    var safeN = judged.filter(function (j, i) { return j.safe && !items[i].__done; }).length;
    var waitN = judged.filter(function (j, i) { return !j.safe && !items[i].__done; }).length;

    var html = '<div class="tiny" style="margin:12px 0 8px">待审 <b>' + items.length + '</b> 条' +
      '（其中 <b style="color:#3B6D11">' + safeN + '</b> 条低风险可批量，<b style="color:#854F0B">' + waitN + '</b> 条需要你逐条定）；' +
      '对比基准：线上 <b>' + online.length + '</b> 条成绩</div>' +
      '<div class="chips" style="margin-bottom:10px">' +
        '<button class="btn sm" data-mt-safe' + (safeN ? '' : ' disabled') + '>批量通过低风险项（' + safeN + '）</button>' +
        '<button class="btn ghost sm" data-mt-all>展开全部</button>' +
        '<span class="tiny">通过＝写进数据并立刻推上网站</span>' +
      '</div>';

    html += items.map(function (it, i) {
      var j = judged[i];
      it.__judgeFields = j.fields || [];      // 供「改完再通过」按下标定位字段
      var top = it.__done ? { text: it.__done === 'ok' ? '已通过上线' : '已驳回', tone: it.__done === 'ok' ? 'green' : 'red' } : j.verdicts[0];
      var rows = '';
      if (it.__open) {
        if (j.verdicts.length > 1) {
          rows += '<div class="notice" style="margin:8px 0;line-height:1.8">这条混了几种情况：<b>' +
            j.verdicts.map(function (v) { return escv(v.text); }).join(' ／ ') + '</b>　建议逐条看</div>';
        }
        if (j.notes.length) {
          rows += '<div class="tiny" style="margin:6px 0;line-height:1.8">' + j.notes.map(escv).join('<br>') + '</div>';
        }

        if (it.type === 'maitian-member') {
          rows += '<div class="tbl-wrap"><table class="tbl" style="min-width:auto"><thead><tr>' +
            '<th class="no-sort">字段</th><th class="no-sort">现在</th><th class="no-sort">提交</th><th class="no-sort"></th>' +
            '</tr></thead><tbody>';
          if (!j.fields.length) rows += '<tr><td colspan="4" class="tiny">资料字段与现在完全一致</td></tr>';
          j.fields.forEach(function (f, fi) {
            rows += '<tr' + (f.kind === 'edit' ? ' style="background:#FAEEDA"' : '') + '>' +
              '<td>' + escv(FNAME[f.f] || f.f) + '</td>' +
              '<td>' + (f.now ? '<span style="color:#888780;text-decoration:line-through">' + escv(f.now) + '</span>' : '<span class="tiny">（空）</span>') + '</td>' +
              '<td><input type="text" data-mt-f="' + i + '" data-mt-fi="' + fi + '" value="' + escv(f.want) + '" style="width:150px"></td>' +
              '<td class="tiny">' + (f.kind === 'edit' ? '改了这个' : '补空') + '</td></tr>';
          });
          if (it.data && it.data.photo) rows += '<tr><td>头像</td><td colspan="3" class="tiny">带了 1 张</td></tr>';
          rows += '</tbody></table></div>';
        } else {
          rows += '<div class="tbl-wrap"><table class="tbl" style="min-width:auto"><thead><tr>' +
            '<th class="no-sort">姓名</th><th class="no-sort">项目</th><th class="no-sort">成绩</th><th class="no-sort hide-sm">日期</th>' +
            '<th class="no-sort">与现状对比</th></tr></thead><tbody>';
          j.rows.forEach(function (r, ri) {
            var bg = r.verdict.tone === 'red' ? '#FCEBEB' : (r.verdict.tone === 'green' ? '#EAF3DE' : '#FAEEDA');
            var cmp = r.same.length
              ? '现在 ' + r.same.map(function (x) { return escv(x.fmt); }).join('、') + (r.same[0].src ? '<br><span class="tiny">' + escv(r.same[0].src) + '</span>' : '')
              : '<span class="tiny">原来没有这个项目的记录</span>';
            rows += '<tr style="background:' + bg + '">' +
              '<td><input type="text" data-mt-r="' + i + '" data-mt-ri="' + ri + '" data-mt-k="name" value="' + escv(r.name) + '" style="width:82px"></td>' +
              '<td><input type="text" data-mt-r="' + i + '" data-mt-ri="' + ri + '" data-mt-k="event" value="' + escv(r.event) + '" style="width:78px"></td>' +
              '<td><input type="text" data-mt-r="' + i + '" data-mt-ri="' + ri + '" data-mt-k="fmt" value="' + escv(r.fmt) + '" style="width:86px"></td>' +
              '<td><input type="text" data-mt-r="' + i + '" data-mt-ri="' + ri + '" data-mt-k="date" value="' + escv(r.date) + '" style="width:92px"></td>' +
              '<td><b style="color:' + toneColor(r.verdict.tone) + '">' + escv(r.verdict.text) + '</b><br>' + cmp +
                (r.notes.length ? '<br><span class="tiny">' + r.notes.map(escv).join('<br>') + '</span>' : '') + '</td></tr>';
          });
          rows += '</tbody></table></div>';
        }

        rows += '<div class="chips" style="margin-top:10px">' +
          '<button class="btn sm" data-mt-ok="' + i + '">通过并上线</button>' +
          '<button class="btn ghost sm" data-mt-keep="' + i + '">仅收下（不上线）</button>' +
          '<button class="btn danger sm" data-mt-no="' + i + '">驳回</button>' +
          '<span class="tiny">改上面的格子再点「通过并上线」＝ 改完再通过</span></div>' +
          '<div id="mtRj' + i + '" style="display:none;margin-top:8px">' +
            '<input type="text" id="mtRjt' + i + '" placeholder="驳回理由（例如：成绩疑似少写秒、姓名写错字），会记进审核记录" style="width:100%">' +
            '<div class="chips" style="margin-top:6px"><button class="btn danger sm" data-mt-nod="' + i + '">确认驳回</button></div>' +
          '</div>';
      }
      return '<div class="comp-row" style="cursor:default;flex-direction:column;align-items:stretch">' +
        '<div style="display:flex;gap:10px;align-items:flex-start">' +
          '<span class="' + toneCls(top.tone) + '" style="flex:0 0 auto">' + escv(top.text) + '</span>' +
          '<div class="l" style="flex:1;min-width:0">' +
            '<div class="t">' + escv(it.type === 'maitian-member' ? (S(it.data && it.data.name) + ' 的资料') :
              ('成绩 ' + ((it.data && it.data.rows) || []).length + ' 条：' + ((it.data && it.data.rows) || []).slice(0, 3).map(function (r) { return S(r.name); }).join('、'))) + '</div>' +
            '<div class="tiny">' + escv(String(it.at || '').replace('T', ' ').slice(0, 16)) + ' · ' + escv(it.id) +
              ' ' + (it.type === 'maitian-member' ? '<span class="tagbadge green">资料</span>' : '<span class="tagbadge wheat">成绩</span>') +
              (it.__done ? ' · <b>' + (it.__done === 'ok' ? '已通过' : '已驳回') + '</b>' + (it.__reason ? '：' + escv(it.__reason) : '') : '') + '</div>' +
          '</div>' +
          '<button class="btn ghost sm" data-mt-tg="' + i + '">' + (it.__open ? '收起' : '看明细') + '</button>' +
        '</div>' + rows + '</div>';
    }).join('');

    box.innerHTML = html;
    bindBoard();
  };

  function rerender() { try { window.renderInbox(); } catch (e) {} }

  function bindBoard() {
    var box = document.getElementById('inboxArea');
    if (!box) return;
    var items = (typeof inboxItems !== 'undefined' && inboxItems) || [];

    box.querySelectorAll('[data-mt-tg]').forEach(function (b) {
      b.onclick = function () { var it = items[+b.dataset.mtTg]; it.__open = !it.__open; rerender(); };
    });
    box.querySelectorAll('[data-mt-all]').forEach(function (b) {
      b.onclick = function () {
        var anyClosed = items.some(function (it) { return !it.__open; });
        items.forEach(function (it) { it.__open = anyClosed; });
        rerender();
      };
    });
    box.querySelectorAll('[data-mt-safe]').forEach(function (b) {
      b.onclick = function () { approveBatch(); };
    });
    box.querySelectorAll('[data-mt-ok]').forEach(function (b) {
      b.onclick = function () { approveOne(+b.dataset.mtOk, false); };
    });
    box.querySelectorAll('[data-mt-keep]').forEach(function (b) {
      b.onclick = function () { approveOne(+b.dataset.mtKeep, true); };
    });
    box.querySelectorAll('[data-mt-no]').forEach(function (b) {
      b.onclick = function () {
        var d = document.getElementById('mtRj' + b.dataset.mtNo);
        if (d) d.style.display = 'block';
      };
    });
    box.querySelectorAll('[data-mt-nod]').forEach(function (b) {
      b.onclick = function () {
        var i = +b.dataset.mtNod;
        var t = document.getElementById('mtRjt' + i);
        rejectOne(i, (t && t.value.trim()) || '（没写理由）');
      };
    });

    // 就地改内容（改完再通过）
    box.querySelectorAll('[data-mt-r]').forEach(function (inp) {
      inp.onchange = function () {
        var it = items[+inp.dataset.mtR];
        var r = ((it.data && it.data.rows) || [])[+inp.dataset.mtRi];
        if (!r) return;
        var k = inp.dataset.mtK;
        if (k === 'fmt') {
          r.fmt = inp.value.trim();
          r.sec = secFromCell(r.fmt, r.event || '5000米') || 0;
        } else r[k] = inp.value.trim();
        it.__edited = true;
        rerender();
      };
    });
    box.querySelectorAll('[data-mt-f]').forEach(function (inp) {
      inp.onchange = function () {
        var it = items[+inp.dataset.mtF];
        var f = (it.__judgeFields || [])[+inp.dataset.mtFi];
        if (!f) return;
        if (f.f === 'level') it.data.level = inp.value.trim();
        else it.data[f.f] = inp.value.trim();
        it.__edited = true;
        rerender();
      };
    });
  }

  /* ------------------------------ 动作 ------------------------------ */

  function reviewerName() {
    var v = '';
    try { v = S(lsGet(LS_REVIEWER, '')); } catch (e) {}
    if (!v) {
      v = S(window.prompt('你是哪位（写进审核记录，只需填一次）', '队长'));
      if (v) { try { lsSet(LS_REVIEWER, v); } catch (e) {} }
    }
    return v || '队长';
  }

  function b64(str) {
    var bytes = new TextEncoder().encode(str), bin = '';
    for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin);
  }

  /** 审核留痕：本机存一份，另在仓库 data/audit/ 建一个新文件（新文件不会覆盖任何东西） */
  async function writeAudit(rec) {
    try {
      var all = lsGet('mt_audit_v1', []) || [];
      all.push(rec); lsSet('mt_audit_v1', all.slice(-300));
    } catch (e) {}
    try {
      var cfg = ghCfg();
      if (!cfg || !cfg.token) return;
      var name = 'data/audit/' + String(rec.at).replace(/[-:T.Z]/g, '').slice(0, 14) + '-' + rec.action + '-' + (rec.id || 'x').slice(-5) + '.json';
      await ghPut(cfg, name, b64(JSON.stringify(rec, null, 1)), '审核记录 ' + rec.action + ' ' + (rec.id || ''));
    } catch (e) { /* 留痕失败不影响数据，静默 */ }
  }

  /** 把一条提交「落库」到本机（复用 app.js 的现成函数，与原来「接收」完全一致） */
  async function landToLocal(it) {
    if (it.type === 'maitian-member') {
      var r = await applyMemberDoc(it.data);
      return r ? ('资料：信息 ' + r.info + ' 项、成绩 ' + r.pbs + ' 条' + (r.photo ? '、头像 1 张' : '')) : '资料（缺姓名，未处理）';
    }
    var rows = ((it.data && it.data.rows) || []).map(function (r) {
      return {
        uid: newUid(), name: r.name, event: r.event || '5000米',
        sec: Number(r.sec) || secFromCell(r.fmt, r.event) || 0,
        fmt: r.fmt || fmtSec(r.sec || 0),
        date: r.date || (it.data && it.data.date) || '', meet: r.meet || '', rank: r.rank || '', ts: Date.now()
      };
    }).filter(function (r) { return r.name && r.sec; });
    addMyResults(rows);
    return rows.length + ' 条成绩';
  }

  /** 通过并上线：落库 → 发布 → 推上线 → 从队列删掉 → 留痕 */
  async function approveOne(i, onlyKeep) {
    var items = (typeof inboxItems !== 'undefined' && inboxItems) || [];
    var it = items[i];
    if (!it) return;
    var cfg = ghCfg();
    if (!onlyKeep && !cfg.token) {
      return toast('还没填「访问令牌」，无法一键上线：数据管理 → 同步 → 粘上令牌 → 保存设置。也可以先点「仅收下（不上线）」。', 12000);
    }
    try {
      var what = await landToLocal(it);
      var pushed = false;
      if (!onlyKeep) {
        if (it.type === 'maitian-scores') { try { publishMine(); } catch (e) {} }   // 成绩：并入「待上线」
        await pushToGitHub();                                                      // 统一推上线
        pushed = true;
      }
      // 从队列里删掉
      try { if (cfg.token) await ghDelete(cfg, it.path, (onlyKeep ? '收下' : '通过上线') + '上报 ' + it.id); }
      catch (e) { toast('数据已经处理，但队列里这条没删掉：' + String((e && e.message) || e), 9000); }

      it.__done = 'ok'; it.__open = false;
      items.splice(i, 1);                       // 与原「接收」一致：处理完就从队列移除
      await writeAudit({ at: new Date().toISOString(), reviewer: reviewerName(), action: onlyKeep ? 'keep' : 'approve',
        id: it.id, type: it.type, submittedAt: it.at, edited: !!it.__edited, summary: what,
        detail: it.type === 'maitian-member' ? it.data :
          { date: it.data && it.data.date, rows: ((it.data && it.data.rows) || []) } });

      toast(pushed ? ('已通过并上线：' + what + '（GitHub Pages 约 30–90 秒生效）')
                   : ('已收下：' + what + '（还没上线，去「数据管理 → 比赛成绩 / 队员名册」处理）'), 11000);
      rerender(); if (typeof render === 'function' && it.type === 'maitian-member') render();
    } catch (e) {
      toast('没处理成功：' + String((e && e.message) || e) + '（这条还留在队列里，可以重试）', 14000);
    }
  }

  /** 批量通过低风险项：先全部落库，再一次性推上线（只产生一次提交） */
  async function approveBatch() {
    var items = (typeof inboxItems !== 'undefined' && inboxItems) || [];
    if (!items.length) return;
    var cfg = ghCfg();
    if (!cfg.token) return toast('还没填「访问令牌」，无法一键上线：数据管理 → 同步 → 粘上令牌 → 保存设置。', 12000);
    var online = onlineResults();
    var safeList = items.map(function (it, i) { return { it: it, i: i, j: judgeItem(it, online) }; })
      .filter(function (x) { return x.j.safe; });
    if (!safeList.length) return toast('没有低风险条目 —— 剩下的都要你逐条看', 9000);
    if (!window.confirm('把 ' + safeList.length + ' 条低风险提交（补全资料 / 新增成绩 / 刷新最好成绩 / 不是最好成绩）一起通过并上线？')) return;

    var doneIds = [], what = [];
    try {
      for (var k = 0; k < safeList.length; k++) {
        var desc = await landToLocal(safeList[k].it);
        what.push(safeList[k].it.id.slice(-5) + ' ' + desc);
        doneIds.push(safeList[k].it);
      }
      try { publishMine(); } catch (e) {}
      await pushToGitHub();                       // 一次提交推上去
      for (var m = 0; m < doneIds.length; m++) {
        var it = doneIds[m];
        try { await ghDelete(cfg, it.path, '批量通过上线 ' + it.id); } catch (e) {}
        await writeAudit({ at: new Date().toISOString(), reviewer: reviewerName(), action: 'approve-batch',
          id: it.id, type: it.type, submittedAt: it.at, edited: !!it.__edited, summary: '批量通过' });
      }
      // 从队列移除
      var keep = items.filter(function (it) { return doneIds.indexOf(it) < 0; });
      items.length = 0; keep.forEach(function (it) { items.push(it); });
      toast('已批量通过并上线 ' + doneIds.length + ' 条（GitHub Pages 约 30–90 秒生效）', 11000);
      rerender(); if (typeof render === 'function') render();
    } catch (e) {
      toast('批量处理中断：' + String((e && e.message) || e) + '　已处理的条目不会再重复处理，剩下的还留在队列里', 16000);
      rerender();
    }
  }

  /** 驳回：带理由删掉队列文件 + 留痕（不碰任何数据） */
  async function rejectOne(i, reason) {
    var items = (typeof inboxItems !== 'undefined' && inboxItems) || [];
    var it = items[i];
    if (!it) return;
    var cfg = ghCfg();
    try {
      if (cfg.token) await ghDelete(cfg, it.path, '驳回上报 ' + it.id + '：' + reason);
    } catch (e) { return toast('删不掉：' + String((e && e.message) || e), 9000); }
    await writeAudit({ at: new Date().toISOString(), reviewer: reviewerName(), action: 'reject',
      id: it.id, type: it.type, submittedAt: it.at, reason: reason });
    items.splice(i, 1);
    toast('已驳回（理由已记进审核记录）', 8000);
    rerender();
  }

  /* ------------------------------ 自检 ------------------------------ */

  window.__mtInboxReview.selfCheck = function () {
    var need = ['rosterStatus', 'allResults', 'secFromCell', 'fmtSec', 'applyMemberDoc', 'addMyResults',
                'publishMine', 'pushToGitHub', 'ghDelete', 'ghPut', 'ghCfg', 'lsGet', 'lsSet', 'toast', 'esc'];
    var miss = need.filter(function (n) { return typeof window[n] !== 'function'; });
    var sample = { name: '李志宏', event: '半马', fmt: '1:22:10', sec: secFromCell('1:22:10', '半马'), date: '2026.9.14' };
    var online = onlineResults();
    var j = judgeRow(sample, online, rosterStatus(sample.name));
    return {
      ok: miss.length === 0,
      missing: miss,
      onlineResults: online.length,
      sampleSec: sample.sec,
      sampleFmt: fmtSec(sample.sec),
      sampleVerdict: V[j.key].text,
      sampleNotes: j.notes,
      renderInboxIsOurs: String(window.renderInbox).indexOf('待审') >= 0 || String(window.renderInbox).indexOf('data-mt-ok') >= 0
    };
  };

  /* ------------------------------ 安装 ------------------------------ */
  /* 关键：动态插入的 <script> 不保证按插入顺序执行（小的文件可能先跑完）。
     captain/index.html 里是用 app.js 的 onload 串起来的（顺序有保证），
     但这里仍然自己等一手 —— 万一别的页面直接把本文件并行加载，也不会被 app.js 覆盖掉。 */
  function installed() {
    return typeof window.renderInbox === 'function' && String(window.renderInbox).indexOf('data-mt-ok') >= 0;
  }

  function install() {
    if (installed()) return true;
    if (typeof window.renderInbox !== 'function' || typeof window.render !== 'function') return false;  // app.js 还没到
    window.renderInbox = renderBoard;
    var realRender = window.render;
    window.render = function () {
      var out = realRender.apply(this, arguments);
      try {
        var box = document.getElementById('inboxArea');
        if (box && typeof inboxItems !== 'undefined' && inboxItems && inboxItems.length) window.renderInbox();
      } catch (e) {}
      return out;
    };
    try {
      var box = document.getElementById('inboxArea');
      if (box && typeof inboxItems !== 'undefined' && inboxItems) window.renderInbox();
    } catch (e) {}
    return true;
  }

  window.__mtInboxReview.install = install;
  if (!install()) {
    var waited = 0;
    var timer = setInterval(function () {
      waited += 100;
      if (install() || waited > 8000) {
        clearInterval(timer);
        if (!installed()) console.warn('[待审台] 没能挂上：assets/app.js 似乎没加载成功');
      }
    }, 100);
  }
})();
