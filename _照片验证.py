# -*- coding: utf-8 -*-
"""验证：① 照片管理区不再显示「尚未同步」（已同步的要显示已上线）② 照片墙上不再出现照片名字
用法: python _照片验证.py
"""
import base64, importlib.util, io, json, os, re, sqlite3, subprocess, shutil, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OWNER, REPO = "zl4639574-bit", "maitian-running"
SITE = "https://%s.github.io/%s/" % (OWNER, REPO)
PAY = os.path.join(os.environ.get("LOCALAPPDATA", "."), "Temp", "mt_payload.txt")

spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)


def payload():
    if os.path.exists(PAY):
        return io.open(PAY, encoding="utf-8").read().strip()
    db = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "state.db").replace("\\", "/")
    cn = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    for mid, content in cn.execute("select id, content from messages where content like '%index.html#t=%' order by id desc limit 5"):
        for m in re.finditer(r"#t=([A-Za-z0-9_\-]+)", content or ""):
            p = m.group(1)
            try:
                o = json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))
            except Exception:
                continue
            if o.get("token") and o.get("repo"):
                io.open(PAY, "w", encoding="utf-8").write(p)
                return p
    raise SystemExit("没载荷")


def wait_render(c):
    for _ in range(40):
        time.sleep(0.5)
        try:
            if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 3:
                return
        except Exception:
            pass


def main():
    url = SITE + "captain/#t=" + payload()
    port = ph.free_port(); proc, prof = ph.start_edge(port)
    try:
        time.sleep(2)
        with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=8) as r:
            pg = next(t for t in json.loads(r.read()) if t["type"] == "page")
        c = ph.CDP(pg["webSocketDebuggerUrl"])
        for d in ("Page.enable", "Runtime.enable", "Network.enable", "DOM.enable"):
            c.send(d)
        c.send("Network.setCacheDisabled", cacheDisabled=True)
        c.send("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=2, mobile=True)
        for _ in range(3):
            ph.goto(c, url, wait=30)
            if (c.js("location.href") or "").startswith("https://"):
                break
        wait_render(c)

        print("== ① 数据管理 → 照片（本机没有未同步照片时的样子）==")
        r = c.js("""(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  for (const n of document.querySelectorAll('.nav-item,[data-tab]'))
    if ((n.textContent||'').trim() === '数据管理') { n.click(); break; }
  await wait(1300);
  const ch = document.querySelector('[data-msec="photos"]'); if (ch) ch.click();
  await wait(900);
  const t = document.body.innerText;
  return JSON.stringify({
    还显示未同步标题: t.indexOf('尚未同步') >= 0 || t.indexOf('还没同步的照片') >= 0,
    显示已上线提示: /照片全部已同步上线|已上线的照片/.test(t),
    提示原文: (t.match(/(✅ 照片全部已同步上线[^\\n]*|已上线的照片：[^\\n]*)/) || ['(无)'])[0],
    本机草稿照片数: JSON.parse(localStorage.getItem('mt_ov_local_v1') || '{}').photos ? JSON.parse(localStorage.getItem('mt_ov_local_v1')).photos.length : 0,
  });
})()""")
        print("   ", r)
        sc = c.send("Page.captureScreenshot", format="png")
        io.open(os.path.join(HERE, u"照片验证_1_管理区.png"), "wb").write(base64.b64decode(sc["data"]))

        print("== ② 照片墙 → 打开相册（看有没有照片名字）==")
        r2 = c.js("""(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  for (const n of document.querySelectorAll('.nav-item,[data-tab]'))
    if ((n.textContent||'').trim() === '照片墙') { n.click(); break; }
  await wait(1500);
  const alb = document.querySelectorAll('.alb');
  const names = [].map.call(alb, e => e.textContent.replace(/\\s+/g,' ').trim());
  const first = [...alb].find(e => /2026年校运会/.test(e.textContent)) || alb[0];
  if (first) first.click();
  await wait(1800);
  const items = document.querySelectorAll('.pitem');
  const caps = document.querySelectorAll('.pitem .cap');
  return JSON.stringify({照片墙相册数: alb.length, 相册名: names.slice(0,6),
    打开相册后照片数: items.length, 照片上的名字浮层数: caps.length,
    前3个浮层文字: [].map.call(caps, e => e.textContent).slice(0,3)});
})()""")
        print("   ", r2)
        sc = c.send("Page.captureScreenshot", format="png")
        io.open(os.path.join(HERE, u"照片验证_2_相册内.png"), "wb").write(base64.b64decode(sc["data"]))
        c.ws.close()
    finally:
        subprocess.run(["taskkill", "/F", "/PID", str(proc.pid), "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(prof, ignore_errors=True)
    print("截图: 照片验证_1_管理区.png | 照片验证_2_相册内.png")


if __name__ == "__main__":
    main()
