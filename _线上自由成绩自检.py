# -*- coding: utf-8 -*-
"""线上只读：队长版 → 数据管理 → 自由成绩，看列表和「已删除的成绩」是否正常（只读，不点删/不点同步）"""
import importlib.util, json, os, sys, time, urllib.request, base64, io

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)

shot = sys.argv[1] if len(sys.argv) > 1 else ""
port = ph.free_port(); proc, prof = ph.start_edge(port)
try:
    time.sleep(2)
    with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=8) as r:
        pg = next(t for t in json.loads(r.read()) if t["type"] == "page")
    c = ph.CDP(pg["webSocketDebuggerUrl"])
    for d in ("Page.enable", "Runtime.enable"):
        c.send(d)
    c.send("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=2, mobile=True)
    for _ in range(5):
        ph.goto(c, "https://zl4639574-bit.github.io/maitian-running/captain/?r=%d" % (int(time.time() * 1000) % 100000), wait=30)
        if (c.js("location.href") or "").startswith("https://"):
            break
    for _ in range(60):
        time.sleep(0.5)
        if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 3:
            break
    r = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  for (const n of document.querySelectorAll('.nav-item,[data-tab]'))
    if ((n.textContent||'').trim() === '数据管理') { n.click(); break; }
  await w(1200);
  const c2 = Array.from(document.querySelectorAll('[data-msec]')).find(x => x.textContent.trim() === '自由成绩');
  if (c2) c2.click();
  await w(1400);
  const rows = Array.from(document.querySelectorAll('[data-resdel]'));
  const res = Array.from(document.querySelectorAll('[data-resrestore]'));
  return { 列表: rows.length, 已删除: res.length, 活数据: ov().results.length,
           删除记录: (JSON.parse(localStorage.getItem('mt_ov_local_v1') || '{}').hiddenResults || []).length };
})()""")
    print(json.dumps(r, ensure_ascii=False))
    ok = r["列表"] >= 1 and r["已删除"] >= 1
    if shot:
        c.js("window.scrollTo(0, document.body.scrollHeight*0.25); 'ok'")
        time.sleep(0.6)
        r2 = c.send("Page.captureScreenshot", format="png", captureBeyondViewport=False)
        io.open(shot, "wb").write(base64.b64decode(r2["data"]))
        print("截图：", shot)
    print("\n" + ("✅ 线上自由成绩区正常：列表 + 「已删除的成绩（可恢复）」都在" if ok else "❌ 线上不符预期"))
    sys.exit(0 if ok else 1)
finally:
    try:
        proc.terminate()
    except Exception:
        pass
