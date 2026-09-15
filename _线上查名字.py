# -*- coding: utf-8 -*-
"""线上只读：在线上页面里查几个名字在不在（用来核对名册/名册管理）"""
import importlib.util, json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)

URL = sys.argv[1] if len(sys.argv) > 1 else "https://zl4639574-bit.github.io/maitian-running/?r=1"
NAMES = (sys.argv[2] if len(sys.argv) > 2 else "李志宏,王俊尧,王俊豪,王涛,王金豪,罗美晴,张津浩").split(',')
TAB = sys.argv[3] if len(sys.argv) > 3 else "队员名册"

port = ph.free_port(); proc, prof = ph.start_edge(port)
try:
    time.sleep(2)
    with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=8) as r:
        pg = next(t for t in json.loads(r.read()) if t["type"] == "page")
    c = ph.CDP(pg["webSocketDebuggerUrl"])
    for d in ("Page.enable", "Runtime.enable"):
        c.send(d)
    for _ in range(5):
        ph.goto(c, URL, wait=30)
        if (c.js("location.href") or "").startswith("http"):
            break
    time.sleep(3)
    if TAB:
        c.js("(async()=>{const w=ms=>new Promise(r=>setTimeout(r,ms));for(const n of document.querySelectorAll('.nav-item,[data-tab]'))"
             "if((n.textContent||'').trim()===%s){n.click();break;} await w(1800); return 1;})()" % json.dumps(TAB, ensure_ascii=False))
    out = c.js(r"""(function(){
  const t = document.body.textContent.replace(/\s+/g,' ');
  const m = t.match(/(\d+)\s*人/);
  return { hit: %s, count: (m?m[1]:''), len: t.length };
})()""" % json.dumps({n: None for n in NAMES}, ensure_ascii=False).replace('"None"', 'null'))
    names = c.js(r"""(function(){
  const t = document.body.textContent.replace(/\s+/g,' ');
  const o = {};
  %s.forEach(function(n){ o[n] = t.indexOf(n) >= 0; });
  return o;
})()""" % json.dumps(NAMES, ensure_ascii=False))
    print(json.dumps({"count": out.get("count"), "names": names}, ensure_ascii=False))
finally:
    try:
        proc.terminate()
    except Exception:
        pass
