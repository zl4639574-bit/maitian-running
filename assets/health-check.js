/* =====================================================================
   数据体检 + 「他为什么没上榜」（独立插件，只挂在队长版的「数据管理」页）
   目的：把"数据里有问题但没人知道"变成"打开就看见红点"。
        —— 2026-09-16 那次「通过了好几条上报但网站不显示」，其实同时藏着
           身份不够上不了榜、同步回滚、头像没挂上人、重复成绩四件事，
           每一件当时都没有任何地方会告诉你。

   两个视图：
     · 数据体检：有成绩却上不了榜的人 / 被「已移除显示」挡着的 / 重复成绩 / 本机没同步的改动
     · 他为什么没上榜：输入姓名，直接给结论和改法

   全部用本机已有的数据算（不联网），所以打开就是即时的。
   依赖 app.js 的顶层函数：rosterList / effLevel / rosterStatus / isVisibleLevel /
   personalBests / allResults / ov / pendingCount / esc / fmtSec
   ===================================================================== */
(function () {
  'use strict';
  if (window.__mtHealth) return;
  window.__mtHealth = 1;
  if (window.APP_MODE !== 'captain') return;        // 只有队长版能改数据，体检也只对队长有用

  var V = { tab: 'check', open: '', q: '' };
  var SEP = '\u0001';                               // 用来拼 key，名字里不会出现这个字符

  /* ------------------------------------------------------------ 计算 */

  function scoresOf() {                             // 谁有几条成绩（比赛记录 + 自由成绩 + 单独录入的 PB）
    var c = {};
    var add = function (r) { if (r && r.name && r.sec) (c[r.name] = c[r.name] || []).push(r); };
    try { allResults().forEach(add); } catch (e) {}
    try { (ov().pbAdded || []).forEach(add); } catch (e) {}
    return c;
  }

  function bestCount() {
    try { return (personalBests() || []).length; } catch (e) { return 0; }
  }

  function audit() {
    var cnt = scoresOf();
    var hiddenSet = new Set(ov().hidden || []);
    var noOff = [], isRemoved = [];
    Object.keys(cnt).forEach(function (n) {
      var lv = effLevel(n) || [];
      var official = lv.indexOf('正式') >= 0;       // 成绩榜只认「正式」
      if (hiddenSet.has(n)) { isRemoved.push({ name: n, lv: lv, official: official }); return; }
      if (!official) noOff.push({ name: n, lv: lv, vis: isVisibleLevel(lv) });
    });

    var kc = {};                                    // 完全相同的成绩记了多次（同一份资料被反复通过）
    (ov().pbAdded || []).forEach(function (p) {
      if (!p || !p.name || !p.sec) return;
      var k = p.name + SEP + (p.event || '') + SEP + p.sec;
      kc[k] = (kc[k] || 0) + 1;
    });
    var dup = Object.keys(kc).filter(function (k) { return kc[k] > 1; }).map(function (k) {
      var a = k.split(SEP);
      return { name: a[0], event: a[1], n: kc[k], sec: Number(a[2]) };
    }).sort(function (x, y) { return y.n - x.n; });

    var pend = 0;
    try { pend = pendingCount() || 0; } catch (e) {}

    return { cnt: cnt, noOff: noOff, isRemoved: isRemoved, dup: dup, pend: pend,
             rosterN: (rosterList() || []).length, boardN: bestCount(),
             withScoreN: Object.keys(cnt).length };
  }

  function diag(name) {                             // 「他为什么没上榜」的结论
    var n = String(name || '').trim();
    if (!n) return null;
    var st, lv, list, onBoard = false;
    try { st = rosterStatus(n); lv = effLevel(n) || []; } catch (e) { return null; }
    list = scoresOf()[n] || [];
    try { onBoard = (personalBests() || []).some(function (r) { return r.name === n; }); } catch (e) {}

    var official = lv.indexOf('正式') >= 0;
    var known = st.inBase || st.isNew;
    var why = [];
    if (!known) why.push('名册里根本没有这个人 —— 先核对是不是名字写错了（写错会被当成另一个人）');
    if (!official && known) why.push('身份不是「正式」（现在是「' + (lv.join('、') || '空') + '」）—— 成绩榜只统计正式队员，' +
      (isVisibleLevel(lv) ? '他进得了公开名册，但成绩一条都上不了榜' : '他连公开名册都进不去'));
    if (st.removed) why.push('被列在「已移除显示」名单里（身份够也照样不显示）');
    if (!list.length && known) why.push('一条成绩记录都没有 —— 不是被封住了，是确实还没有成绩');

    return { name: n, st: st, lv: lv, list: list, official: official, known: known,
             onBoard: onBoard, why: why };
  }

  /* ------------------------------------------------------------ 渲染 */

  var ICON = function (bad) {                     // 传「是不是问题」
    return bad ? '<span style="color:var(--wheat)">⚠️</span>'
               : '<span style="color:var(--green)">✅</span>';
  };
  var MARK = function (good) { return ICON(!good); };

  function listLine(rows, fmt, empty) {
    if (!rows.length) return '<div style="padding:4px 0 6px 22px;color:var(--t3)">' + empty + '</div>';
    return '<div style="padding:6px 0 8px 22px;color:var(--t2);line-height:1.9">' +
      rows.map(fmt).join('、') + '</div>';
  }

  function checkHTML() {
    var a = audit();
    var h = [];
    var link = function (key, label) {
      return ' <a href="#" data-hcopen="' + key + '">' + (V.open === key ? '收起' : label) + '</a>';
    };

    h.push('<div class="tiny" style="line-height:2">');

    h.push('<div>' + ICON(a.noOff.length) + ' 有成绩却<b>上不了榜</b>的人：<b style="color:' +
      (a.noOff.length ? 'var(--wheat)' : 'var(--green)') + '">' + a.noOff.length + '</b> 人' +
      (a.noOff.length ? ' —— 身份不到「正式」，成绩榜一条都不显示' + link('noOff', '看名单') : '') + '</div>');
    if (V.open === 'noOff') {
      h.push(listLine(a.noOff, function (x) {
        return esc(x.name) + '<span style="color:var(--t3)">（' + esc((x.lv || []).join('、') || '未填') +
          (x.vis ? ' · 已在公开名册' : '') + '）</span>';
      }, '没有'));
    }

    h.push('<div>' + ICON(a.isRemoved.length) + ' 身份够、却被「<b>已移除显示</b>」挡着的：<b style="color:' +
      (a.isRemoved.length ? 'var(--wheat)' : 'var(--green)') + '">' + a.isRemoved.length + '</b> 人' +
      (a.isRemoved.length ? ' —— 名册里点「↺ 恢复显示」就能放回来' + link('removed', '看名单') : '') + '</div>');
    if (V.open === 'removed') {
      h.push(listLine(a.isRemoved, function (x) { return esc(x.name); }, '没有'));
    }

    h.push('<div>' + ICON(a.dup.length) + ' <b>重复成绩</b>：<b style="color:' +
      (a.dup.length ? 'var(--wheat)' : 'var(--green)') + '">' + a.dup.length + '</b> 处' +
      (a.dup.length ? ' —— 同一个人同一项被记了多次（多半是同一份资料通过了两遍）；不影响榜单显示，只是库里脏' +
        link('dup', '看明细') : '') + '</div>');
    if (V.open === 'dup') {
      h.push(listLine(a.dup, function (x) {
        return esc(x.name) + ' ' + esc(x.event || '未标注') + ' ' + esc(fmtSec(x.sec)) +
          '<span style="color:var(--t3)">（记了 ' + x.n + ' 次）</span>';
      }, '没有'));
    }

    h.push('<div>' + ICON(a.pend) + ' 本机还有 <b style="color:' +
      (a.pend ? 'var(--wheat)' : 'var(--green)') + '">' + a.pend + '</b> 处修改没同步到线上' +
      (a.pend ? ' —— 别忘了点「同步我的修改到线上」，不然别人看不到' : '') + '</div>');

    h.push('<div style="margin-top:6px;color:var(--t3)">' +
      '📊 公开名册 <b>' + a.rosterN + '</b> 人 · 成绩榜 <b>' + a.boardN + '</b> 条 · ' +
      '有成绩记录的人 <b>' + a.withScoreN + '</b></div>');

    h.push('</div>');
    h.push('<div class="tiny" style="margin-top:8px;color:var(--t3);line-height:1.7">' +
      '这些数字都是拿本机现有的数据现算的，打开就是最新的。第一项和第三项点开能看具体是谁。</div>');
    return h.join('');
  }

  function whoHTML() {
    var d = diag(V.q);
    if (!V.q.trim()) {
      return '<div class="tiny" style="color:var(--t3);padding:10px 0">' +
        '在上面输入一个名字，比如「付游」—— 会告诉你他的身份、有几条成绩、为什么没出现在榜上、要怎么改。</div>';
    }
    if (!d) return '<div class="tiny" style="color:var(--wheat)">读不到这个人的数据。</div>';

    var L = [];
    L.push('<div style="font-size:15px;font-weight:600;margin:2px 0 8px">' + esc(d.name) + '</div>');
    L.push('<div class="tiny" style="line-height:2">');

    L.push('<div>' + MARK(d.known) + ' 在名册里：<b>' + (d.known ? '是' : '否') + '</b>' +
      (d.st && d.st.isNew && !d.st.inBase ? '（队长新增）' : '') +
      (d.st && d.st.removed ? '，但被列在「已移除显示」名单里' : '') + '</div>');
    L.push('<div>' + MARK(d.official) + ' 身份：<b>' + esc((d.lv || []).join('、') || '未填') + '</b>' +
      (d.official ? '（成绩榜认这个身份）' : '（成绩榜<b>不</b>认，只认「正式」）') + '</div>');
    L.push('<div>' + MARK(d.list.length > 0) + ' 成绩记录：<b>' + d.list.length + '</b> 条' +
      (d.list.length ? '（数据是有的）' : '') + '</div>');
    L.push('<div>' + MARK(d.onBoard) + ' 出现在成绩榜上：<b>' + (d.onBoard ? '是' : '否') + '</b></div>');

    if (d.why.length) {
      L.push('<div style="margin-top:8px;padding:8px 12px;border-radius:8px;background:var(--wheat-soft);color:var(--wheat);line-height:1.85">' +
        '<b>为什么没显示：</b><br>' + d.why.map(function (x) { return '· ' + x; }).join('<br>') + '</div>');
    } else if (d.onBoard) {
      L.push('<div style="margin-top:8px;padding:8px 12px;border-radius:8px;background:var(--green-soft);color:var(--green)">' +
        '<b>一切正常</b> —— 他的成绩在榜上。如果页面上没看到，可能是浏览器缓存，刷新一下（成绩榜每 30 秒自己会查一次更新）。</div>');
    }

    if (!d.official && d.known) {
      L.push('<div class="tiny" style="margin-top:8px;color:var(--t2);line-height:1.9">' +
        '<b>怎么改：</b>数据管理 → 队员名册 → 搜索框打「' + esc(d.name) + '」→ 把「身份」改成 <b>正式</b> → ' +
        '保存名册修改 → 回到「同步」点一次「同步我的修改到线上」，等 1 分钟。</div>');
    }
    L.push('</div>');
    return L.join('');
  }

  function inner() {
    var t = V.tab;
    return '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px">' +
        '<h2 style="font-size:15px;margin:0">数据体检</h2>' +
        '<div class="chips" style="margin:0">' +
          '<div class="chip' + (t === 'check' ? ' active' : '') + '" data-hctab="check">体检</div>' +
          '<div class="chip' + (t === 'who' ? ' active' : '') + '" data-hctab="who">他为什么没上榜</div>' +
        '</div>' +
      '</div>' +
      (t === 'check' ? checkHTML()
        : '<input type="search" id="hcQ" placeholder="输入姓名，比如 付游" value="' + esc(V.q) + '" style="width:100%;margin-bottom:8px">' +
          '<div id="hcOut">' + whoHTML() + '</div>');
  }

  function bind(card) {
    [].forEach.call(card.querySelectorAll('[data-hctab]'), function (el) {
      el.onclick = function () { V.tab = el.getAttribute('data-hctab'); paint(); };
    });
    [].forEach.call(card.querySelectorAll('[data-hcopen]'), function (el) {
      el.onclick = function (e) {
        e.preventDefault();
        var k = el.getAttribute('data-hcopen');
        V.open = (V.open === k) ? '' : k;
        paint();
      };
    });
    var q = card.querySelector('#hcQ');
    if (q) {
      q.oninput = function () {                       // 边打边查，只重画结果区，不整页重渲染
        V.q = q.value;
        var out = card.querySelector('#hcOut');
        if (out) out.innerHTML = whoHTML();
      };
      if (V.q) { try { q.focus(); q.setSelectionRange(q.value.length, q.value.length); } catch (e) {} }
    }
  }

  function paint() {
    var card = document.getElementById('healthCard');
    if (!card) return;
    card.innerHTML = inner();
    bind(card);
  }

  function mount() {
    if (typeof state === 'undefined' || state.tab !== 'manage') return;
    var page = document.getElementById('page');
    if (!page || document.getElementById('healthCard')) return;
    var anchor = page.querySelector('.chips.sec');   // 数据管理里那排分区按钮
    if (!anchor) return;
    var card = document.createElement('div');
    card.id = 'healthCard';
    card.className = 'card sec';
    card.style.padding = '16px 20px';
    card.style.marginBottom = '16px';
    anchor.parentNode.insertBefore(card, anchor.nextSibling);
    paint();
  }

  window.__mtHooks = window.__mtHooks || [];
  window.__mtHooks.push(function () { mount(); });
  setTimeout(mount, 40);
})();
