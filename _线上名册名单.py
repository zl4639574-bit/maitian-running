# -*- coding: utf-8 -*-
"""线上只读：把展示版队员名册的名字全列出来（只读，用来跟云端数据核对）"""
import importlib.util, json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)

port = ph.free_port(); proc, prof = ph.start_edge(port)
try:
    time.sleep(2)
    with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=8) as r:
        pg = next(t for t in json.loads(r.read()) if t["type"] == "page")
    c = ph.CDP(pg["webSocketDebuggerUrl"])
    for d in ("Page.enable", "Runtime.enable"):
        c.send(d)
    for _ in range(5):
        ph.goto(c, "https://zl4639574-bit.github.io/maitian-running/?r=%d" % (int(time.time() * 1000) % 100000), wait=30)
        if (c.js("location.href") or "").startswith("https://"):
            break
    time.sleep(2)
    c.js("(async()=>{const w=ms=>new Promise(r=>setTimeout(r,ms));for(const n of document.querySelectorAll('.nav-item,[data-tab]'))"
         "if((n.textContent||'').trim()==='队员名册'){n.click();break;} await w(1500); return 1;})()")
    out = c.js(r"""(function(){
  const cards = Array.from(document.querySelectorAll('.mcard, .rcard, [data-mname]'));
  const names = cards.map(x => (x.getAttribute('data-mname') || x.querySelector('b,h3,strong') && x.querySelector('b,h3,strong').textContent || '').trim()).filter(Boolean);
  const txt = document.body.textContent.replace(/\s+/g,' ');
  const m = txt.match(/(\d+)\s*人/);
  return { cards: cards.length, names: names, hint: (m ? m[0] : '') };
})()""")
    print(json.dumps(out, ensure_ascii=False))
finally:
    try:
        proc.terminate()
    except Exception:
        pass
