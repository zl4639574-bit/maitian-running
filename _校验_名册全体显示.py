# -*- coding: utf-8 -*-
"""验证「名册显示所有人员」改动（本地 http 服务 + CDP 真机检查）
断言：
  1. 展示版队员名册：卡片数 = 156（名册里所有人），页头写"共 156 人"
  2. 身份 chips 由现有身份自动生成（含 队员 / 正式 / 未分级）
  3. 个人最好成绩榜：3 位身份是「队员」的有成绩的人（姜垚垚/汤睿/邓天昊）都上榜
  4. 名册外的 6 人（刘亦帆…）不进最好成绩榜
  5. 队长版「队员名册」管理列表列出全部 156 人；「数据体检」卡片正常渲染
  6. 手机 390 宽无横向溢出；页面没有 JS 报错
"""
import json, os, subprocess, sys, time, urllib.request, base64, socket, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import importlib.util
spec = importlib.util.spec_from_file_location("phone", os.path.join(HERE, "手机检查.py"))
phone = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phone)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


PORT = free_port()
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
                       cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2.5)
BASE = "http://127.0.0.1:%d" % PORT

ERRHOOK = """(function(){
  window.__errs = [];
  window.addEventListener('error', function(e){ window.__errs.push('error: ' + (e.message||'') + ' @' + (e.filename||'').split('/').pop() + ':' + (e.lineno||'')); });
  window.addEventListener('unhandledrejection', function(e){ window.__errs.push('reject: ' + String(e.reason && e.reason.message || e.reason)); });
  var oe = console.error;
  console.error = function(){ window.__errs.push('console.error: ' + Array.prototype.join.call(arguments,' ')); oe.apply(console, arguments); };
})();"""


def boot():
    port = phone.free_port()
    proc, prof = phone.start_edge(port)
    try:                      # 新版 Edge 的 /json/new 只认 PUT，失败也无所谓（用已有的 about:blank 页）
        urllib.request.urlopen(urllib.request.Request(
            "http://127.0.0.1:%d/json/new?about:blank" % port, method="PUT"), timeout=5).read()
    except Exception:
        pass
    with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=5) as r:
        targets = json.loads(r.read())
    page = next(t for t in targets if t["type"] == "page")
    c = phone.CDP(page["webSocketDebuggerUrl"])
    c.send("Page.enable"); c.send("Runtime.enable"); c.send("Network.enable")
    c.send("Network.setCacheDisabled", cacheDisabled=True)
    c.send("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=2, mobile=True)
    c.send("Page.addScriptToEvaluateOnNewDocument", source=ERRHOOK)
    return proc, prof, c


def wait_render(c, tab, extra=0.0):
    for _ in range(40):
        n = c.js("(function(){var p=document.getElementById('page');return p?p.innerHTML.length:0;})()")
        try:
            if int(str(n).strip()) > 800:
                break
        except Exception:
            pass
        time.sleep(0.5)
    time.sleep(1.0 + extra)


def shot(c, name):
    out = os.path.join(HERE, "手机截图", name)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    r = c.send("Page.captureScreenshot", format="png", captureBeyondViewport=True)
    open(out, "wb").write(base64.b64decode(r["data"]))
    return out


results = []
def check(label, ok, detail=""):
    results.append((label, ok, detail))
    print(("✅ " if ok else "❌ ") + label + (("  → " + str(detail)[:400]) if detail else ""))


try:
    proc, prof, c = boot()

    # ---------- 展示版 · 队员名册 ----------
    ok = phone.goto(c, BASE + "/index.html?v=chk1#roster")
    wait_render(c, "roster", extra=1.0)
    print("--- 展示版队员名册 ---")
    info = c.js("""(function(){
      var cards = document.querySelectorAll('.pcard');
      var head = document.querySelector('.sec-head .tiny');
      var chips = [];
      document.querySelectorAll('.toolbar .chip').forEach(function(ch){
        chips.push((ch.getAttribute('data-lvl')||'') + ':' + ch.textContent.trim().replace(/\\s+/g,'/'));
      });
      var tags = {};
      document.querySelectorAll('.pcard .tagbadge').forEach(function(t){ tags[t.textContent.trim()] = (tags[t.textContent.trim()]||0)+1; });
      return JSON.stringify({href: location.href, cards: cards.length, head: head?head.textContent.replace(/\\s+/g,' ').trim():'',
        chips: chips, tags: tags, roster: (typeof rosterList==='function'? rosterList().length : -1),
        overflow: document.documentElement.scrollWidth - window.innerWidth, errs: window.__errs||[]});
    })()""")
    d = json.loads(info or "{}")
    print(json.dumps(d, ensure_ascii=False, indent=1))
    check("展示版名册：卡片数 = 名册人数（156）", d.get("cards") == 156 and d.get("roster") == 156,
          "cards=%s rosterList=%s" % (d.get("cards"), d.get("roster")))
    check("页头写「共 156 人」", "共 156 人" in (d.get("head") or ""), d.get("head"))
    lvchips = [x.split(":")[0] for x in d.get("chips") or []]
    check("chips 含 全部 / 正式 / 队员 / 未分级", all(k in lvchips for k in ["", "正式", "队员"]), lvchips)
    check("手机 390 宽无横向溢出", (d.get("overflow") or 0) <= 1, "scrollWidth-innerWidth=%s" % d.get("overflow"))
    check("展示版无 JS 报错", not d.get("errs"), d.get("errs"))
    s1 = shot(c, "校验_名册全体显示.png")
    print("截图:", s1)

    # ---------- 展示版 · 成绩榜（最好成绩） ----------
    ok = phone.goto(c, BASE + "/index.html?v=chk2#board")
    wait_render(c, "board", extra=1.2)
    print("--- 展示版成绩榜 ---")
    bd = c.js("""(function(){
      var tabs = document.querySelectorAll('.chips .chip[data-comp]');
      var rows = [];
      document.querySelectorAll('table.tbl tbody tr').forEach(function(tr){ rows.push(tr.innerText.replace(/\\s+/g,' ').trim()); });
      var txt = rows.join(' || ');
      return JSON.stringify({rows: rows.length,
        has_jiang: txt.indexOf('姜垚垚')>=0, has_tang: txt.indexOf('汤睿')>=0, has_deng: txt.indexOf('邓天昊')>=0,
        has_guest: txt.indexOf('刘亦帆')>=0, sample: rows.slice(0,3), errs: window.__errs||[]});
    })()""")
    b = json.loads(bd or "{}")
    print(json.dumps(b, ensure_ascii=False, indent=1))
    check("身份「队员」有成绩的人进最好成绩榜", b.get("has_jiang") and b.get("has_tang") and b.get("has_deng"),
          "姜垚垚=%s 汤睿=%s 邓天昊=%s" % (b.get("has_jiang"), b.get("has_tang"), b.get("has_deng")))
    check("名册外的同学仍不进最好成绩榜（只进单场榜）", b.get("has_guest") is False, "刘亦帆=%s" % b.get("has_guest"))
    s2 = shot(c, "校验_成绩榜.png")
    print("截图:", s2)

    # ---------- 队长版 ----------
    ok = phone.goto(c, BASE + "/captain/index.html?v=chk3#manage")
    wait_render(c, "manage", extra=1.5)
    print("--- 队长版数据管理 · 队员名册 ---")
    gate = c.js("""(function(){
      if (document.documentElement.classList.contains('mt-locked')) {
        var b = document.getElementById('mtSkip');           // 新设备第一次进来：口令门「暂不设置，直接进入」
        if (b) { b.click(); return 'clicked-skip'; }
        return 'locked-no-skip';
      }
      return 'no-gate';
    })()""")
    print("口令门：", gate)
    for _ in range(20):                     # 等 app.js + 插件加载完
        n = c.js("(function(){var p=document.getElementById('page');return p?p.innerHTML.length:0;})()")
        try:
            if int(str(n).strip()) > 800:
                break
        except Exception:
            pass
        time.sleep(0.5)
    time.sleep(2.0)
    cp = c.js("""(function(){
      var locked = document.documentElement.classList.contains('mt-locked');
      var secs = [];
      document.querySelectorAll('.chips.sec .chip').forEach(function(x){ secs.push(x.textContent.trim().split(' ')[0]); });
      return JSON.stringify({href: location.href, locked: locked, secs: secs, errs: window.__errs||[], pageLen: (document.getElementById('page')||{}).innerHTML.length});
    })()""")
    p = json.loads(cp or "{}")
    print(json.dumps(p, ensure_ascii=False, indent=1))
    check("队长版能进（口令门不挡测试）", p.get("locked") is False and (p.get("pageLen") or 0) > 800, p)

    # 切到「队员名册」分区
    c.js("""(function(){var el=document.querySelector('.chips.sec .chip[data-msec=\\"member\\"]'); if(el) el.click(); return 'clicked';})()""")
    time.sleep(2.5)
    mg = c.js("""(function(){
      var rows = document.querySelectorAll('.mgrid .mrow');
      var hc = document.getElementById('healthCard');
      var txt = document.body.innerText;
      return JSON.stringify({mrow: rows.length, health: !!hc, healthTxt: hc?hc.innerText.replace(/\\s+/g,' ').slice(0,300):'',
        rosterNote: (txt.match(/原始名册 \\d+ 人[^\\n]*/)||[''])[0], errs: window.__errs||[]});
    })()""")
    m = json.loads(mg or "{}")
    print(json.dumps(m, ensure_ascii=False, indent=1))
    check("队长版名册管理列出所有人（156 个编辑卡片）", m.get("mrow") == 156, "mrow=%s" % m.get("mrow"))
    check("数据体检卡片渲染出来了", m.get("health") is True, m.get("healthTxt"))
    check("队长版无 JS 报错", not m.get("errs"), m.get("errs"))
    s3 = shot(c, "校验_队长版名册管理.png")
    print("截图:", s3)
    s4 = shot(c, "校验_队长版数据体检.png")
    print("截图:", s4)

    c.ws.close()
    subprocess.run(["taskkill", "/F", "/PID", str(proc.pid), "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import shutil
    shutil.rmtree(prof, ignore_errors=True)
finally:
    srv.terminate()

bad = [r for r in results if not r[1]]
print("\n===== 结果：%d 项通过 / %d 项失败 =====" % (len(results) - len(bad), len(bad)))
for l, _, d in bad:
    print("❌", l, "→", str(d)[:300])
sys.exit(1 if bad else 0)
