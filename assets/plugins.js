/* =====================================================================
   麦田守望长跑队 · 插件加载器
   作用：app.js 执行完后自动加载下面的插件，**串行**加载（动态 <script> 不保证执行顺序，
        小文件会先跑完 —— 这是这个项目踩过的坑，所以这里一律用 onload 排队）。
   以后要加插件，只改这个文件里的两个数组就行，网页和队长版都不用动。
   ===================================================================== */
(function () {
  if (window.__mtPluginsDone) return;
  window.__mtPluginsDone = 1;

  var R = window.APP_ROOT || '';
  var MODE = window.APP_MODE || 'view';
  var has = function (tab) { return (window.TABS ? (TABS[MODE] || []) : []).some(function (t) { return t[0] === tab; }); };

  /* 三种模式都用（成绩榜上的成绩图谱） */
  var BASE = [];
  if (!window.TABS || has('board')) BASE.push('assets/pb-chart.js');

  /* 只有队长版才加载（挂在「数据管理」里） */
  var CAP = ['assets/health-check.js', 'assets/history.js'];

  var LIST = BASE.concat(MODE === 'captain' ? CAP : []);

  (function next(i) {
    if (i >= LIST.length) return;
    var s = document.createElement('script');
    s.src = R + LIST[i] + '?t=' + Date.now();
    s.onload = function () { next(i + 1); };
    s.onerror = function () {                       // 某个插件加载失败不该拖累后面的
      if (window.console) console.warn('[插件] 加载失败：' + LIST[i] + '（其它插件继续）');
      next(i + 1);
    };
    document.head.appendChild(s);
  })(0);
})();
