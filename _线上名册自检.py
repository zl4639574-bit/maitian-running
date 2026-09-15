# -*- coding: utf-8 -*-
"""线上只读自检：打开 GitHub Pages 上的队长版 → 队员名册，看改过身份的人有没有出现
   （只读，不点任何修改/同步按钮，不写任何数据）"""
import importlib.util, io, json, os, time, urllib.request, base64, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = "https://zl4639574-bit.github.io/maitian-running/captain/?r=%d"
spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)

WANT = ["王金豪", "王涛"]


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
        for attempt in range(5):
            ph.goto(c, SITE % int(time.time() * 1000 % 100000) + "#roster", wait=30)
            if (c.js("location.href") or "").startswith("https://"):
                break
        for _ in range(60):
            time.sleep(0.5)
            try:
                if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 3:
                    break
            except Exception:
                pass
        c.js("(async()=>{const w=ms=>new Promise(r=>setTimeout(r,ms));"
             "for(const n of document.querySelectorAll('.nav-item,[data-tab]'))"
             " if((n.textContent||'').trim()==='队员名册'){n.click();break;} await w(2000); return 'ok';})()")
        res = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  await w(1500);
  const cards = Array.from(document.querySelectorAll('.pcard'));
  const found = {};
  ['王金豪','王涛'].forEach(n => {
    const hit = cards.filter(x => ((x.querySelector('.nm')||{}).textContent||'').trim() === n);
    found[n] = hit.length ? { text: (hit[0].innerText||'').replace(/\s+/g,' ').slice(0,90),
                              avatar: (hit[0].querySelector('img')||{}).src || '' } : null;
  });
  return { head: ((document.querySelector('.sec-head')||{}).innerText||'').replace(/\s+/g,' ').trim(),
           n: cards.length, found: found, sync: (typeof SYNC_STATE !== 'undefined' ? SYNC_STATE : '?') };
})()""")
        print(json.dumps(res, ensure_ascii=False, indent=1))
        ok = all(res and res["found"].get(n) for n in WANT)
        print("\n线上队员名册里能查到改过身份的人：%s" % ("✅ 王金豪 + 王涛 都在" if ok else "❌ 还缺人"))
        if shot:
            r = c.send("Page.captureScreenshot", format="png", captureBeyondViewport=False)
            io.open(shot, "wb").write(base64.b64decode(r["data"]))
            print("截图：", shot)
        return 0 if ok else 1
    finally:
        try:
            if proc: proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
