# -*- coding: utf-8 -*-
"""验证：① 拼音组词中不触发检索、组词结束才检索 ② 新增队员身份为空也能显示（自动按正式）
        ③ 名册区显示"还有 N 处没同步"+"立即同步"按钮（只写本机，不碰线上）
"""
import base64, importlib.util, io, json, os, re, sqlite3, subprocess, shutil, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OWNER, REPO = "zl4639574-bit", "maitian-running"
SITE = "https://%s.github.io/%s/" % (OWNER, REPO)
PAY = os.path.join(os.environ.get("LOCALAPPDATA", "."), "Temp", "mt_payload.txt")
NEWGUY = u"身份测试员"

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


def main():
    pl = payload()
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

        def load(i=0):
            for attempt in range(4):
                for _ in range(3):
                    ph.goto(c, "%scaptain/?r=%d%d%d#t=%s" % (SITE, int(time.time()), i, attempt, pl), wait=30)
                    if (c.js("location.href") or "").startswith("https://"):
                        break
                for _ in range(60):
                    time.sleep(0.5)
                    try:
                        if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 3:
                            return True
                    except Exception:
                        pass
                print("   ! 页面没出来，重试…")
                time.sleep(3)
            return False

        def tab(label, wait=1.5):
            return c.js("(async()=>{const w=ms=>new Promise(r=>setTimeout(r,ms));"
                        "for(const n of document.querySelectorAll('.nav-item,[data-tab]'))"
                        " if((n.textContent||'').trim()===%s){n.click();break;} await w(%d); return 'ok';})()"
                        % (json.dumps(label), int(wait * 1000)))

        load()
        c.js("(function(){localStorage.removeItem('mt_ov_local_v1');return 1;})()")
        load(1)

        print("═══ ① 拼音组词中不检索、组词结束才检索（队员名册页）═══")
        tab(u'队员名册')
        r = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  const q = document.getElementById('rosterQ');
  if (!q) return '没找到检索框';
  const page = document.querySelector('#page .toolbar');
  const cards0 = document.querySelectorAll('.pcard').length;
  page.dataset.mk = '1';
  q.focus();
  q.value = 'zhangjin';                                  // 模拟拼音还没上屏
  q.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true }));
  q.dispatchEvent(new Event('input', { bubbles: true }));
  await w(600);
  const tb2 = document.querySelector('#page .toolbar');
  const markerAlive = !!(tb2 && tb2.dataset.mk === '1');
  const cardsMid = document.querySelectorAll('.pcard').length;
  // 组词结束，上屏"张津浩"
  q.value = '张津浩';
  q.dispatchEvent(new CompositionEvent('compositionend', { bubbles: true }));
  await w(900);
  const el = document.querySelector('#page .toolbar');
  const afterRender = !(el && el.dataset.mk === '1');
  const cardsAfter = document.querySelectorAll('.pcard').length;
  const names = [].map.call(document.querySelectorAll('.pcard .nm'), e => e.textContent.trim()).slice(0, 4);
  return JSON.stringify({卡片数_初始: cards0, 拼音中_页面是否重渲染: markerAlive ? '否(正确)' : '是(不对)',
    拼音中_卡片数: cardsMid, 上屏后_是否重新检索渲染: afterRender ? '是(正确)' : '否(不对)',
    上屏后_卡片数: cardsAfter, 上屏后_结果: names});
})()""")
        print("   ", r)

        print("\n═══ ② 新增队员身份为空 → 自动按正式（能出现在公开名册）═══")
        c.js("(function(){var o=JSON.parse(localStorage.getItem('mt_ov_local_v1')||'{}');"
             "o.newMembers=[{uid:'test_no_lv',name:'%s',sex:'男',college:'林学院',major:'林学2101',grade:'2024',level:[],addedAt:'2026-09-14'}];"
             "localStorage.setItem('mt_ov_local_v1', JSON.stringify(o));return 1;})()" % NEWGUY)
        time.sleep(0.5)
        load(2)          # 必须重新加载页面，应用才会读到刚写进本机的数据
        tab(u'队员名册')
        r2 = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  const q = document.getElementById('rosterQ');
  if (q) { q.value = %s; q.dispatchEvent(new Event('input', {bubbles: true})); await w(1000); }
  const card = document.querySelector('.pcard');
  return JSON.stringify({名册里能否搜到: !!card, 卡片: card ? card.innerText.replace(/\s+/g,' ').slice(0,80) : '(没有)'});
})()""" % json.dumps(NEWGUY))
        print("   ", r2)

        print(u'\n═══ ③ 名册区是否提示『还有 N 处没同步』+ 有「立即同步」按钮（管理区）═══')
        tab(u'数据管理')
        c.js("(function(){var ch=document.querySelector('[data-msec=\"member\"]'); if(ch) ch.click(); return 1;})()")
        time.sleep(1)
        r3 = c.js(r"""(function(){
  const t = document.body.innerText.replace(/\s+/g, ' ');
  return JSON.stringify({提示: (t.match(/⚠️ 名册有[^。]{0,90}/) || ['(没有提示)'])[0],
    有立即同步按钮: !!document.getElementById('btnRosterSync'),
    列表里该队员: (t.match(/身份测试员[^\n]{0,40}/) || ['(没在列表里)'])[0]});
})()""")
        print("   ", r3)
        sc = c.send("Page.captureScreenshot", format="png")
        io.open(os.path.join(HERE, u"名册_检索与身份.png"), "wb").write(base64.b64decode(sc["data"]))
        c.js("(function(){localStorage.removeItem('mt_ov_local_v1');return 1;})()")
        c.ws.close()
    finally:
        subprocess.run(["taskkill", "/F", "/PID", str(proc.pid), "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(prof, ignore_errors=True)
    print("\n（只写本机，测试数据已清空，线上未被改动）")


if __name__ == "__main__":
    main()
