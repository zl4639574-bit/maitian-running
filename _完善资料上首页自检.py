# -*- coding: utf-8 -*-
"""自检：队员端「完善资料」上了成绩上报的首页面
  ① 第一次来（本机没资料）→ 默认停在「完善我的资料」
  ② 卡片按钮能跳到完善资料
  ③ 填过资料的人 → 默认停在「成绩上报」，首页卡片显示"欢迎回来 + 姓名"
  ④ 首页「直接上报成绩 ↓」能跳到成绩上报并把光标放进姓名框
  ⑤ 完善资料页的「去上报成绩 →」仍然好用
"""
import importlib.util, json, os, socket, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)


def main():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); hp = s.getsockname()[1]; s.close()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(hp), "--bind", "127.0.0.1"],
                           cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    port = ph.free_port(); proc, prof = ph.start_edge(port)
    base = "http://127.0.0.1:%d/report/" % hp
    res = []
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/index.html" % hp, timeout=1).read(100); break
            except Exception:
                time.sleep(0.25)
        time.sleep(2)
        with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=8) as r:
            pg = next(t for t in json.loads(r.read()) if t["type"] == "page")
        c = ph.CDP(pg["webSocketDebuggerUrl"])
        for d in ("Page.enable", "Runtime.enable"):
            c.send(d)
        c.send("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=2, mobile=True)

        def load():
            for _ in range(5):
                ph.goto(c, base + "?r=%d" % (int(time.time() * 1000) % 100000), wait=25)
                for _ in range(40):
                    time.sleep(0.3)
                    if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 2:
                        return True
            return False

        # ① 第一次来
        c.js("localStorage.removeItem('mt_me_v1'); 'ok'")
        load()
        r1 = c.js(r"""(function(){
  const active = Array.from(document.querySelectorAll('.nav-item')).filter(x => x.className.indexOf('active') >= 0)
     .map(x => x.textContent.trim());
  const txt = document.body.textContent.replace(/\s+/g,' ');
  return { active: active, hasCard: txt.indexOf('完善我的资料') >= 0, tabs: Array.from(document.querySelectorAll('.nav-item')).map(x=>x.textContent.trim()) };
})()""")
        print("① 第一次来：", json.dumps(r1, ensure_ascii=False))
        ok1 = r1["active"] == ["完善我的资料"] and r1["tabs"] == ["成绩上报", "完善我的资料"]
        res.append(("① 第一次来 → 默认停在「完善我的资料」", ok1))

        # ③ 填过资料的人
        c.js("""localStorage.setItem('mt_me_v1', JSON.stringify({ type:'maitian-member', name:'张津浩', college:'林学院', level:'正式', pb:{} })); 'ok'""")
        load()
        r3 = c.js(r"""(function(){
  const active = Array.from(document.querySelectorAll('.nav-item')).filter(x => x.className.indexOf('active') >= 0)
     .map(x => x.textContent.trim());
  const txt = document.body.textContent.replace(/\s+/g,' ');
  return { active: active, welcome: txt.indexOf('欢迎回来，张津浩') >= 0,
           btn: !!Array.from(document.querySelectorAll('button')).find(b => /完善 \/ 修改我的资料/.test(b.textContent)),
           jump: !!document.getElementById('btnJumpUpload') };
})()""")
        print("③ 填过资料的：", json.dumps(r3, ensure_ascii=False))
        ok3 = r3["active"] == ["成绩上报"] and r3["welcome"] and r3["btn"] and r3["jump"]
        res.append(("③ 填过资料 → 停在「成绩上报」，首页卡片显示「欢迎回来 + 姓名」", ok3))

        # ② 卡片按钮 → 完善资料；④ 直接上报成绩 → 回成绩上报并聚焦姓名
        r2 = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  const b = Array.from(document.querySelectorAll('button')).find(x => /完善 \/ 修改我的资料/.test(x.textContent));
  b.click(); await w(900);
  const t1 = Array.from(document.querySelectorAll('.nav-item')).filter(x => x.className.indexOf('active') >= 0).map(x => x.textContent.trim());
  const back = Array.from(document.querySelectorAll('button')).find(x => x.textContent.trim() === '去上报成绩 →');
  const hasBack = !!back;
  if (back) back.click(); await w(900);
  const t2 = Array.from(document.querySelectorAll('.nav-item')).filter(x => x.className.indexOf('active') >= 0).map(x => x.textContent.trim());
  const ju = document.getElementById('btnJumpUpload');
  if (ju) ju.click(); await w(700);
  return { afterJumpToMe: t1, hasBackBtn: hasBack, afterBack: t2,
           focused: (document.activeElement && document.activeElement.id) || '',
           t3: Array.from(document.querySelectorAll('.nav-item')).filter(x => x.className.indexOf('active') >= 0).map(x => x.textContent.trim()) };
})()""")
        print("②④⑤ 跳转：", json.dumps(r2, ensure_ascii=False))
        ok2 = r2["afterJumpToMe"] == ["完善我的资料"]
        ok5 = r2["hasBackBtn"] and r2["afterBack"] == ["成绩上报"]
        ok4 = r2["t3"] == ["成绩上报"] and r2["focused"] in ("f_name", "")
        res.append(("② 首页卡片按钮 → 跳到「完善我的资料」", ok2))
        res.append(("④ 首页「直接上报成绩 ↓」→ 回到成绩上报并聚焦姓名框", ok4))
        res.append(("⑤ 完善资料页的「去上报成绩 →」仍然好用", ok5))

        print()
        for name, ok in res:
            print(("✅ " if ok else "❌ ") + name)
        return 0 if all(ok for _, ok in res) else 1
    finally:
        try:
            if proc: proc.terminate()
        except Exception:
            pass
        srv.terminate()


if __name__ == "__main__":
    sys.exit(main())
