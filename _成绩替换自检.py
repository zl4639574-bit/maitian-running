# -*- coding: utf-8 -*-
"""验证「新成绩自动替换个人最好成绩」：本机加一条更快的 / 更慢的，看榜单和名册卡片是否自动更新
   只写本机 localStorage；每次注入后重新加载页面（应用启动时读本机改动）；不往线上写任何东西。
"""
import base64, importlib.util, io, json, os, re, sqlite3, subprocess, shutil, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OWNER, REPO = "zl4639574-bit", "maitian-running"
SITE = "https://%s.github.io/%s/" % (OWNER, REPO)
PAY = os.path.join(os.environ.get("LOCALAPPDATA", "."), "Temp", "mt_payload.txt")
WHO = u"阿巴小洛"
EVENT = u"5000米"

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


PROBE = r"""(async () => {
 try {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const out = {};
  const click = (label) => { for (const n of document.querySelectorAll('.nav-item,[data-tab]'))
      if ((n.textContent||'').trim() === label) { n.click(); return true; } return false; };
  click('总览'); await wait(1300);
  const home = document.body.innerText.replace(/\s+/g, ' ');
  out['总览统计'] = ((home.match(/\d+\s*成绩记录/) || ['(无)'])[0]) + ' / ' + ((home.match(/\d+\s*个人最好成绩/) || ['(无)'])[0]);
  click('成绩榜'); await wait(1600);
  const rows = [].map.call(document.querySelectorAll('table.tbl tbody tr'), e => e.innerText.replace(/\s+/g,' ').trim());
  out['榜单里该队员'] = rows.filter(x => x.indexOf('__WHO__') >= 0);
  click('队员名册'); await wait(1600);
  const q = document.getElementById('rosterQ');
  if (q) { q.value = '__WHO__'; q.dispatchEvent(new Event('input', {bubbles: true})); await wait(1300); }
  const card = document.querySelector('.pcard');
  out['名册卡片'] = card ? card.innerText.replace(/\s+/g, ' ').trim().slice(0, 200) : '(没找到卡片)';
  return JSON.stringify(out);
 } catch (e) { return 'PROBE ERROR: ' + (e && e.message); }
})()""".replace('__WHO__', WHO)


def inject(c, recs):
    return c.js("(function(){var o=JSON.parse(localStorage.getItem('mt_ov_local_v1')||'{}');"
                "o.results=%s; localStorage.setItem('mt_ov_local_v1', JSON.stringify(o)); return o.results.length;})()"
                % json.dumps(recs, ensure_ascii=False))


def rec(uid, sec, fmt_, date, meet):
    return {"uid": uid, "name": WHO, "event": EVENT, "sec": sec, "fmt": fmt_, "raw": fmt_,
            "date": date, "meet": meet, "ts": 1}


def main():
    pl = payload()
    url = SITE + "captain/#t=" + pl
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

        def reload():
            for i in range(3):
                # 注意：location.assign 给「完全相同的地址」不会真的重新加载，必须带个变化的参数
                ph.goto(c, "%scaptain/?r=%d%d#t=%s" % (SITE, int(time.time()), i, pl), wait=30)
                if (c.js("location.href") or "").startswith("https://"):
                    break
            for _ in range(40):
                time.sleep(0.5)
                try:
                    if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 3:
                        return
                except Exception:
                    pass

        def case(title, recs):
            print("\n=== %s ===" % title)
            print("     注入:", inject(c, recs), "条本机成绩")
            reload()
            print("   ", c.js(PROBE))

        case(u"A. 原始状态（本机没有新成绩）", [])
        case(u"B. 加一条【更快】的 5000 米成绩 16:00（原最好 17:02）",
             [rec("t_fast", 960, "16:00", "2026-01-01", u"自检(更快)")])
        case(u"C. 换成一条【更慢】的 19:00 —— 最好成绩不应该变差",
             [rec("t_slow", 1140, "19:00", "2026-01-02", u"自检(更慢)")])
        case(u"D. 两条并存（16:00 + 19:00）—— 应该取 16:00",
             [rec("t_fast", 960, "16:00", "2026-01-01", u"自检(更快)"),
              rec("t_slow", 1140, "19:00", "2026-01-02", u"自检(更慢)")])
        print("\n     清空本机测试数据:", inject(c, []))
        reload()
        sc = c.send("Page.captureScreenshot", format="png")
        io.open(os.path.join(HERE, u"成绩替换_验证.png"), "wb").write(base64.b64decode(sc["data"]))
        c.ws.close()
    finally:
        subprocess.run(["taskkill", "/F", "/PID", str(proc.pid), "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(prof, ignore_errors=True)
    print("\n（全程只写本机 localStorage，线上没有被改动）")


if __name__ == "__main__":
    main()
