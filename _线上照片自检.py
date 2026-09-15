# -*- coding: utf-8 -*-
"""线上只读自检：队长版 → 数据管理 → 照片，看新增的「照片墙上的照片（删/恢复）」有没有上线
   （只读：不点删、不点同步、不写任何东西）"""
import importlib.util, io, json, os, sys, time, urllib.request, base64

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = "https://zl4639574-bit.github.io/maitian-running/captain/?r=%d"
spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)


def main():
    shot = sys.argv[1] if len(sys.argv) > 1 else ""
    port = ph.free_port(); proc, prof = ph.start_edge(port)
    try:
        time.sleep(2)
        with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=8) as r:
            pg = next(t for t in json.loads(r.read()) if t["type"] == "page")
        c = ph.CDP(pg["webSocketDebuggerUrl"])
        for d in ("Page.enable", "Runtime.enable", "DOM.enable"):
            c.send(d)
        c.send("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=2, mobile=True)
        for _ in range(5):
            ph.goto(c, SITE % (int(time.time() * 1000) % 100000), wait=30)
            if (c.js("location.href") or "").startswith("https://"):
                break
        for _ in range(60):
            time.sleep(0.5)
            if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 3:
                break
        res = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  for (const n of document.querySelectorAll('.nav-item,[data-tab]'))
    if ((n.textContent||'').trim() === '数据管理') { n.click(); break; }
  await w(1200);
  const t = Array.from(document.querySelectorAll('[data-msec]')).find(x => x.textContent.trim() === '照片');
  if (t) t.click();
  await w(1500);
  const txt = document.getElementById('page').textContent.replace(/\s+/g, ' ');
  const m = txt.match(/照片墙上的照片（(\d+) 张）/);
  const r = txt.match(/已从照片墙移除（(\d+) 张）/);
  return { wall: m ? +m[1] : null, removed: r ? +r[1] : null,
           nDel: document.querySelectorAll('[data-phdel]').length,
           nRes: document.querySelectorAll('[data-phrestore]').length,
           albTotal: albums().reduce((a, x) => a + x.photos.length, 0),
           albums: albums().length, hasHint: txt.indexOf('把它从照片墙移除') >= 0 };
})()""")
        print(json.dumps(res, ensure_ascii=False, indent=1))
        ok = bool(res and res["wall"] and res["nDel"] == res["wall"] and res["albTotal"] == res["wall"] + (res["removed"] or 0))
        print("\n线上照片管理区有「删/恢复」：%s" % ("✅ 上线可用（照片墙 %d 张）" % (res and res["wall"]) if ok else "❌ 还没上线或数量对不上"))
        if shot:
            c.js("(function(){const h=Array.from(document.querySelectorAll('h3')).find(x=>x.textContent.indexOf('照片墙上的照片')>=0);"
                 "if(h)h.scrollIntoView({block:'start'}); return 1;})()")
            time.sleep(1.0)
            r2 = c.send("Page.captureScreenshot", format="png", captureBeyondViewport=False)
            io.open(shot, "wb").write(base64.b64decode(r2["data"]))
            print("截图：", shot)
        return 0 if ok else 1
    finally:
        try:
            if proc: proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
