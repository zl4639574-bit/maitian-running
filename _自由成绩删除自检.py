# -*- coding: utf-8 -*-
"""自由成绩「删」自检（用真实线上数据副本 + 临时 Edge）
  ① 列表里能看到线上已发布的成绩，「已删除的成绩」也列得出来
  ② 点「删」→ 真的从列表消失、本机记下删除、进「已删除」列表
  ③ 点「↺ 恢复」→ 真的回到列表，本机记下"恢复"
  ④ 同步载荷：删掉的成绩不进 results、key 进 hiddenResults；恢复过的 key 从 hiddenResults 里扣掉
  ⑤ 本机自己发布的成绩点「删」→ 直接从本机列表里删掉
"""
import importlib.util, json, os, socket, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)

JS_NAV = r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  for (const n of document.querySelectorAll('.nav-item,[data-tab]'))
    if ((n.textContent||'').trim() === '数据管理') { n.click(); break; }
  await w(1200);
  const c2 = Array.from(document.querySelectorAll('[data-msec]')).find(x => x.textContent.trim() === '自由成绩');
  if (c2) c2.click();
  await w(1200);
  return { rows: document.querySelectorAll('[data-resdel]').length,
           removed: document.querySelectorAll('[data-resrestore]').length };
})()"""


def main():
    port = ph.free_port(); proc, prof = ph.start_edge(port)
    s = socket.socket(); s.bind(("127.0.0.1", 0)); hp = s.getsockname()[1]; s.close()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(hp), "--bind", "127.0.0.1"],
                           cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    res = []
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/index.html" % hp, timeout=1).read(100); break
            except Exception:
                time.sleep(0.25)
        time.sleep(2)
        with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=8) as r:
            pg = next(t for t in json.loads(r.read()) if t["type"] == "page")
        c = ph.CDP(pg["webSocketDebuggerUrl"])
        for d in ("Page.enable", "Runtime.enable", "DOM.enable"):
            c.send(d)
        c.js("window.confirm = function () { return true; }; 'ok'")

        def load():
            for _ in range(6):
                ph.goto(c, "http://127.0.0.1:%d/captain/?r=%d" % (hp, int(time.time() * 1000) % 100000), wait=25)
                for _ in range(40):
                    time.sleep(0.3)
                    if int(str(c.js("(typeof CLOUD_OV!=='undefined' && CLOUD_OV) ? 1 : 0") or 0)) == 1:
                        return True
            return False

        load()
        r1 = c.js(JS_NAV)
        st0 = c.js("({ live: ov().results.length, removed: removedResults().length })")
        print("① 列表：", json.dumps(dict(r1, **st0), ensure_ascii=False))
        ok1 = r1["rows"] >= 1 and st0["removed"] >= 1
        res.append(("① 线上已发布的自由成绩和「已删除的成绩」都能列出来", ok1))

        # ② 点删（第一行 = 线上那条）
        r2 = c.js(r"""(function(){
  const b = document.querySelector('[data-resdel]');
  const key = b.dataset.resdel;
  b.click();
  const l = JSON.parse(localStorage.getItem('mt_ov_local_v1') || '{}');
  return { key: key, live: ov().results.length, removed: removedResults().length,
           hidden: l.hiddenResults || [], rowsNow: document.querySelectorAll('[data-resdel]').length,
           removedRows: document.querySelectorAll('[data-resrestore]').length };
})()""")
        print("② 点删：", json.dumps(r2, ensure_ascii=False))
        ok2 = (r2["live"] == st0["live"] - 1 and r2["key"] in (r2["hidden"] or [])
               and r2["removed"] == st0["removed"] + 1)
        res.append(("② 点「删」→ 真的从列表消失、进「已删除」、本机记下删除", ok2))

        # ③ 点恢复（恢复刚删的那条：它只是本机删的，云端没记录 → 恢复后 shownResults 可以为空）
        r3 = c.js("""(function(){
  const key = '%s';
  const b = document.querySelector('[data-resrestore="' + key + '"]');
  if (!b) return { err: '没找到恢复按钮' };
  b.click();
  const l = JSON.parse(localStorage.getItem('mt_ov_local_v1') || '{}');
  return { key: key, live: ov().results.length, removed: removedResults().length,
           hidden: l.hiddenResults || [], shown: l.shownResults || [] };
})()""" % r2["key"])
        print("③ 点恢复：", json.dumps(r3, ensure_ascii=False))
        ok3 = (not r3.get("err")) and r3["live"] == st0["live"] and r2["key"] not in (r3["hidden"] or [])
        res.append(("③ 点「↺ 恢复」→ 真的回到列表", ok3))

        # ③b 恢复"云端记着删过"的那条 → 必须写进 shownResults（否则同步后又被云端记录藏起来）
        r3b = c.js("""(function(){
  const key = 'rmu114vax_1_vq0n';                 // 云端 hiddenResults 里的一条
  const b = document.querySelector('[data-resrestore="' + key + '"]');
  if (!b) return { err: '没找到恢复按钮' };
  b.click();
  const l = JSON.parse(localStorage.getItem('mt_ov_local_v1') || '{}');
  return { key: key, live: ov().results.length, shown: l.shownResults || [],
           inList: ov().results.some(r => resultKey(r) === key) };
})()""")
        print("③b 恢复云端记过删的：", json.dumps(r3b, ensure_ascii=False))
        ok3b = (not r3b.get("err")) and r3b["inList"] and r3b["key"] in (r3b["shown"] or [])

        res.append(("③b 恢复云端记着删过的那条 → 写进 shownResults，列表里也回来了", ok3b))

        # ④ 同步载荷
        c.js("localStorage.setItem('mt_gh_cfg_v1', JSON.stringify({owner:'zl4639574-bit',repo:'maitian-running',branch:'master',token:'TESTTOKEN'})); 'ok'")
        load()
        c.js(r"""(function(){
  window.__puts = [];
  window.ghRealBranch = async () => 'master';
  window.loadCloud = async () => true;
  window.ghPut = async (cfg, path, content, msg) => { window.__puts.push({path: path, content: content}); return {ok:true}; };
  return 'stub ok';
})()""")
        # 先删一条线上成绩，再同步
        c.js(JS_NAV)
        r4a = c.js("""(function(){
  const b = document.querySelector('[data-resdel]');
  const k = b ? b.dataset.resdel : '';
  if (b) b.click();
  return { key: k, live: ov().results.length };
})()""")
        c.js("""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  const c2 = Array.from(document.querySelectorAll('[data-msec]')).find(x => x.textContent.trim() === '同步');
  if (c2) c2.click();
  await w(1200);
  return 'nav sync';
})()""")
        c.js("(function(){ const b = document.getElementById('btnPush'); if (b) b.click(); return 1; })()")
        time.sleep(4)
        r4 = c.js(r"""(function(){
  const p = (window.__puts || []).filter(x => x.path === 'data/overrides.js')[0];
  if (!p) return { err: '没抓到同步请求' };
  let txt = p.content;
  try { txt = decodeURIComponent(escape(atob(p.content))); } catch (e) {}
  const m = txt.match(/\{[\s\S]*\}/);
  const o = JSON.parse(m[0]);
  const keys = (o.results || []).map(r => r.uid || (r.name + '|' + r.sec));
  return { results: keys.length, hasDeleted: keys.indexOf(%s) >= 0,
           hiddenHas: (o.hiddenResults || []).indexOf(%s) >= 0 };
})()""" % (json.dumps(r4a["key"]), json.dumps(r4a["key"])))
        print("④ 同步载荷：", json.dumps(dict(r4a, **r4), ensure_ascii=False))
        ok4 = (not r4.get("err")) and r4["results"] == r4a["live"] and (not r4["hasDeleted"]) and r4["hiddenHas"]
        res.append(("④ 同步写出去的 results 里没有它、hiddenResults 里有它", ok4))

        # ⑤ 本机自己发布的成绩：点删 → 直接删掉
        r5 = c.js(r"""(function(){
  const l = JSON.parse(localStorage.getItem('mt_ov_local_v1') || '{}');
  l.results = (l.results || []).concat([{ uid: 'test_local_1', name: '测试跑者', event: '5000米', sec: 1115,
                                          fmt: '18:35', date: '2026.09.15', meet: '本机测试' }]);
  localStorage.setItem('mt_ov_local_v1', JSON.stringify(l));
  return 'ok';
})()""")
        load()
        c.js(JS_NAV)
        r5b = c.js(r"""(function(){
  const btns = Array.from(document.querySelectorAll('[data-resdel]'));
  const b = btns.filter(x => x.dataset.resdel === 'test_local_1')[0];
  if (!b) return { err: '本机那条没出现在列表里' };
  b.click();
  const l = JSON.parse(localStorage.getItem('mt_ov_local_v1') || '{}');
  return { localLeft: (l.results || []).length, has: (l.results || []).some(x => x.uid === 'test_local_1') };
})()""")
        print("⑤ 本机成绩：", json.dumps(r5b, ensure_ascii=False))
        ok5 = (not r5b.get("err")) and r5b["localLeft"] == 0 and r5b["has"] is False
        res.append(("⑤ 本机自己发布的那条点「删」→ 直接从本机删掉", ok5))

        print()
        for name, ok in res:
            print(("✅ " if ok else "❌ ") + name)
        return 0 if all(ok for _, ok in res) else 1
    finally:
        try:
            if proc: proc.terminate()
        except Exception:
            pass
        srv.terminate()


if __name__ == "__main__":
    sys.exit(main())
