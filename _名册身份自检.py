# -*- coding: utf-8 -*-
"""自检：把原始身份是「队员」的人改成「正式」后，他会不会真的出现在队员名册里。

做法：本地 http 起一份站点（不碰线上、不碰用户浏览器），在临时 Edge 里
      写一条本机草稿（王金豪：身份=正式 + 头像），再看「队员名册」渲染出来的人。
用法：python _名册身份自检.py             → 跑当前代码
      python _名册身份自检.py --dir 目录   → 站点目录（默认本目录）
"""
import argparse, importlib.util, io, json, os, socket, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)

DRAFT = {
    "memberEdits": {
        "王金豪": {"college": "林学院", "major": "", "grade": "2024",
                    "level": ["正式"], "sex": "男",
                    "photo": "images/avatars/mhmttw.jpg"}
    }
}


def http_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=HERE)
    ap.add_argument("--shot", default="")
    a = ap.parse_args()

    hp = http_port()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(hp), "--bind", "127.0.0.1"],
                           cwd=a.dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = "http://127.0.0.1:%d/captain/" % hp
    proc = prof = None
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen(url, timeout=1).read(200); break
            except Exception:
                time.sleep(0.25)
        print("本地站点：", url)

        port = ph.free_port(); proc, prof = ph.start_edge(port)
        time.sleep(2)
        with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=8) as r:
            pg = next(t for t in json.loads(r.read()) if t["type"] == "page")
        c = ph.CDP(pg["webSocketDebuggerUrl"])
        for d in ("Page.enable", "Runtime.enable", "Network.enable", "DOM.enable"):
            c.send(d)
        c.send("Network.setCacheDisabled", cacheDisabled=True)
        c.send("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=2, mobile=True)

        def load(tag):
            for _ in range(6):
                ph.goto(c, url + "?r=%d%s" % (int(time.time() * 1000) % 100000, tag), wait=25)
                for _ in range(40):
                    time.sleep(0.3)
                    try:
                        if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 3:
                            return True
                    except Exception:
                        pass
            return False

        if not load(""):
            print("!! 页面没起来"); return 1

        # 写本机草稿（只写这个临时浏览器）
        c.js("localStorage.setItem('mt_ov_local_v1', %s); 'ok'" % json.dumps(json.dumps(DRAFT, ensure_ascii=False)))
        if not load("b"):
            print("!! 第二次加载失败"); return 1

        # 切到「队员名册」
        c.js("(async()=>{const w=ms=>new Promise(r=>setTimeout(r,ms));"
             "for(const n of document.querySelectorAll('.nav-item,[data-tab]'))"
             " if((n.textContent||'').trim()==='队员名册'){n.click();break;} await w(1500); return 'ok';})()")

        res = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  await w(1200);
  const head = (document.querySelector('.sec-head') || {}).innerText || '';
  const cards = Array.from(document.querySelectorAll('.pcard'));
  const txt = cards.map(x => (x.innerText || '') + '|' + ((x.querySelector('img') || {}).src || ''));
  const hit = n => txt.filter(t => t.indexOf(n) >= 0);
  const wjh = hit('王金豪');
  return { head: head.replace(/\s+/g, ' ').trim(),
           n: cards.length,
           names: cards.map(x => ((x.querySelector('.nm') || {}).textContent || '').trim()),
           wangjihao: wjh.length ? wjh[0].slice(0, 200) : '',
           wangtao: hit('王涛').length > 0,
           levels: (function(){ const m = {}; cards.forEach(x => { const lv = (x.innerText||'').match(/正式|预备/g) || []; lv.forEach(v => m[v] = (m[v]||0)+1); }); return m; })() };
})()""")
        print(json.dumps(res, ensure_ascii=False, indent=1))

        ok1 = bool(res and res.get("wangjihao"))
        ok2 = bool(res and res.get("wangtao"))
        print("\n① 本机草稿里把王金豪（原始身份「队员」）改成「正式」→ 名册里有他：%s" % ("✅" if ok1 else "❌"))
        print("② 线上已同步的同款改动（王涛：队员→正式）→ 名册里有他：%s" % ("✅" if ok2 else "❌"))
        print("③ 名册卡片共 %s 张，身份统计 %s" % (res and res.get("n"), res and res.get("levels")))

        if a.shot:
            r = c.send("Page.captureScreenshot", format="png", captureBeyondViewport=True)
            io.open(a.shot, "wb").write(__import__("base64").b64decode(r["data"]))
            print("截图：", a.shot)
        return 0 if (ok1 and ok2) else 1
    finally:
        try:
            if proc: proc.terminate()
        except Exception:
            pass
        try:
            srv.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
