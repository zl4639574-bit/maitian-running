# -*- coding: utf-8 -*-
"""自检：照片墙的删/恢复
   做法：把站点拷到临时目录 → 在临时目录的 data/overrides.js 里塞一条「云端已删的照片」
        → 本地 http 起站 + 临时 Edge 打开，检查照片墙张数、管理区的「删」「↺ 恢复」是否真的生效。
   全程只动临时副本，不碰线上、不碰用户浏览器。
"""
import importlib.util, io, json, os, re, shutil, socket, subprocess, sys, tempfile, time, urllib.request, base64

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)

DEL_ID = "up_1789462146293_4.jpg"          # 临时副本里当作「云端已删」的那张（26年杨马）


def build_site(dst):
    os.makedirs(os.path.join(dst, "images"), exist_ok=True)
    for f in ("index.html", "guide.txt"):
        p = os.path.join(HERE, f)
        if os.path.exists(p):
            shutil.copyfile(p, os.path.join(dst, f))
    for d in ("assets", "data", "captain", "report"):
        shutil.copytree(os.path.join(HERE, d), os.path.join(dst, d), dirs_exist_ok=True)
    shutil.copyfile(os.path.join(HERE, "images", "photos.js"), os.path.join(dst, "images", "photos.js"))
    # 云端 overrides 里加一条 hiddenPhotos（模拟"以前删过一张，已同步到线上"）
    p = os.path.join(dst, "data", "overrides.js")
    s = io.open(p, encoding="utf-8").read()
    d = json.loads(re.search(r'window\.TEAM_OVERRIDES\s*=\s*(\{.*\})\s*;?\s*$', s, re.S).group(1))
    d["hiddenPhotos"] = [DEL_ID]
    io.open(p, "w", encoding="utf-8").write("window.TEAM_OVERRIDES = " + json.dumps(d, ensure_ascii=False, indent=1) + ";\n")
    return len(d.get("photos") or [])


def main():
    tmp = tempfile.mkdtemp(prefix="mt_photos_")
    ncloud = build_site(tmp)
    s = socket.socket(); s.bind(("127.0.0.1", 0)); hp = s.getsockname()[1]; s.close()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(hp), "--bind", "127.0.0.1"],
                           cwd=tmp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = "http://127.0.0.1:%d/captain/" % hp
    proc = None
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/index.html" % hp, timeout=1).read(100); break
            except Exception:
                time.sleep(0.25)
        port = ph.free_port(); proc, prof = ph.start_edge(port)
        time.sleep(2)
        with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=8) as r:
            pg = next(t for t in json.loads(r.read()) if t["type"] == "page")
        c = ph.CDP(pg["webSocketDebuggerUrl"])
        for d in ("Page.enable", "Runtime.enable", "DOM.enable"):
            c.send(d)
        c.send("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=2, mobile=True)

        def load(tag=""):
            for _ in range(5):
                ph.goto(c, url + "?r=%d%s" % (int(time.time() * 1000) % 100000, tag), wait=25)
                for _ in range(40):
                    time.sleep(0.3)
                    if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 3:
                        return True
            return False

        if not load():
            print("!! 页面没起来"); return 1

        def tab(label):
            return c.js("(async()=>{const w=ms=>new Promise(r=>setTimeout(r,ms));"
                        "for(const n of document.querySelectorAll('.nav-item,[data-tab]'))"
                        " if((n.textContent||'').trim()===%s){n.click();break;} await w(1600); return 'ok';})()"
                        % json.dumps(label, ensure_ascii=False))

        def read():
            return c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  await w(600);
  const txt = document.getElementById('page').textContent.replace(/\s+/g,' ');
  const m1 = txt.match(/照片墙上的照片（(\d+) 张）/);
  const m2 = txt.match(/已从照片墙移除（(\d+) 张）/);
  const m3 = txt.match(/还没同步的照片（(\d+) 张）/);
  return { wall: m1 ? +m1[1] : null, removed: m2 ? +m2[1] : null, pending: m3 ? +m3[1] : null,
           nDel: document.querySelectorAll('[data-phdel]').length,
           nRes: document.querySelectorAll('[data-phrestore]').length,
           albums: (typeof albums === 'function' ? albums().map(a => a.name + '=' + a.photos.length).join(', ') : ''),
           total: document.querySelectorAll('.pitem').length,
           local: JSON.parse(localStorage.getItem('mt_ov_local_v1') || '{}'),
           hidden: (typeof ov === 'function' ? ov().hiddenPhotos : null) };
})()""")

        # ① 云端已删的那张：照片墙上不该有，但要在「已从照片墙移除」里
        tab("队员名册"); tab("数据管理")
        c.js("(function(){const t=Array.from(document.querySelectorAll('[data-msec]')).find(x=>x.textContent.trim()==='照片');"
             "if(t)t.click(); return 1;})()")
        r1 = read()
        print("① 管理区→照片：", json.dumps({k: r1[k] for k in ('wall', 'removed', 'nDel', 'nRes', 'hidden')}, ensure_ascii=False))
        ok1 = (r1["removed"] == 1 and r1["nRes"] == 1 and r1["nRes"] == 1 and r1["wall"] == ncloud + 44 - 1)

        # 照片墙（展示版口径）里不该出现那张
        tab("照片墙")
        r2 = c.js("(async()=>{const w=ms=>new Promise(r=>setTimeout(r,ms)); await w(800);"
                  "const t=document.getElementById('page').textContent.replace(/\\s+/g,' ');"
                  "return { head: t.slice(0, 120), has: t.indexOf(%s) >= 0, albums: albums().length,"
                  " total: albums().reduce((a,x)=>a+x.photos.length,0) };})()" % json.dumps(DEL_ID))
        print("② 照片墙页：", json.dumps(r2, ensure_ascii=False))
        ok2 = (r2["total"] == 44 + ncloud - 1)

        # ③ 点 ↺ 恢复 → 照片墙上回来，且本机记下「恢复显示」
        tab("数据管理")
        c.js("(function(){const t=Array.from(document.querySelectorAll('[data-msec]')).find(x=>x.textContent.trim()==='照片');if(t)t.click();return 1;})()")
        c.js("(function(){const b=document.querySelector('[data-phrestore]'); if(b)b.click(); return 1;})()")
        r3 = read()
        print("③ 点了 ↺ 恢复：", json.dumps({k: r3[k] for k in ('wall', 'removed', 'hidden')}, ensure_ascii=False),
              "｜本机 shownPhotos =", json.dumps(r3["local"].get("shownPhotos"), ensure_ascii=False))
        ok3 = (r3["removed"] in (0, None) and DEL_ID not in (r3["hidden"] or []) and (r3["local"].get("shownPhotos") or []) == [DEL_ID])

        # ④ 点「删」→ 进 hiddenPhotos，墙上少一张
        before = r3["wall"]
        c.js("(function(){window.confirm=function(){return true;}; const b=document.querySelector('[data-phdel]'); if(b)b.click(); return 1;})()")
        r4 = read()
        print("④ 点了一张的「删」：", json.dumps({k: r4[k] for k in ('wall', 'removed', 'hidden')}, ensure_ascii=False),
              "｜本机 hiddenPhotos =", json.dumps(r4["local"].get("hiddenPhotos"), ensure_ascii=False))
        ok4 = (r4["removed"] == 1 and r4["wall"] == before - 1 and len(r4["local"].get("hiddenPhotos") or []) == 1)

        # ⑤ 待同步提示数（pendingCount）认得这处改动
        pend = c.js("(typeof pendingCount==='function') ? pendingCount() : -1")
        print("⑤ 待同步处数 =", pend)
        ok5 = int(pend or 0) >= 2        # hiddenPhotos 1 处 + shownPhotos 1 处

        # ⑥ 同步时写进 data/overrides.js 的 hiddenPhotos / shownPhotos（把 GitHub 那一层换成假的，只验载荷）
        c.js("localStorage.setItem('mt_gh_cfg_v1', JSON.stringify({owner:'zl4639574-bit',repo:'maitian-running',branch:'master',token:'TESTTOKEN'})); 'ok'")
        c.js("localStorage.setItem('mt_ov_local_v1', JSON.stringify({hiddenPhotos:['up_test_a.jpg','社团活动_02.jpg'], shownPhotos:['" + DEL_ID + "']})); 'ok'")
        load("tok")
        c.js("(async()=>{const w=ms=>new Promise(r=>setTimeout(r,ms));"
             "window.ghRealBranch = async () => 'master'; window.loadCloud = async () => true;"
             "window.__puts = [];"
             "window.ghPut = async (cfg, path, content, msg) => { window.__puts.push({path:path, content:content, msg:msg}); return {}; };"
             "for(const n of document.querySelectorAll('.nav-item,[data-tab]'))"
             " if((n.textContent||'').trim()==='数据管理'){n.click();break;} await w(1200);"
             "const t=Array.from(document.querySelectorAll('[data-msec]')).find(x=>x.textContent.trim()==='同步'); if(t)t.click(); await w(1200);"
             "const b=document.getElementById('btnPush'); window.__clicked = !!b; if(b)b.click(); await w(2500); return 1;})()")
        put = c.js("(function(){const a=(window.__puts||[]).filter(x=>x.path==='data/overrides.js');"
                   "return a.length ? a[a.length-1] : null;})()")
        payload = None
        if put and put.get("content"):
            payload = json.loads(re.search(r'\{.*\}', base64.b64decode(put["content"]).decode("utf-8"), re.S).group(0))
        print("⑥ 同步载荷：", json.dumps({k: (payload or {}).get(k) for k in ("hiddenPhotos", "shownPhotos")},
                                        ensure_ascii=False), "｜写入的文件：", [p["path"] for p in (c.js("window.__puts||[]") or [])])
        ok6 = bool(payload) and sorted(payload.get("hiddenPhotos") or []) == sorted(["up_test_a.jpg", "社团活动_02.jpg"]) \
              and (payload.get("shownPhotos") or []) == [DEL_ID] and len(payload.get("photos") or []) == ncloud

        print()
        for name, ok in [("① 云端删过的照片：墙上没有、列表里有、可恢复", ok1),
                         ("② 照片墙（展示口径）张数正确", ok2),
                         ("③ ↺ 恢复：照片回到墙上、本机记住 shownPhotos", ok3),
                         ("④ 删：写进本机 hiddenPhotos、墙上少一张", ok4),
                         ("⑤ 待同步计数认得照片改动", ok5),
                         ("⑥ 同步载荷带上 hiddenPhotos/shownPhotos（照片清单不丢）", ok6)]:
            print(("✅ " if ok else "❌ ") + name)
        return 0 if all([ok1, ok2, ok3, ok4, ok5, ok6]) else 1
    finally:
        try:
            if proc: proc.terminate()
        except Exception:
            pass
        srv.terminate()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
