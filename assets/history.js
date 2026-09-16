/* =====================================================================
   改动历史 + 一键还原（独立插件，只挂在队长版的「数据管理」页）
   目的：让"某次同步把别人的成绩盖掉了"从"查不出来"变成"能看见、能捞回来"。

   为什么能捞回来：
     app.js 每次同步成功之后，都会把这次写出去的整份数据，另存成一个新文件
     data/history/20260916-214500-ab3f.js（一次改动一个文件，永不覆盖别人）。
     这里就用 GitHub 的目录接口把这些文件列出来 —— 不需要"索引文件"，
     所以也不会出现"索引被别人覆盖了、于是历史记录丢了"这种事。

   两个动作（都要有令牌，因为要读写仓库）：
     · 看看   —— 展开这一条到底改了什么（谁的成绩、谁的资料）
     · 还原   —— 把整份数据退回那一刻。会自动先给"现在这一份"也留一个存档，
                 所以还原本身也是可以再还原回去的。

   依赖 app.js 的顶层函数：ghCfg / ghHeaders / ghGetTextSha / cloudFresh /
   ghPut / loadCloud / render / toast / esc / summarizeOv
   ===================================================================== */
(function () {
  'use strict';
  if (window.__mtHistory) return;
  window.__mtHistory = 1;
  if (window.APP_MODE !== 'captain') return;        // 只有队长版有令牌，历史也只对队长有用

  var DIR = 'data/history';
  var API = 'https://api.github.com';
  var MAX_SHOW = 30;                                // 一次最多列这么多条（够用，也不至于卡）

  var V = { list: null, err: '', busy: '', open: '', arc: null, prev: null, confirm: '', restoring: false };

  /* ------------------------------------------------------------ 小工具 */

  function cfg() { try { return ghCfg(); } catch (e) { return null; } }
  function X(s) { try { return esc(s); } catch (e) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]; }); } }
  function say(m, ms) { try { toast(m, ms); } catch (e) {} }
  function b64(s) { return btoa(unescape(encodeURIComponent(s))); }

  /** 文件名 20260916-214500-ab3f.js → 2026-09-16 21:45 */
  function whenOf(name) {
    var m = String(name).match(/^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})/);
    if (!m) return String(name).replace(/\.js$/, '');
    return m[1] + '-' + m[2] + '-' + m[3] + ' ' + m[4] + ':' + m[5];
  }
  function agoOf(name) {
    var m = String(name).match(/^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})/);
    if (!m) return '';
    var t = new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]).getTime();
    var d = Math.round((Date.now() - t) / 60000);
    if (d < 1) return '刚刚';
    if (d < 60) return d + ' 分钟前';
    if (d < 60 * 24) return Math.round(d / 60) + ' 小时前';
    var day = Math.round(d / 60 / 24);
    return day <= 31 ? (day + ' 天前') : '';
  }
  function kb(n) { return (n / 1024).toFixed(0) + ' KB'; }

  /** 「X 里有、Y 里没有」的东西。
      为什么不复用 app.js 的 summarizeOv：那个函数带方向（a→b 的"新增/删除"），
      两边调用一次，同一条记录会同时落进"新增"和"删除"，看着自相矛盾。
      这里只回答一个不带方向的问题，就不会看反。 */
  function onlyIn(x, y) {
    x = x || {}; y = y || {};
    var rk = function (r) { return r ? [r.name, r.event || r.short || r.title || '', r.sec || r.time || r.date || ''].join('·') : ''; };
    var sub = function (p, q) {
      var s = {};
      (q || []).forEach(function (r) { s[rk(r)] = 1; });
      return (p || []).map(rk).filter(function (k) { return k && !s[k]; });
    };
    var out = {};
    var R = sub(x.results, y.results);                     if (R.length) out['成绩'] = R;
    var P = sub(x.pbAdded, y.pbAdded);                     if (P.length) out['个人最好成绩'] = P;
    var C = sub(x.competitions, y.competitions);           if (C.length) out['比赛'] = C;
    var N = sub(x.newMembers, y.newMembers);               if (N.length) out['队员'] = N;
    var H = (x.hidden || []).filter(function (n) { return (y.hidden || []).indexOf(n) < 0; });
    if (H.length) out['隐藏的人'] = H;
    var M = Object.keys(x.memberEdits || {}).filter(function (k) { return (y.memberEdits || {})[k] === undefined; });
    if (M.length) out['名册资料'] = M;
    var PH = (x.photos || []).length - (y.photos || []).length;
    if (PH > 0) out['照片'] = PH;
    return out;
  }

  /** 摘要对象 → 「新增成绩 3 条（丙·5000米·1250、丁…）」这样一句话
      一定要把名字带出来：队长要回答的是"少了谁"，不是"少了几条"。 */
  function brief(ch) {
    var k = Object.keys(ch || {});
    if (!k.length) return '（这次没有实质改动）';
    return k.map(function (n) {
      var v = ch[n];
      if (Object.prototype.toString.call(v) === '[object Array]') {
        var head = v.slice(0, 3).join('、');
        return X(n) + ' ' + v.length + ' 条（' + X(head) + (v.length > 3 ? ' 等' : '') + '）';
      }
      return X(n) + ' ' + v;
    }).join(' · ');
  }

  /* ------------------------------------------------------------ 取数据 */

  function api(path) {
    var c = cfg();
    return fetch(API + '/repos/' + c.owner + '/' + c.repo + '/contents/' + path +
      '?ref=' + encodeURIComponent(c.branch || 'master') + '&t=' + Date.now(),
      { headers: ghHeaders(c), cache: 'no-store' });
  }

  function refresh() {
    if (!cfg() || !cfg().token) { V.list = []; V.err = 'no-token'; paint(); return; }
    V.busy = 'list'; V.err = ''; paint();
    api(DIR).then(function (r) {
      if (r.status === 404) return [];                    // 还没同步过：目录还不存在，这很正常
      if (!r.ok) throw new Error('读取存档目录失败 ' + r.status);
      return r.json();
    }).then(function (j) {
      if (!Array.isArray(j)) throw new Error('存档目录返回的格式不对（可能目录被改名了）');
      V.list = j.filter(function (f) { return f && /\.js$/.test(f.name || ''); })
        .map(function (f) { return { name: f.name, size: f.size || 0 }; })
        .sort(function (a, b) { return a.name < b.name ? 1 : -1; });   // 文件名带时间戳，倒序 = 最新在前
      V.busy = ''; paint();
    }).catch(function (e) {
      V.err = String((e && e.message) || e); V.busy = ''; paint();
    });
  }

  function fetchArc(name) {
    return api(DIR + '/' + encodeURIComponent(name)).then(function (r) {
      if (!r.ok) throw new Error('读不到这一条存档（' + r.status + '）');
      return r.json();
    }).then(function (d) {
      var txt = decodeURIComponent(escape(atob(String(d.content || '').replace(/\s/g, ''))));
      var i = txt.indexOf('window.TEAM_ARCHIVE');
      if (i < 0) throw new Error('这个文件不是存档');
      var j = txt.indexOf('=', i);
      var body = txt.slice(j + 1).trim();
      if (body.charAt(body.length - 1) === ';') body = body.slice(0, -1);
      return JSON.parse(body);
    });
  }

  /** 打开一条存档。
      预览"还原会发生什么"必须拿仓库里**真正最新那份 overrides** 来比：
        · 不能拿渲染出来的页面数据（那是"基础名册 + overrides"的合并结果，口径不一样，
          比出来会显示"要删掉 49 条成绩"这种吓人的假差别）
        · 所以这里先 cloudFresh() 读一次最新，再算差异。 */
  function openArc(name) {
    V.open = name; V.arc = null; V.prev = null; V.busy = 'arc-' + name; paint();
    var a = null;
    fetchArc(name).then(function (x) {
      a = x; V.arc = x;
      return cloudFresh();
    }).then(function () {
      try {
        var cur = CLOUD_OV || EMPTY_OV;
        // 补回来 = 存档有、现在没有；去掉 = 现在有、存档没有
        V.prev = { add: onlyIn(a.state, cur), del: onlyIn(cur, a.state) };
      } catch (e) { V.prev = null; }
      V.busy = ''; paint();
    }).catch(function (e) { V.busy = ''; V.arc = { err: String((e && e.message) || e) }; paint(); });
  }

  /* ------------------------------------------------------------ 还原 */

  /** 把一份完整数据写回仓库 —— 和 app.js 同步时用的是同一套乐观锁：
      带上"我读到的那一版"的 sha；被拒（别人同时在写）就重读、重试，最多 3 轮。 */
  function putState(state, msg, onTry) {
    var c = cfg();
    return cloudFresh().then(function () {
      var go = function (attempt) {
        var b64s = b64('window.TEAM_OVERRIDES = ' + JSON.stringify(state, null, 1) + ';\n');
        return ghPut(c, 'data/overrides.js', b64s, msg, (typeof FRESH_SHA === 'string' ? FRESH_SHA : '')).then(function (r) {
          if (r && r.content && r.content.sha && typeof FRESH_SHA === 'string') FRESH_SHA = r.content.sha;
          return r;
        }).catch(function (e) {
          var m = String((e && e.message) || '');
          if (attempt >= 3 || !/( 409| 422)/.test(m)) throw e;
          if (onTry) onTry(attempt + 1);
          return new Promise(function (res) { setTimeout(res, 700); }).then(function () {
            return cloudFresh();
          }).then(function () { return go(attempt + 1); });
        });
      };
      return go(1);
    });
  }

  function restore(name) {
    var c = cfg();
    if (!c || !c.token) return say('先填访问令牌再还原', 5000);
    V.restoring = true; V.busy = 'restore'; paint();
    var stamp = new Date().toISOString();
    var keepNow = null;
    fetchArc(name).then(function (a) {
      return cloudFresh().then(function () {
        keepNow = CLOUD_OV || EMPTY_OV;                        // 还原前的"现在这一份"
        var fn = stamp.slice(0, 19).replace(/[-:]/g, '').replace('T', '-') + '-' + Math.random().toString(36).slice(2, 6);
        var arch = '/* 麦田守望长跑队 · 改动存档（自动生成，请勿手改） */\nwindow.TEAM_ARCHIVE = ' +
          JSON.stringify({
            t: stamp, ver: 1, note: '还原到 ' + whenOf(name) + ' 之前，自动留的备份',
            changed: summarizeOv(a.state, keepNow), state: keepNow
          }, null, 1) + ';\n';
        // ① 先把"现在这一份"存下来 —— 这样还原本身也能再还原回去
        return ghPut(c, DIR + '/' + fn + '.js', b64(arch), '还原前备份 ' + whenOf(name)).catch(function () { /* 备份失败也继续，下面会提示 */ });
      }).then(function () {
        // ② 再把存档那份写回去
        return putState(a.state, '还原数据到 ' + whenOf(name), function (n) { V.busy = 'restore-' + n; paint(); });
      });
    }).then(function () {
      return loadCloud(true);
    }).then(function () {
      V.restoring = false; V.busy = ''; V.confirm = ''; V.open = '';
      say('✅ 已还原到 ' + whenOf(name) + ' 的数据。线上约 1 分钟后生效（含还原前的自动备份）', 9000);
      try { render(); } catch (e) {}
      refresh();
    }).catch(function (e) {
      V.restoring = false; V.busy = ''; paint();
      say('还原失败：' + String((e && e.message) || e), 9000);
    });
  }

  /* ------------------------------------------------------------ 界面 */

  function inner() {
    var h = [];
    h.push('<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:4px">');
    h.push('<b style="font-size:15px">🕘 改动历史</b>');
    h.push('<span style="color:var(--t3);font-size:12.5px">每次同步都会自动留一份存档，随时能退回去</span>');
    h.push('<span style="flex:1"></span>');
    h.push('<button class="btn-s" id="hsRefresh"' + (V.busy === 'list' ? ' disabled' : '') + '>' + (V.busy === 'list' ? '读取中…' : '↻ 刷新') + '</button>');
    h.push('</div>');

    if (V.err === 'no-token') {
      h.push('<div style="background:var(--wheat-soft);border-radius:12px;padding:10px 12px;font-size:13px;line-height:1.7">');
      h.push('还没填访问令牌 —— 历史存在 GitHub 仓库里，要读它就得有令牌。<br>');
      h.push('<b>数据管理 → 同步 → 访问令牌</b> 那一栏贴好后点保存设置，再回来点「↻ 刷新」。');
      h.push('</div>');
      return h.join('');
    }
    if (V.err) {
      h.push('<div style="background:#FBEAE7;border-radius:12px;padding:10px 12px;font-size:13px;line-height:1.7;color:var(--red)">');
      h.push('读不出来：' + X(V.err) + '<br><span style="color:var(--t2)">令牌权限够不够（要 Contents 读写）、网络通不通，先确认这两样。</span>');
      h.push('</div>');
      return h.join('');
    }
    if (!V.list) { h.push('<div style="color:var(--t3);font-size:13px">正在读取存档列表…</div>'); return h.join(''); }
    if (!V.list.length) {
      h.push('<div style="background:var(--green-soft);border-radius:12px;padding:10px 12px;font-size:13px;line-height:1.7">');
      h.push('还没有任何存档。<br>存档是在<b>点「同步我的修改到线上」成功之后</b>自动生成的 —— 去同步一次，这里就会有了。');
      h.push('</div>');
      return h.join('');
    }

    var more = V.list.length > MAX_SHOW ? ('（共 ' + V.list.length + ' 条，这里显示最近 ' + MAX_SHOW + ' 条）') : '';
    h.push('<div style="color:var(--t3);font-size:12px;margin:6px 0 8px">最近 ' + Math.min(V.list.length, MAX_SHOW) + ' 次改动，新的在上面 ' + more + '</div>');

    V.list.slice(0, MAX_SHOW).forEach(function (f) {
      var isOpen = V.open === f.name;
      var loading = V.busy === 'arc-' + f.name;
      h.push('<div style="border:1px solid var(--line);border-radius:14px;padding:10px 12px;margin-bottom:8px;' +
        (isOpen ? 'background:var(--green-soft);border-color:var(--green-line);' : '') + '">');
      h.push('<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">');
      h.push('<b style="font-size:13.5px">' + X(whenOf(f.name)) + '</b>');
      h.push('<span style="color:var(--t3);font-size:12px">' + X(agoOf(f.name)) + ' · ' + kb(f.size) + '</span>');
      h.push('<span style="flex:1"></span>');
      h.push('<button class="btn-s" data-hsopen="' + X(f.name) + '">' + (isOpen ? '收起' : '看看') + '</button>');
      h.push('<button class="btn-s" data-hsrestore="' + X(f.name) + '"' + (V.busy ? ' disabled' : '') + '>还原</button>');
      h.push('</div>');

      if (isOpen) {
        if (loading) h.push('<div style="color:var(--t3);font-size:13px;margin-top:8px">正在打开…</div>');
        else if (!V.arc) h.push('<div style="color:var(--t3);font-size:13px;margin-top:8px">…</div>');
        else if (V.arc.err) h.push('<div style="color:var(--red);font-size:13px;margin-top:8px">' + X(V.arc.err) + '</div>');
        else {
          h.push('<div style="margin-top:8px;font-size:13px;line-height:1.8">');
          if (V.arc.note) h.push('<div style="color:var(--wheat)">📌 ' + X(V.arc.note) + '</div>');
          h.push('<div>这次改了：' + brief(V.arc.changed) + '</div>');
          var st = V.arc.state || {};
          h.push('<div style="color:var(--t2);font-size:12.5px;margin-top:4px">这份存档里：成绩 ' +
            ((st.results || []).length + (st.pbAdded || []).length) + ' 条 · 名册 ' +
            (rosterCount(st)) + ' 人 · 照片 ' + ((st.photos || []).length) + ' 张</div>');
          h.push('</div>');

          if (V.prev) {
            var A = Object.keys(V.prev.add || {}), D = Object.keys(V.prev.del || {});
            h.push('<div style="margin-top:8px;background:var(--card);border:1px dashed var(--line);border-radius:12px;padding:9px 11px;font-size:12.5px;line-height:1.8">');
            h.push('<b>如果现在点还原，会发生什么：</b><br>');
            h.push(A.length ? ('<span style="color:var(--green)">＋ 补回来：' + brief(V.prev.add) + '</span><br>') : '');
            h.push(D.length ? ('<span style="color:var(--red)">－ 去掉：' + brief(V.prev.del) + '</span><br>') : '');
            h.push(!A.length && !D.length ? '<span style="color:var(--t2)">和现在一模一样，不用还原。</span>' : '');
            h.push('</div>');
          }

          if (V.confirm === f.name) {
            h.push('<div style="margin-top:8px;background:var(--wheat-soft);border-radius:12px;padding:9px 11px;font-size:12.5px;line-height:1.8">');
            h.push('<b>确认把整份数据退回 ' + X(whenOf(f.name)) + '？</b><br>');
            h.push('这一条之后的所有改动都会被覆盖掉。<br>');
            h.push('<span style="color:var(--t2)">放心：还原前会自动给「现在这一份」也留一个存档，退错了还能再退回来。</span><br>');
            h.push('<button class="btn-s" id="hsDo" style="margin-top:6px"' + (V.busy ? ' disabled' : '') + '>' +
              (V.busy && V.busy.indexOf('restore') === 0 ? '正在还原，别关页面…' : '确认还原') + '</button> ');
            h.push('<button class="btn-s" id="hsCancel">取消</button>');
            h.push('</div>');
          }
        }
      }
      h.push('</div>');
    });
    return h.join('');
  }

  function rosterCount(st) {
    var n = 0;
    try { n = (BASE.roster || []).length; } catch (e) {}
    var hid = (st.hidden || []).length;
    return Math.max(0, n + (st.newMembers || []).length - hid);
  }

  /* ------------------------------------------------------------ 挂载 */

  function paint() {
    var card = document.getElementById('historyCard');
    if (!card) return;
    card.innerHTML = inner();
    bind(card);
  }

  function bind(card) {
    var r = card.querySelector('#hsRefresh');
    if (r) r.onclick = function () { refresh(); };
    [].forEach.call(card.querySelectorAll('[data-hsopen]'), function (b) {
      b.onclick = function () {
        var n = b.getAttribute('data-hsopen');
        if (V.open === n) { V.open = ''; V.arc = null; paint(); } else { openArc(n); }
      };
    });
    [].forEach.call(card.querySelectorAll('[data-hsrestore]'), function (b) {
      b.onclick = function () {
        var n = b.getAttribute('data-hsrestore');
        V.confirm = (V.confirm === n ? '' : n);
        if (V.confirm) openArc(n); else paint();
      };
    });
    var d = card.querySelector('#hsDo');
    if (d) d.onclick = function () { if (!V.busy) restore(V.confirm); };
    var c2 = card.querySelector('#hsCancel');
    if (c2) c2.onclick = function () { V.confirm = ''; paint(); };
  }

  function mount() {
    if (typeof state === 'undefined' || state.tab !== 'manage') return;
    var page = document.getElementById('page');
    if (!page || document.getElementById('historyCard')) return;
    var anchor = page.querySelector('.chips.sec');
    if (!anchor) return;
    var card = document.createElement('div');
    card.id = 'historyCard';
    card.className = 'card sec';
    card.style.padding = '16px 20px';
    card.style.marginBottom = '16px';
    anchor.parentNode.insertBefore(card, anchor.nextSibling);
    paint();
    refresh();
  }

  window.__mtHooks = window.__mtHooks || [];
  window.__mtHooks.push(function () { mount(); });
  setTimeout(mount, 60);
})();
