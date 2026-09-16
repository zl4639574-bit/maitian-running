/* =====================================================================
   麦田守望长跑队 · 成绩图谱（独立插件，不改 app.js 里的任何逻辑）
   挂载位置：成绩榜 →「个人最好成绩」视图，表格上方

   视图一「队内分布」—— 选一个项目，看全队成绩的高低分布
        · 条越长 = 成绩越好；前 3 名加深；顶部给最快 / 中位 / 最慢
        · 在成绩榜搜索框里打名字，图里那一条会高亮出来（回答"我在队里什么水平"）

   视图二「进步曲线」—— 选一个项目，看这项成绩随时间的变化
        · 横轴是曾经出现过的日期，纵轴是成绩；同一个人出现多次会自动连成线
        · 只有一次记录的人画成空心点（连不成线是数据本身如此，不是画错了）

   依赖 app.js 的顶层函数：personalBests / allResults / distM / fmtSec / fmtPace / dateKey / esc
   ===================================================================== */
(function () {
  'use strict';
  if (window.__mtPbChart) return;
  window.__mtPbChart = 1;
  if (window.APP_MODE === 'report') return;          // 收集页没有成绩榜

  var LINE = ['#2F6B39', '#8A7314', '#4C7A6B', '#A9762F', '#5B7D9C', '#7A5C99', '#C0392B', '#3E8A48'];
  var SHOW_N = 16;                                   // 默认最多画多少人（人多的项目全画出来太长）
  var V = { view: 'dist', ev: '', all: false };      // 插件自己的界面状态，不碰 app.js 的 state

  /* ------------------------------------------------------------ 数据 */

  function pbRows() {                                // 成绩榜上的个人最好成绩（只含距离能算出来的）
    var a;
    try { a = personalBests() || []; } catch (e) { return []; }
    return a.filter(function (r) { return r && r.name && r.sec > 0 && distM(r.event) > 0; });
  }

  function byEvent() {
    var m = {};
    pbRows().forEach(function (r) {
      var e = r.event || '未标注';
      (m[e] = m[e] || []).push(r);
    });
    Object.keys(m).forEach(function (e) {
      m[e].sort(function (a, b) { return a.sec - b.sec; });
    });
    return m;
  }

  function evOrder(g) {                              // 人数多的排前面，默认就看项目里人最多的
    return Object.keys(g).sort(function (a, b) { return g[b].length - g[a].length; });
  }

  function trendPoints(ev) {                         // 带日期的成绩点（没日期的点画不出来，跳过）
    var pts = [];
    try {
      allResults().forEach(function (r) {
        if (!r || !r.name || !r.sec) return;
        if ((r.event || '') !== ev) return;
        var d = r.date || r.srcDate || '';
        var k = dateKey(d);
        if (!k) return;
        pts.push({ name: r.name, sec: r.sec, key: k, date: d, fmt: r.fmt || fmtSec(r.sec), src: r.srcLabel || r.src || '' });
      });
    } catch (e) { return []; }
    var best = {};                                   // 同一个人同一天有多条时只留最快的
    pts.forEach(function (p) {
      var k = p.name + '|' + p.key;
      if (!best[k] || p.sec < best[k].sec) best[k] = p;
    });
    return Object.keys(best).map(function (k) { return best[k]; });
  }

  /* ------------------------------------------------- 视图一：队内分布 */

  function distSVG(rows, full) {
    var rowH = 26, top = 6;
    var H = top + rows.length * rowH + 8;
    var sMin = full[0].sec, sMax = full[full.length - 1].sec;   // 比例按"全队"算，只显示前几名时条形长短不变形
    var span = (sMax - sMin) || 1;
    var q = String((typeof state !== 'undefined' && state.pbQ) || '').trim().toLowerCase();
    var o = [];
    o.push('<svg viewBox="0 0 680 ' + H + '" width="100%" style="display:block" role="img" aria-label="队内成绩分布">');
    o.push('<title>' + esc(full[0].event + ' · 队内成绩分布') + '</title>');
    rows.forEach(function (it) {
      var r = it.r;
      var cy = top + it.i * rowH + rowH / 2;
      var w = Math.round(296 * (0.14 + 0.86 * (sMax - r.sec) / span));
      var hit = !!q && String(r.name).toLowerCase().indexOf(q) >= 0;
      if (hit) o.push('<rect x="34" y="' + (cy - 11) + '" width="612" height="22" rx="7" style="fill:var(--wheat-soft)"/>');
      o.push('<text x="64" y="' + cy + '" text-anchor="end" dominant-baseline="central" font-size="12" style="fill:var(--t3)">' + it.rk + '</text>');
      o.push('<text x="74" y="' + cy + '" dominant-baseline="central" font-size="14"' +
        (hit ? ' font-weight="600" style="fill:var(--wheat)"' : ' style="fill:var(--t1)"') + '>' + esc(r.name) + '</text>');
      o.push('<rect x="180" y="' + (cy - 7) + '" width="' + w + '" height="14" rx="4" style="fill:' +
        (it.rk <= 3 ? 'var(--green)' : 'var(--green-3)') + '"/>');
      o.push('<text x="488" y="' + cy + '" dominant-baseline="central" font-size="14" font-weight="600" style="fill:var(--t1)">' +
        esc(r.fmt || fmtSec(r.sec)) + '</text>');
      o.push('<text x="562" y="' + cy + '" dominant-baseline="central" font-size="12" style="fill:var(--t3)">' +
        esc(fmtPace(r.sec, r.event)) + '</text>');
    });
    o.push('</svg>');
    return o.join('');
  }

  function distBlock(ev, list) {
    var mid = list[Math.floor((list.length - 1) / 2)];
    var q = String((typeof state !== 'undefined' && state.pbQ) || '').trim();
    var mine = q ? list.findIndex(function (r) { return String(r.name).indexOf(q) >= 0; }) : -1;
    var stat = list.length + ' 人 · 最快 <b>' + esc(list[0].fmt || fmtSec(list[0].sec)) + '</b>（' + esc(list[0].name) + '）' +
      ' · 中位 <b>' + esc(mid.fmt || fmtSec(mid.sec)) + '</b>' +
      ' · 最慢 ' + esc(list[list.length - 1].fmt || fmtSec(list[list.length - 1].sec));
    var mineLine = mine >= 0 ? '<div class="tiny" style="margin-top:2px;color:var(--green)">' +
      esc(list[mine].name) + ' 在这个项目排第 <b>' + (mine + 1) + '</b> / ' + list.length + '，' +
      (mine === 0 ? '就是队里最快的' : '比队内最快慢 ' + fmtSec(list[mine].sec - list[0].sec)) + '</div>' : '';

    // 人多的项目默认只画前 SHOW_N 个；搜索命中的人排在后面就自动全展开，免得"查了却看不见"
    var autoAll = mine >= SHOW_N;
    var expanded = V.all || autoAll;
    var rows = (expanded ? list : list.slice(0, SHOW_N))
      .map(function (r, i) { return { r: r, rk: i + 1, i: i }; });
    var btn = '';
    if (list.length > SHOW_N && !autoAll) {
      btn = '<div style="display:flex;justify-content:flex-end;margin-top:6px">' +
        '<button class="btn ghost sm" id="pbcMore">' +
        (expanded ? '只看前 ' + SHOW_N + ' 名' : '展开后面 ' + (list.length - SHOW_N) + ' 名') + '</button></div>';
    }

    return '<div class="tiny" style="margin:0 0 10px;line-height:1.7">' + stat + mineLine + '</div>' +
      distSVG(rows, list) + btn +
      '<div class="tiny" style="margin-top:8px;color:var(--t3)">条越长成绩越好。每项取各人最快的一次，' +
      '只有正式队员会出现在这里；在成绩榜的搜索框里打名字，图里那一条会高亮。</div>';
  }

  /* ------------------------------------------------- 视图二：进步曲线 */

  function trendSVG(ev) {
    var pts = trendPoints(ev);
    if (!pts.length) {
      return '<div style="padding:26px 0;text-align:center;color:var(--t3);font-size:13px">' +
        '这个项目还没有「带日期」的成绩记录，画不出随时间的变化。<br>' +
        '<span style="font-size:12px">（成绩单里带了比赛日期的才画得出来；队长新增比赛时填上日期就会出现在这里）</span></div>';
    }
    var xs = Array.from(new Set(pts.map(function (p) { return p.key; }))).sort(function (a, b) { return a - b; });
    var pos = {}; xs.forEach(function (k, i) { pos[k] = i; });
    var byName = {};
    pts.forEach(function (p) { (byName[p.name] = byName[p.name] || []).push(p); });
    Object.keys(byName).forEach(function (n) {
      byName[n].sort(function (a, b) { return a.key - b.key; });
    });
    var multi = Object.keys(byName).filter(function (n) { return byName[n].length > 1; });

    var secs = pts.map(function (p) { return p.sec; });
    var sMin = Math.min.apply(null, secs), sMax = Math.max.apply(null, secs);
    var pad = Math.max(2, (sMax - sMin) * 0.14);
    var lo = sMin - pad, hi = sMax + pad;
    var L = 78, Rr = 614, T = 22, B = 206, H = 252;
    var X = function (k) { return xs.length < 2 ? (L + Rr) / 2 : L + (Rr - L) * pos[k] / (xs.length - 1); };
    var Y = function (s) { return T + (B - T) * (s - lo) / (hi - lo); };

    var o = [];
    o.push('<svg viewBox="0 0 680 ' + H + '" width="100%" style="display:block" role="img" aria-label="进步曲线">');
    o.push('<title>' + esc(ev + ' 成绩随时间的变化') + '</title>');

    // 横向刻度（快的在上面）
    [0, 0.5, 1].forEach(function (t) {
      var s = lo + (hi - lo) * t, y = Y(s);
      o.push('<line x1="' + L + '" y1="' + y + '" x2="' + Rr + '" y2="' + y + '" stroke-width="0.5" style="stroke:var(--line)"/>');
      o.push('<text x="' + (L - 8) + '" y="' + y + '" text-anchor="end" dominant-baseline="central" font-size="11" style="fill:var(--t3)">' +
        esc(fmtSec(Math.round(s))) + '</text>');
    });
    // 日期刻度
    xs.forEach(function (k) {
      var s = String(k);
      var lab = s.slice(2, 4) + '.' + s.slice(4, 6) + (s.slice(6, 8) === '01' ? '' : '.' + s.slice(6, 8));
      o.push('<text x="' + X(k) + '" y="' + (B + 20) + '" text-anchor="middle" font-size="11" style="fill:var(--t3)">' + esc(lab) + '</text>');
    });
    // 折线（同一个人多次出现）
    multi.forEach(function (n, i) {
      var arr = byName[n];
      var d = arr.map(function (p) { return X(p.key) + ',' + Y(p.sec); }).join(' ');
      o.push('<polyline points="' + d + '" fill="none" stroke-width="1.6" stroke-linejoin="round" style="stroke:' + LINE[i % LINE.length] + '"/>');
    });
    // 点
    pts.forEach(function (p) {
      var many = byName[p.name].length > 1;
      var i = multi.indexOf(p.name);
      var col = many ? LINE[i % LINE.length] : 'var(--green-3)';
      o.push('<circle cx="' + X(p.key) + '" cy="' + Y(p.sec) + '" r="' + (many ? 4.5 : 3.5) + '" style="fill:' + col + '" fill-opacity="0.9"><title>' +
        esc(p.name + ' ' + p.fmt + '（' + p.date + (p.src ? ' · ' + p.src : '') + '）') + '</title></circle>');
    });
    // 连线的人标姓名：挂在各自最后一个点旁边。先纵向排开 —— 不然几个人收在同一天时标签会互相盖住；
    // 被挪动过的标签补一条很淡的引线，避免"名字和点对不上"
    var labs = multi.map(function (n, i) {
      var last = byName[n][byName[n].length - 1];
      var px = X(last.key), py = Y(last.sec);
      var right = px < 556;
      return { n: n, px: px, py: py, x: px + (right ? 8 : -8), y: py - 9,
               a: right ? 'start' : 'end', c: LINE[i % LINE.length] };
    });
    labs.sort(function (a, b) { return a.y - b.y; });
    var TOPL = T + 4, BOTL = B + 16, k2;
    for (k2 = 1; k2 < labs.length; k2++) {
      if (labs[k2].y - labs[k2 - 1].y < 15) labs[k2].y = labs[k2 - 1].y + 15;
    }
    if (labs.length && labs[labs.length - 1].y > BOTL) {      // 排到底了就整体回推，别压到日期
      labs[labs.length - 1].y = BOTL;
      for (k2 = labs.length - 2; k2 >= 0; k2--) {
        if (labs[k2 + 1].y - labs[k2].y < 15) labs[k2].y = labs[k2 + 1].y - 15;
      }
      if (labs.length && labs[0].y < TOPL) labs[0].y = TOPL;
    }
    labs.forEach(function (lb) {
      var ex = lb.a === 'start' ? lb.x - 2 : lb.x + 2;
      var ey = lb.y - 4;
      if (Math.abs(ey - lb.py) > 4) {
        o.push('<line x1="' + lb.px + '" y1="' + lb.py + '" x2="' + ex + '" y2="' + ey +
          '" stroke-width="0.8" style="stroke:' + lb.c + '" stroke-opacity="0.5" fill="none"/>');
      }
      o.push('<text x="' + lb.x + '" y="' + lb.y + '" text-anchor="' + lb.a +
        '" font-size="12" font-weight="600" style="fill:' + lb.c + '">' + esc(lb.n) + '</text>');
    });
    o.push('</svg>');

    var solo = Object.keys(byName).length - multi.length;
    return '<div class="tiny" style="margin:0 0 10px;line-height:1.7">' +
      '一共 <b>' + pts.length + '</b> 条带日期的成绩，来自 ' + Object.keys(byName).length + ' 个人；' +
      '其中 <b>' + multi.length + '</b> 人出现过两次以上（画成折线），' + solo + ' 人只出现过一次（画成空心点）。</div>' +
      o.join('') +
      '<div class="tiny" style="margin-top:8px;color:var(--t3)">点越小、越靠上 = 成绩越好。把鼠标停在点上能看是谁、哪一场。</div>';
  }

  /* ------------------------------------------------------------ 卡片 */

  function inner() {
    var g = byEvent();
    var evs = evOrder(g);
    if (!evs.length) return '';
    if (evs.indexOf(V.ev) < 0) V.ev = evs[0];

    var chips = evs.map(function (e) {
      return '<div class="chip' + (V.ev === e ? ' active' : '') + '" data-pbcev="' + esc(e) + '">' + esc(e) +
        ' <span class="n">' + g[e].length + '</span></div>';
    }).join('');

    var body = V.view === 'dist' ? distBlock(V.ev, g[V.ev]) : trendSVG(V.ev);

    return '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px">' +
        '<h2 style="font-size:15px;margin:0">成绩图谱</h2>' +
        '<div class="chips" style="margin:0">' +
          '<div class="chip' + (V.view === 'dist' ? ' active' : '') + '" data-pbcv="dist">队内分布</div>' +
          '<div class="chip' + (V.view === 'trend' ? ' active' : '') + '" data-pbcv="trend">进步曲线</div>' +
        '</div>' +
      '</div>' +
      '<div class="chips" style="margin:0 0 10px">' + chips + '</div>' +
      body;
  }

  function bind(card) {
    [].forEach.call(card.querySelectorAll('[data-pbcv]'), function (el) {
      el.onclick = function () { V.view = el.getAttribute('data-pbcv'); paint(); };
    });
    [].forEach.call(card.querySelectorAll('[data-pbcev]'), function (el) {
      el.onclick = function () { V.ev = el.getAttribute('data-pbcev'); V.all = false; paint(); };
    });
    var more = card.querySelector('#pbcMore');
    if (more) more.onclick = function () { V.all = !V.all; paint(); };
  }

  function paint() {
    var card = document.getElementById('pbChartCard');
    if (!card) return;
    card.innerHTML = inner();
    bind(card);
  }

  /* ------------------------------------------------------------ 挂载 */

  function mount() {
    if (typeof state === 'undefined') return;
    if (state.tab !== 'board' || state.comp || state.compList) return;   // 只在「个人最好成绩」视图
    var page = document.getElementById('page');
    if (!page || document.getElementById('pbChartCard')) return;
    if (!pbRows().length) return;                                        // 一条可画的都没有就不插
    var tw = page.querySelector('.tbl-wrap');
    if (!tw || !page.querySelector('table.tbl-board')) return;           // 锚点不在就说明不是这个视图
    var card = document.createElement('div');
    card.id = 'pbChartCard';
    card.className = 'card sec';
    card.style.padding = '16px 20px';
    card.style.marginBottom = '16px';
    tw.parentNode.insertBefore(card, tw);
    paint();
  }

  window.__mtHooks = window.__mtHooks || [];
  window.__mtHooks.push(function () { mount(); });
  setTimeout(mount, 30);            // 插件比 app.js 晚加载，页面已经渲染完了，补挂一次
})();
