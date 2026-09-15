# -*- coding: utf-8 -*-
"""线上复核 + 截图：队员端首页（第一次来 → 完善我的资料；填过的 → 成绩上报 + 欢迎卡片）"""
import importlib.util, io, json, os, sys, time, urllib.request, base64

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)

OUT = sys.argv[1] if len(sys.argv) > 1 else '手机截图'
URL = "https://zl4639574-bit.github.io/maitian-running/report/?r=%d"
port = ph.free_port(); proc, prof = ph.start_edge(port)
ok = True
try:
    time.sleep(2)
    with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=8) as r:
        pg = next(t for t in json.loads(r.read()) if t["type"] == "page")
    c = ph.CDP(pg["webSocketDebuggerUrl"])
    for d in ("Page.enable", "Runtime.enable"):
        c.send(d)
    c.send("Emulation.setDeviceMetricsOverride", width=390, height=900, deviceScaleFactor=2, mobile=True)

    def load():
        for _ in range(5):
            ph.goto(c, URL % (int(time.time() * 1000) % 100000), wait=30)
            for _ in range(40):
                time.sleep(0.4)
                if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 2:
                    return True
        return False

    def shot(name):
        c.js("window.scrollTo(0,0); 'ok'")
        time.sleep(0.5)
        r2 = c.send("Page.captureScreenshot", format="png", captureBeyondViewport=False)
        p = os.path.join(OUT, name)
        io.open(p, "wb").write(base64.b64decode(r2["data"]))
        print("截图：", p)

    active = lambda: c.js("Array.from(document.querySelectorAll('.nav-item')).filter(x=>x.className.indexOf('active')>=0).map(x=>x.textContent.trim())")

    c.js("localStorage.removeItem('mt_me_v1'); 'ok'")
    load()
    a1 = active()
    print("第一次来 →", a1)
    shot('线上队员端_第一次来_完善资料首页.png')

    c.js("""localStorage.setItem('mt_me_v1', JSON.stringify({type:'maitian-member', name:'张津浩', college:'林学院', level:'正式', pb:{'5000米':'18:35'}})); 'ok'""")
    load()
    a2 = active()
    r = c.js(r"""(function(){
  const t = document.body.textContent.replace(/\s+/g,' ');
  return { welcome: t.indexOf('欢迎回来') >= 0, jump: !!document.getElementById('btnJumpUpload'),
           btn: !!Array.from(document.querySelectorAll('button')).find(b => /完善 \/ 修改我的资料/.test(b.textContent)) };
})()""")
    print("填过资料 →", a2, json.dumps(r, ensure_ascii=False))
    shot('线上队员端_填过资料_成绩上报首页.png')

    ok = (a1 == ["完善我的资料"] and a2 == ["成绩上报"] and r["welcome"] and r["jump"] and r["btn"])
    print("\n" + ("✅ 线上队员端首页符合预期" if ok else "❌ 线上不符预期"))
    sys.exit(0 if ok else 1)
finally:
    try:
        proc.terminate()
    except Exception:
        pass
