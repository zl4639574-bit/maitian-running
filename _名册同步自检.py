# -*- coding: utf-8 -*-
"""名册同步自检（用真实的线上数据副本 + 临时 Edge）
  ① 身份已升级（原始「队员」→「正式」）但被「已移除」压着的人（李志宏）启动后要自动出现在名册里
  ② 当年被刻意移出显示的预备队员（王俊尧）不该被自动放回来
  ③ 点「↺ 恢复显示」后他真的进名册，而且同步载荷里 hidden 要把他扣掉（线上才真的显示）
  ④ 走"资料导入"把身份设成正式（真实用户路径）：人被「已移除」压着也要能进名册，并且同步载荷同步修正
"""
import importlib.util, json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)


def main():
    port = ph.free_port(); proc, prof = ph.start_edge(port)
    import socket, subprocess
    s = socket.socket(); s.bind(("127.0.0.1", 0)); hp = s.getsockname()[1]; s.close()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(hp), "--bind", "127.0.0.1"],
                           cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d/captain/" % hp
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

        def load(path="captain/"):
            for _ in range(6):
                ph.goto(c, "http://127.0.0.1:%d/%s?r=%d" % (hp, path, int(time.time() * 1000) % 100000), wait=25)
                for _ in range(40):
                    time.sleep(0.3)
                    if int(str(c.js("(typeof CLOUD_OV!=='undefined' && CLOUD_OV) ? 1 : 0") or 0)) == 1:
                        return True
            return False

        load()
        r1 = c.js(r"""(function(){
  const names = rosterList().map(m => m.name);
  const l = JSON.parse(localStorage.getItem('mt_ov_local_v1') || '{}');
  return { lzh: names.indexOf('李志宏') >= 0, wjy: names.indexOf('王俊尧') >= 0,
           shown: l.shown || [], n: names.length };
})()""")
        print("① 启动后：", json.dumps(r1, ensure_ascii=False))
        ok1 = r1["lzh"] and not r1["wjy"] and "李志宏" in (r1["shown"] or [])
        res.append(("① 身份升级过、被「已移除」压着的李志宏 自动回到名册；王俊尧仍不显示", ok1))

        # ③ 已移除区点「↺ 恢复显示」
        r3 = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  for (const n of document.querySelectorAll('.nav-item,[data-tab]'))
    if ((n.textContent||'').trim() === '数据管理') { n.click(); break; }
  await w(1200);
  const t = Array.from(document.querySelectorAll('[data-msec]')).find(x => x.textContent.trim() === '队员名册');
  if (t) t.click();
  await w(1500);
  const b = document.querySelector('[data-mrestore="王俊尧"]');
  const found = !!b;
  if (b) b.click();
  await w(600);
  const l = JSON.parse(localStorage.getItem('mt_ov_local_v1') || '{}');
  const inRoster = rosterList().map(m => m.name).indexOf('王俊尧') >= 0;
  return { foundBtn: found, inRoster: inRoster, shown: l.shown || [] };
})()""")
        print("③ 恢复显示：", json.dumps(r3, ensure_ascii=False))
        ok3 = r3["foundBtn"] and r3["inRoster"] and "王俊尧" in (r3["shown"] or [])
        res.append(("③ 已移除区点「↺ 恢复显示」→ 他真的进名册", ok3))

        # ④ 资料导入把身份设成正式（真实路径）：被本地 hidden 压着的人也要出来
        r4 = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  const l0 = JSON.parse(localStorage.getItem('mt_ov_local_v1') || '{}');
  l0.hidden = (l0.hidden || []).concat(['张津浩']);          // 模拟"当年被误移除"
  localStorage.setItem('mt_ov_local_v1', JSON.stringify(l0));
  return { before: rosterList().map(m => m.name).indexOf('张津浩') >= 0 };
})()""")
        load()
        before = c.js("rosterList().map(m => m.name).indexOf('张津浩') >= 0")
        r4b = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  const r = await applyMemberDoc({ type:'maitian-member', name:'张津浩', sex:'男', college:'林学院',
                                   major:'林学2101', grade:'2024', level:'正式', pb:{} });
  await w(400);
  const l = JSON.parse(localStorage.getItem('mt_ov_local_v1') || '{}');
  return { after: rosterList().map(m => m.name).indexOf('张津浩') >= 0, shown: l.shown || [],
           note: r && r.photoNote ? String(r.photoNote) : '' };
})()""")
        print("④ 资料导入（身份=正式）：", json.dumps({"before": before, "after": r4b}, ensure_ascii=False))
        ok4 = (before is False and r4b["after"] is True and "张津浩" in (r4b["shown"] or [])
               and "已把他从「已移除」里放回名册" in r4b["note"])
        res.append(("④ 资料导入身份=正式：把被「已移除」压着的人也真的放回名册", ok4))

        # ⑤ 同步载荷：hidden 必须扣掉本机 shown 的名字（线上才真的显示）
        load()
        c.js("""localStorage.setItem('mt_gh_cfg_v1', JSON.stringify({owner:'zl4639574-bit',repo:'maitian-running',branch:'master',token:'TESTTOKEN'})); 'ok'""")
        load()
        c.js(r"""(function(){
  window.__puts = [];
  window.ghRealBranch = async () => 'master';
  window.loadCloud = async () => true;
  window.ghPut = async (cfg, path, content, msg) => { window.__puts.push({path: path, content: content, msg: msg}); return {ok:true}; };
  return 'stub ok';
})()""")
        c.js("""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  for (const n of document.querySelectorAll('.nav-item,[data-tab]'))
    if ((n.textContent||'').trim() === '数据管理') { n.click(); break; }
  await w(1200);
  const c2 = Array.from(document.querySelectorAll('[data-msec]')).find(x => x.textContent.trim() === '同步');
  if (c2) c2.click();
  await w(1200);
  return 'nav ok';
})()""")
        c.js("(function(){ const b = document.getElementById('btnPush'); if (b) b.click(); return 1; })()")
        time.sleep(4)
        r5 = c.js(r"""(function(){
  const p = (window.__puts || []).filter(x => x.path === 'data/overrides.js')[0];
  if (!p) return { err: '没抓到 overrides 请求', got: (window.__puts||[]).map(x => x.path) };
  let txt = p.content;
  try { txt = decodeURIComponent(escape(atob(p.content))); } catch (e) {}
  const m = txt.match(/\{[\s\S]*\}/);
  const o = JSON.parse(m[0]);
  const h = o.hidden || [];
  return { n: h.length, hasLzh: h.indexOf('李志宏') >= 0, hasWjy: h.indexOf('王俊尧') >= 0,
           hasZjh: h.indexOf('张津浩') >= 0, shownInPayload: o.shown || null };
})()""")
        print("⑤ 同步载荷 hidden：", json.dumps(r5, ensure_ascii=False))
        ok5 = (not r5.get("err")) and (not r5["hasLzh"]) and (not r5["hasWjy"]) and (not r5["hasZjh"]) and r5["n"] >= 15
        res.append(("⑤ 同步写出去的 hidden 里没有了这三个名字（线上从此真的显示）", ok5))

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
