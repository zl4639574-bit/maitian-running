# -*- coding: utf-8 -*-
"""线上只读自检：成绩栏对 1:24:00 的识别（不点任何"添加/同步"，不写数据）"""
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
        r = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  for (const n of document.querySelectorAll('.nav-item,[data-tab]'))
    if ((n.textContent||'').trim() === '上传成绩') { n.click(); break; }
  await w(1200);
  const set = (el, v) => { el.value = v; el.dispatchEvent(new Event('input', {bubbles:true})); };
  const fev = document.getElementById('f_event'), fres = document.getElementById('f_result');
  if (!fev || !fres) return { err: '没找到成绩表单' };
  set(fev, '半马'); set(fres, '1:24:00'); await w(200);
  const halfF = (document.getElementById('f_resultHint').textContent || '').trim();
  set(fev, '全马'); set(fres, '4:20:00'); await w(200);
  const fullF = (document.getElementById('f_resultHint').textContent || '').trim();
  set(fev, '5000米'); set(fres, '17:02:00'); await w(200);
  const fiveK = (document.getElementById('f_resultHint').textContent || '').trim();
  set(fev, '5000米'); set(fres, '1:24:00'); await w(200);
  const warn = (document.getElementById('f_resultHint').textContent || '').trim();
  return { half: halfF, full: fullF, fiveK: fiveK, warn: warn.slice(0, 50) };
})()""")
        print(json.dumps(r, ensure_ascii=False, indent=1))
        ok = (r.get("half") == "识别为 1:24:00（半马）" and r.get("full") == "识别为 4:20:00（全马）"
              and r.get("fiveK") == "识别为 17:02（5000米）" and (r.get("warn") or "").startswith("⚠️"))
        if shot:
            r2 = c.send("Page.captureScreenshot", format="png", captureBeyondViewport=False)
            io.open(shot, "wb").write(base64.b64decode(r2["data"]))
            print("截图：", shot)
        print("\n" + ("✅ 线上成绩解析已修好：1:24:00（半马）= 1 小时 24 分；5000 米老写法不变；不匹配会提醒"
                      if ok else "❌ 线上还没更新或不符预期"))
        return 0 if ok else 1
    finally:
        try:
            if proc: proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
