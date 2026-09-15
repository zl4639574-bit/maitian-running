# -*- coding: utf-8 -*-
"""线上只读自检：① 队员端成绩上报页的姓名框没有下拉提示 ② 模板文件都能下载
   （只读，不改任何数据）"""
import importlib.util, io, json, os, sys, time, urllib.request, base64

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://zl4639574-bit.github.io/maitian-running/"
spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)

TPL = ["templates/00_guide.txt", "templates/01_队员资料收集表.xlsx",
       "templates/02_一场比赛成绩单.xlsx", "templates/03_名册批量添加.xlsx"]


def main():
    shot = sys.argv[1] if len(sys.argv) > 1 else ""
    print("① 模板文件能否下载")
    ok_tpl = True
    for f in TPL:
        url = BASE + urllib.parse.quote(f)
        try:
            r = urllib.request.urlopen(url, timeout=30)
            n = len(r.read())
        except Exception as e:
            n = -1
        good = n > 500
        ok_tpl = ok_tpl and good
        print("   %s %s  %s bytes" % ("✅" if good else "❌", f, n))

    print("② 线上成绩上报页")
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
            ph.goto(c, BASE + "report/?r=%d" % (int(time.time() * 1000) % 100000), wait=30)
            if (c.js("location.href") or "").startswith("https://"):
                break
        for _ in range(40):
            time.sleep(0.5)
            if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 2:
                break
        r = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  const fn = document.getElementById('f_name');
  const dl = Array.from(document.querySelectorAll('datalist')).map(d => d.id);
  fn.value = '张津浩'; fn.dispatchEvent(new Event('input')); await w(100);
  const good = (document.getElementById('f_nameHint') || {}).textContent || '';
  fn.value = '不存在的名字'; fn.dispatchEvent(new Event('input')); await w(100);
  const bad = (document.getElementById('f_nameHint') || {}).textContent || '';
  // 完善我的资料 页签里的「身份」三档
  for (const n of document.querySelectorAll('.nav-item,[data-tab]'))
    if ((n.textContent||'').trim() === '完善我的资料') { n.click(); break; }
  await w(1200);
  const sel = document.getElementById('me_level');
  const opts = sel ? Array.from(sel.options).map(o => o.value) : [];
  return { hasList: !!(fn && fn.getAttribute('list')), ac: fn.getAttribute('autocomplete'),
           datalists: dl, goodHintEmpty: good.trim() === '', badHint: bad.trim().slice(0, 30),
           levelOpts: opts };
})()""")
        print("   " + json.dumps(r, ensure_ascii=False))
        ok_page = (r["hasList"] is False and r["ac"] == "off" and "nameList" not in r["datalists"]
                   and r["goodHintEmpty"] and r["badHint"].startswith("⚠️")
                   and r["levelOpts"] == ["", "正式", "预备", "普通"])
        if shot:
            r2 = c.send("Page.captureScreenshot", format="png", captureBeyondViewport=False)
            io.open(shot, "wb").write(base64.b64decode(r2["data"]))
            print("   截图：", shot)
        print()
        print("✅ 线上成绩上报：姓名直接输入、无下拉、写错有提醒" if ok_page else "❌ 线上成绩上报页还没更新")
        print("✅ 模板文件都在线上（4/4）" if ok_tpl else "❌ 模板文件有缺失")
        return 0 if (ok_page and ok_tpl) else 1
    finally:
        try:
            if proc: proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    import urllib.parse
    sys.exit(main())
