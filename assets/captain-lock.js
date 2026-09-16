/* =====================================================================
   队长版口令门（防误入）
   一句话说清楚它是干什么的、不干什么：

   ✅ 挡的是：队友（或任何人）拿到 /captain/ 这个网址，随手点进来翻数据、
      手一滑点到「同步」或「还原」——这两件事现在能改动线上数据，确实需要一道门。
   ❌ 挡不住：懂技术的人。静态网站的代码是公开的，口令校验也在浏览器里跑，
      看着源码或清掉本机存储就能绕过。
   ⇒ 真正的保护是：**别把 /captain/ 这个网址到处发**；口令只是加一道防误触的栏杆。

   口令存在本机（localStorage），只存加盐 SHA-256，不存明文、也绝不写进仓库。
   忘了口令点「忘记口令」即可 —— 只清掉这道门，令牌和本机未同步的修改都不动。
   ===================================================================== */
(function () {
  'use strict';
  if (window.__mtLockReady) return;
  window.__mtLockReady = 1;
  // ⚠️ 这里不能马上判 APP_MODE：本文件在 <head> 之后、页面里那个内联脚本之前执行，
  //    那时候 window.APP_MODE 还是 undefined（踩过：于是整道门悄无声息地不生效）。
  //    真正的判断放到下面的 setTimeout 里。

  var K = 'mt_captain_pass_v1';                     // {v, salt, h}
  var OK = 'mt_captain_unlocked';                   // sessionStorage：本次开浏览器已经过门
  var MIN = 4;

  function ls(k, d) { try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }
  function save(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function ss(k, d) { try { return sessionStorage.getItem(k) || d; } catch (e) { return d; } }
  function hex(buf) {
    var b = new Uint8Array(buf), s = '', i;
    for (i = 0; i < b.length; i++) s += (b[i] + 256).toString(16).slice(-2);
    return s;
  }
  function weak(s) {                                // 老浏览器没有 crypto.subtle 时的退化方案
    var h = 5381, i;
    for (i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0;
    return (h >>> 0).toString(16);
  }
  function hash(pass, salt) {
    if (window.crypto && crypto.subtle && window.TextEncoder) {
      return crypto.subtle.digest('SHA-256', new TextEncoder().encode(salt + '\u0001' + pass))
        .then(function (d) { return 'sha256:' + hex(d); });
    }
    return Promise.resolve('weak:' + weak(salt + '\u0001' + pass));
  }
  function rnd() {
    if (window.crypto && crypto.getRandomValues) { var a = new Uint8Array(16); crypto.getRandomValues(a); return hex(a.buffer); }
    return ('w' + Date.now().toString(16) + Math.random().toString(16).slice(2)).slice(0, 16);
  }
  function X(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]; }); }

  var gate = null, body = null, mode = '';

  function paint(html) {
    if (!gate) return;
    body.innerHTML = html;
    gate.style.display = 'flex';
    document.documentElement.classList.add('mt-locked');
    var f = body.querySelector('input');
    if (f) setTimeout(function () { try { f.focus(); } catch (e) {} }, 60);
    var e1 = body.querySelector('#mtGo');
    if (e1) e1.onclick = submit;
    var e2 = body.querySelector('#mtSkip');
    if (e2) e2.onclick = open;
    var e3 = body.querySelector('#mtForget');
    if (e3) e3.onclick = forget;
    [].forEach.call(body.querySelectorAll('input'), function (i) {
      i.onkeydown = function (ev) { if (ev.key === 'Enter') submit(); };
    });
  }

  function open() {                                 // 过门 → 起 app
    try { sessionStorage.setItem(OK, '1'); } catch (e) {}
    gate.style.display = 'none';
    document.documentElement.classList.remove('mt-locked');
    if (typeof window.__mtBootApp === 'function') window.__mtBootApp();
  }

  function ask() {
    mode = 'ask';
    paint(
      '<div style="font-size:15px;font-weight:700;margin-bottom:4px">🔒 队长版</div>' +
      '<div style="font-size:12.5px;color:var(--t2);line-height:1.7;margin-bottom:14px">' +
        '这个页面能改线上数据，先输一下队长口令。</div>' +
      '<input id="mtPass" type="password" autocomplete="current-password" placeholder="队长口令"' +
        ' style="width:100%;padding:11px 12px;border:1px solid var(--line);border-radius:12px;font-size:15px;font-family:inherit">' +
      '<div id="mtErr" style="color:var(--red);font-size:12.5px;min-height:18px;margin-top:6px"></div>' +
      '<button class="btn" id="mtGo" style="width:100%">进入</button>' +
      '<div style="text-align:center;margin-top:12px">' +
        '<a href="javascript:;" id="mtForget" style="color:var(--t3);font-size:12px">忘记口令？</a></div>'
    );
  }

  function setup() {
    mode = 'setup';
    paint(
      '<div style="font-size:15px;font-weight:700;margin-bottom:4px">🔒 给队长版设个口令</div>' +
      '<div style="font-size:12.5px;color:var(--t2);line-height:1.7;margin-bottom:14px">' +
        '这个网址谁拿到都能打开，而这里能改线上数据。设个口令挡一下手滑和好奇 —— ' +
        '<b>只挡误入，挡不住懂技术的人</b>，所以也别把 /captain/ 的网址到处发。<br>' +
        '口令只存在你自己这台设备上，不会写进仓库。</div>' +
      '<input id="mtPass" type="password" autocomplete="new-password" placeholder="设一个口令（至少 ' + MIN + ' 位）"' +
        ' style="width:100%;padding:11px 12px;border:1px solid var(--line);border-radius:12px;font-size:15px;font-family:inherit">' +
      '<input id="mtPass2" type="password" autocomplete="new-password" placeholder="再输一遍"' +
        ' style="width:100%;padding:11px 12px;border:1px solid var(--line);border-radius:12px;font-size:15px;font-family:inherit;margin-top:8px">' +
      '<div id="mtErr" style="color:var(--red);font-size:12.5px;min-height:18px;margin-top:6px"></div>' +
      '<button class="btn" id="mtGo" style="width:100%">设置并进入</button>' +
      '<button class="btn flat" id="mtSkip" style="width:100%;margin-top:8px">暂不设置，直接进入</button>' +
      '<div style="color:var(--t3);font-size:11.5px;line-height:1.7;margin-top:12px">' +
        '（先不设也行，下次打开还会问你一次）</div>'
    );
  }

  function err(m) { var e = body.querySelector('#mtErr'); if (e) e.textContent = m; }

  function submit() {
    var p1 = body.querySelector('#mtPass'), p2 = body.querySelector('#mtPass2');
    var pass = (p1 && p1.value) || '';
    if (mode === 'setup') {
      if (pass.length < MIN) return err('口令太短了，至少 ' + MIN + ' 位');
      if (!p2 || p2.value !== pass) return err('两次输的不一样');
      var salt = rnd();
      hash(pass, salt).then(function (h) {
        save(K, { v: 1, salt: salt, h: h });
        open();
      }).catch(function () { err('设口令失败（浏览器不支持加密），可以点「暂不设置」'); });
      return;
    }
    var rec = ls(K, null);
    if (!rec) return ask();
    hash(pass, rec.salt).then(function (h) {
      if (h === rec.h) { open(); return; }
      err('口令不对');
      if (p1) { p1.value = ''; p1.focus(); }
    }).catch(function () { err('校验失败，重试一次'); });
  }

  function forget() {
    var okv = window.confirm('忘记口令 → 只把「队长版口令」这道门清掉，重新进来后再设一个新的。\n\n' +
      '访问令牌、本机未同步的修改都不会动，仓库里的数据也不受影响。\n\n要继续吗？');
    if (!okv) return;
    try { localStorage.removeItem(K); sessionStorage.removeItem(OK); } catch (e) {}
    location.reload();
  }

  // 判断时机：必须等页面里那个内联脚本把 APP_MODE 和 __mtBootApp 挂上。
  // ⚠️ 别用 setTimeout(fn, 0) 等 —— 实测它会在内联脚本之前就跑（那时候 APP_MODE 还是 undefined，
  //    于是整道门悄无声息地不生效，这个坑真踩过一次）。
  //    DOMContentLoaded 是"所有内联脚本都执行完"的保证，用这个才稳。
  var decided = false;
  function decide() {
    if (decided) return;
    decided = true;
    if (window.APP_MODE !== 'captain') return;      // 不是队长版：什么都不做
    gate = document.getElementById('mtLockGate');
    if (!gate || !window.__mtBootApp) return;       // 页面没放门（比如旧版页面），照常启动
    body = document.getElementById('mtLockBody');
    if (ss(OK, '') === '1') return open();          // 这次开浏览器已经过门了
    if (ls(K, null)) return ask();
    setup();
  }
  window.__mtLockDecide = decide;                   // 备页面主动叫（本文件若被异步插入也能用）
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', decide);
  else decide();
  setTimeout(decide, 400);                          // 兜底：万一上面两条都没赶上
})();
