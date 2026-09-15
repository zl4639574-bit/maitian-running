# -*- coding: utf-8 -*-
"""验证桌面副本里的网页能不能正常打开（手机视口真机跑一遍）"""
import base64, importlib.util, io, json, os, subprocess, shutil, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DST = r'E:\Desktop\麦田_今日产出_2026-09-14\01_网页系统（双击 index.html）'
spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)

PAGES = [
    (u'展示版', 'index.html'),
    (u'队长版', 'captain/index.html'),
]

CHECK = r"""
(() => {
  const out = {};
  const t = document.querySelectorAll('.tab,.nav-item,.nav a');
  out['标题'] = (document.title||'').slice(0,40);
  out['页面内容长度'] = (document.getElementById('page')||{}).innerHTML ? document.getElementById('page').innerHTML.length : 0;
  out['可见文字开头'] = ((document.getElementById('page')||{}).textContent||'').replace(/\s+/g,' ').slice(0,110);
  return JSON.stringify(out);
})()
"""


def main():
    port = ph.free_port(); proc, prof = ph.start_edge(port)
    try:
        time.sleep(2)
        with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=8) as r:
            pg = next(t for t in json.loads(r.read()) if t["type"] == "page")
        c = ph.CDP(pg["webSocketDebuggerUrl"])
        for d in ("Page.enable", "Runtime.enable", "Network.enable"):
            c.send(d)
        c.send("Network.setCacheDisabled", cacheDisabled=True)
        c.send("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=2, mobile=True)
        for label, rel in PAGES:
            url = 'file:///' + os.path.join(DST, rel).replace('\\', '/').replace(' ', '%20').replace('（', '%EF%BC%88').replace('）', '%EF%BC%89')
            c.send("Page.navigate", url=url)
            time.sleep(2.5)
            for _ in range(20):
                n = c.js("(function(){var p=document.getElementById('page');return p?p.innerHTML.length:0;})()")
                try:
                    if int(str(n).strip()) > 400:
                        break
                except Exception:
                    pass
                time.sleep(0.5)
            print('[%s] %s' % (label, c.js(CHECK)))
            r = c.send("Page.captureScreenshot", format="png", captureBeyondViewport=True)
            out = os.path.join(HERE, u'副本验证_%s.png' % label)
            io.open(out, 'wb').write(base64.b64decode(r["data"]))
            print('   截图 ->', out)
        c.ws.close()
    finally:
        subprocess.run(["taskkill", "/F", "/PID", str(proc.pid), "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(prof, ignore_errors=True)


main()
