# -*- coding: utf-8 -*-
"""照片上传自检：① 正常 JPG ② JPG+HEIC 混在一起 ③ 本机存储（localStorage ~5MB）满了
用法: python _照片自检.py
"""
import base64, importlib.util, io, json, os, re, sqlite3, subprocess, shutil, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OWNER, REPO = "zl4639574-bit", "maitian-running"
SITE = "https://%s.github.io/%s/" % (OWNER, REPO)
PAY = os.path.join(os.environ.get("LOCALAPPDATA", "."), "Temp", "mt_payload.txt")
TMP = os.path.join(os.environ.get("LOCALAPPDATA", "."), "Temp", "mt_photo_test")
os.makedirs(TMP, exist_ok=True)

spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)

# 一张 40x30 的有效 JPEG（纯色），和一份冒充 iPhone HEIC 的垃圾数据
JPEG_B64 = ("/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
            "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAAeACgBAREA/8QAHwAAAQUBAQEB"
            "AQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1Fh"
            "ByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZ"
            "WmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXG"
            "x8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/9oACAEBAAA/APn+iiiiiiiiiiiiiiii"
            "iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii"
            "iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiv//Z")


def mk_files():
    """用 PIL 生成测试图：一张 2400x1600 的「照片」（看真实体积）+ 一份冒充 iPhone HEIC 的坏文件"""
    from PIL import Image, ImageDraw
    jpg = os.path.join(TMP, "test1.jpg")
    im = Image.new("RGB", (2400, 1600))
    d = ImageDraw.Draw(im)
    for i in range(0, 2400, 40):
        d.line([(i, 0), (i, 1600)], fill=(i % 255, (i * 3) % 255, (i * 7) % 255), width=12)
    for i in range(0, 1600, 40):
        d.line([(0, i), (2400, i)], fill=((i * 5) % 255, 120, (i * 2) % 255), width=8)
    im.save(jpg, "JPEG", quality=88)
    heic = os.path.join(TMP, "IMG_0001.HEIC")
    io.open(heic, "wb").write(b"\x00\x00\x00\x18ftypheic" + os.urandom(200000))
    print("   生成: %s (%.0f KB) / %s (%.0f KB)" % (os.path.basename(jpg), os.path.getsize(jpg) / 1024,
                                                 os.path.basename(heic), os.path.getsize(heic) / 1024))
    return jpg, heic


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


def to_photos_section(c):
    c.js("""(async () => {
  for (const n of document.querySelectorAll('.nav-item,[data-tab]'))
    if ((n.textContent||'').trim() === '数据管理') { n.click(); break; }
  await new Promise(r => setTimeout(r, 1200));
  const ch = document.querySelector('[data-msec="photos"]'); if (ch) ch.click();
  await new Promise(r => setTimeout(r, 800));
  return 'ok';
})()""")


def set_files(c, paths):
    doc = c.send("DOM.getDocument", depth=1)
    n = c.send("DOM.querySelector", nodeId=doc["root"]["nodeId"], selector="#photoInput")
    if not n.get("nodeId"):
        return "找不到 #photoInput"
    c.send("DOM.setFileInputFiles", files=paths, nodeId=n["nodeId"])
    return "已选 %d 个文件" % len(paths)


def read_state(c):
    return c.js("""(function(){
  const l = JSON.parse(localStorage.getItem('mt_ov_local_v1') || '{}');
  const t = document.body.innerText;
  const m = t.match(/(已加入[^\\n]{0,60}|本机存储[^\\n]{0,80}|这个浏览器不让存[^\\n]{0,60})/);
  return JSON.stringify({本机待同步照片: (l.photos||[]).length,
    本机带图数据: (l.photos||[]).filter(p=>p.data).length,
    提示: m ? m[1] : '(没有提示)',
    页面显示本机照片: (t.match(/本机新加的照片（(\\d+) 张/)||[])[1] || '0',
    待同步计数: (function(){try{return pendingCount();}catch(e){return 'n/a';}})()});
})()""")


def main():
    payload = load_payload()
    url = SITE + "captain/#t=" + payload
    jpg, heic = mk_files()
    print("测试文件:", os.path.basename(jpg), "|", os.path.basename(heic))

    port = ph.free_port(); proc, prof = ph.start_edge(port)
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

        # ── 用例 1：一张正常 JPG ──
        to_photos_section(c); time.sleep(1)
        print("\n[用例1] 只传 1 张正常 JPG →", set_files(c, [jpg]))
        time.sleep(4)
        print("        结果:", read_state(c))
        r = c.send("Page.captureScreenshot", format="png")
        io.open(os.path.join(HERE, u"照片自检_1_正常JPG.png"), "wb").write(base64.b64decode(r["data"]))

        # ── 用例 2：JPG + HEIC 混在一起（清空本机后重来）──
        c.js("(function(){localStorage.removeItem('mt_ov_local_v1');localStorage.removeItem('mt_results_v1');return 1;})()")
        ph.goto(c, url, wait=30)
        for _ in range(30):
            time.sleep(0.5)
            try:
                if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 3:
                    break
            except Exception:
                pass
        to_photos_section(c); time.sleep(1)
        print("\n[用例2] JPG + HEIC 一起传（模拟 iPhone 照片）→", set_files(c, [jpg, heic]))
        time.sleep(6)
        print("        结果:", read_state(c))

        # ── 用例 3：本机存储快满了（塞 4.5MB 垃圾）──
        c.js("(function(){localStorage.removeItem('mt_ov_local_v1');"
             "localStorage.setItem('__junk','x'.repeat(4500000));return localStorage.getItem('__junk').length;})()")
        ph.goto(c, url, wait=30)
        for _ in range(30):
            time.sleep(0.5)
            try:
                if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 3:
                    break
            except Exception:
                pass
        to_photos_section(c); time.sleep(1)
        print("\n[用例3] 本机已占 4.5MB，再传 1 张 JPG →", set_files(c, [jpg]))
        time.sleep(4)
        print("        结果:", read_state(c))
        print("        存储占用: %s MB" % c.js("(function(){let n=0;for(let k in localStorage){if(localStorage.hasOwnProperty(k))n+=(localStorage[k]||'').length;}return (n/1048576).toFixed(2);})()"))
        r = c.send("Page.captureScreenshot", format="png")
        io.open(os.path.join(HERE, u"照片自检_3_存储满.png"), "wb").write(base64.b64decode(r["data"]))
        c.ws.close()
    finally:
        subprocess.run(["taskkill", "/F", "/PID", str(proc.pid), "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(prof, ignore_errors=True)


if __name__ == "__main__":
    main()
