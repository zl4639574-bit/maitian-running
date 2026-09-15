# -*- coding: utf-8 -*-
"""照片链路验证（修完后）：选 JPG+HEIC → 直传线上 → 同步清单 → 线上照片墙可访问 → 输出证据
用法: python _照片自检2.py
"""
import base64, importlib.util, io, json, os, re, sqlite3, subprocess, shutil, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OWNER, REPO = "zl4639574-bit", "maitian-running"
SITE = "https://%s.github.io/%s/" % (OWNER, REPO)
PAY = os.path.join(os.environ.get("LOCALAPPDATA", "."), "Temp", "mt_payload.txt")
TMP = os.path.join(os.environ.get("LOCALAPPDATA", "."), "Temp", "mt_photo_test")

spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)


def load_payload():
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
    raise SystemExit("没找到载荷")


def api(path, token, raw=False):
    req = urllib.request.Request("https://api.github.com/repos/%s/%s/%s" % (OWNER, REPO, path),
                                 headers={"User-Agent": "mt", "Accept": "application/vnd.github+json",
                                          "Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.loads(r.read())
    return base64.b64decode(d["content"]).decode("utf-8") if raw else d


def main():
    payload = load_payload()
    token = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["token"]
    url = SITE + "captain/#t=" + payload
    jpg = os.path.join(TMP, "test1.jpg")
    heic = os.path.join(TMP, "IMG_0001.HEIC")
    assert os.path.exists(jpg) and os.path.exists(heic), "先跑一次 _照片自检.py 生成测试图"

    before = json.loads(api("contents/data/overrides.js", token, raw=True).split("=", 1)[1].strip().rstrip(";"))
    print("测试前线上照片数 = %d" % len(before.get("photos") or []))

    port = ph.free_port(); proc, prof = ph.start_edge(port)
    shots = []
    try:
        time.sleep(2)
        with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=8) as r:
            page = next(t for t in json.loads(r.read()) if t["type"] == "page")
        c = ph.CDP(page["webSocketDebuggerUrl"])
        for d in ("Page.enable", "Runtime.enable", "Network.enable", "DOM.enable"):
            c.send(d)
        c.send("Network.setCacheDisabled", cacheDisabled=True)
        c.send("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=2, mobile=True)
        for _ in range(3):
            ph.goto(c, url, wait=30)
            if (c.js("location.href") or "").startswith("https://"):
                break
        for _ in range(40):
            time.sleep(0.5)
            try:
                if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 3:
                    break
            except Exception:
                pass

        c.js("(function(){localStorage.removeItem('mt_ov_local_v1');return 1;})()")
        ph.goto(c, url, wait=30)
        for _ in range(30):
            time.sleep(0.5)
            try:
                if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 3:
                    break
            except Exception:
                pass
        c.js("""(async () => {
  for (const n of document.querySelectorAll('.nav-item,[data-tab]'))
    if ((n.textContent||'').trim() === '数据管理') { n.click(); break; }
  await new Promise(r => setTimeout(r, 1200));
  const ch = document.querySelector('[data-msec="photos"]'); if (ch) ch.click();
  await new Promise(r => setTimeout(r, 800));
})()""")
        time.sleep(1)
        doc = c.send("DOM.getDocument", depth=1)
        node = c.send("DOM.querySelector", nodeId=doc["root"]["nodeId"], selector="#photoInput")
        c.send("DOM.setFileInputFiles", files=[jpg, heic], nodeId=node["nodeId"])
        print("① 已选 2 个文件（1 张正常 JPG + 1 张 iPhone HEIC）")
        time.sleep(12)
        st = c.js("""(function(){
  const l = JSON.parse(localStorage.getItem('mt_ov_local_v1')||'{}');
  const t = document.body.innerText;
  const m = t.match(/(已加入[^\\n]{0,150}|打不开被跳过[^\\n]{0,80})/g);
  return JSON.stringify({本机待同步照片:(l.photos||[]).length,
    带图数据条数:(l.photos||[]).filter(p=>p.data).length,
    localStorage占用KB: Math.round(JSON.stringify(l).length/1024),
    提示:(m||[]).join(' / ').slice(0,220)});
})()""")
        print("② 选完之后:", st)
        r = c.send("Page.captureScreenshot", format="png")
        s1 = os.path.join(HERE, u"照片自检_修后_选完.png"); shots.append(s1)
        io.open(s1, "wb").write(base64.b64decode(r["data"]))

        print("③ 点「同步我的修改到线上」写清单…")
        done = c.js("""(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const ch = document.querySelector('[data-msec="sync"]'); if (ch) ch.click();
  await wait(900);
  const b = document.getElementById('btnPush');
  if (!b) return '没找到同步按钮';
  if (b.disabled) return '同步按钮是灰的（说明没识别到待同步的照片）';
  b.click();
  for (let i = 0; i < 40; i++) { await wait(2500);
    const t = document.body.innerText;
    if (t.indexOf('同步成功') >= 0) return '同步成功';
    const m = t.match(/(同步失败[^\\n]{0,40}|没有需要同步[^\\n]{0,30}|拦下[^\\n]{0,30})/);
    if (m) return m[1];
  }
  return '(100 秒内没结果)';
})()""")
        print("    结果:", done)
        r = c.send("Page.captureScreenshot", format="png")
        s2 = os.path.join(HERE, u"照片自检_修后_同步后.png"); shots.append(s2)
        io.open(s2, "wb").write(base64.b64decode(r["data"]))
        c.ws.close()
    finally:
        subprocess.run(["taskkill", "/F", "/PID", str(proc.pid), "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(prof, ignore_errors=True)

    print("④ 仓库/线上核对")
    time.sleep(6)
    after = json.loads(api("contents/data/overrides.js", token, raw=True).split("=", 1)[1].strip().rstrip(";"))
    phs = after.get("photos") or []
    print("   线上照片清单: %d -> %d 条" % (len(before.get("photos") or []), len(phs)))
    newp = [p for p in phs if p.get("file") not in [x.get("file") for x in (before.get("photos") or [])]]
    print("   新增照片:", json.dumps(newp, ensure_ascii=False)[:200])
    for p in newp:
        u = SITE + "images/" + p["file"] + "?t=3"
        try:
            with urllib.request.urlopen(u, timeout=25) as r:
                print("   线上可访问 %s -> HTTP %d, %d 字节" % (p["file"], r.status, int(r.headers.get("content-length") or 0)))
        except Exception as e:
            print("   ⚠️ 线上取不到 %s: %s（Pages 可能还在发布，等 1 分钟再试）" % (p["file"], e))
    print("截图:", " | ".join(shots))


if __name__ == "__main__":
    main()
