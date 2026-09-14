# -*- coding: utf-8 -*-
"""端到端同步自检：手机视口打开线上队长版 → 自动点「测试同步（不改数据）」→ 抓结果
   + 从 GitHub 侧独立核对（提交记录、overrides.js 内容）
用法: python _同步自检.py            （载荷从 %LOCALAPPDATA%\\Temp\\mt_payload.txt 读，不进命令行）
"""
import base64, importlib.util, io, json, os, subprocess, shutil, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OWNER, REPO = "zl4639574-bit", "maitian-running"
SITE = "https://%s.github.io/%s/" % (OWNER, REPO)
PAYLOAD_FILE = os.path.join(os.environ.get("LOCALAPPDATA", "."), "Temp", "mt_payload.txt")

spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ph)

MASK = lambda s: ("%s...%s(%d位)" % (s[:7], s[-4:], len(s))) if s else "无"


def api(path, token=None):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"User-Agent": "mt-selftest", "Accept": "application/vnd.github+json"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.status, json.loads(r.read()), dict(r.headers)


def latest_commits(n=4, token=None):
    st, data, _ = api("/repos/%s/%s/commits?per_page=%d" % (OWNER, REPO, n), token)
    return st, [(c["sha"][:7], c["commit"]["message"].split("\n")[0]) for c in data]


def overrides_content(token=None):
    try:
        st, data, _ = api("/repos/%s/%s/contents/data/overrides.js" % (OWNER, REPO), token)
        return st, base64.b64decode(data["content"]).decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, ""


def main():
    payload = io.open(PAYLOAD_FILE, encoding="utf-8").read().strip()
    token = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["token"]
    print("== 0. 令牌体检（只读接口）==")
    st, _, hdr = api("/repos/%s/%s" % (OWNER, REPO), token)
    print("   GET /repos/... -> HTTP %d | 令牌类型=%s | 权限域=%s"
          % (st, hdr.get("X-OAuth-Scopes") and "经典令牌" or "细粒度", hdr.get("X-OAuth-Scopes") or hdr.get("x-accepted-oauth-scopes", "")[:60]))

    print("== 1. 测试前：仓库状态 ==")
    st, cbefore = latest_commits(3, token)
    print("   最近提交:", cbefore)
    st, ov0 = overrides_content(token)
    print("   data/overrides.js -> HTTP %s | 含自检标记=%s" % (st, "selfTest" in ov0))

    url = SITE + "captain/#t=" + payload
    port = ph.free_port()
    proc, prof = ph.start_edge(port)
    shot_before = shot_after = None
    try:
        time.sleep(2)
        with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=8) as r:
            targets = json.loads(r.read())
        page = next(t for t in targets if t["type"] == "page")
        c = ph.CDP(page["webSocketDebuggerUrl"])
        c.send("Page.enable"); c.send("Runtime.enable"); c.send("Network.enable")
        c.send("Network.setCacheDisabled", cacheDisabled=True)
        c.send("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=2, mobile=True)
        c.send("Emulation.setTouchEmulationEnabled", enabled=True)

        print("== 2. 打开线上队长版（手机视口 390x844）==")
        ok = False
        for attempt in range(3):
            ok = ph.goto(c, url, wait=30)
            try:
                where = c.js("location.href") or ""
            except Exception:
                where = ""
            if where.startswith("https://"):
                break
            print("   ! 第 %d 次落在 %s，重试…" % (attempt + 1, where[:60]))
            time.sleep(2)
        print("   加载成功=%s  当前地址=%s" % (ok, (where or "")[:78]))
        for _ in range(40):
            time.sleep(0.5)
            try:
                if int(str(c.js("(function(){var p=document.getElementById('page');return p?p.innerHTML.length:0;})()")).strip()) > 400:
                    break
            except Exception:
                pass
        time.sleep(1.5)
        info = c.js("(function(){try{var cfg=JSON.parse(localStorage.getItem('mt_gh_cfg_v1')||'{}');"
                    "return JSON.stringify({MODE:(typeof MODE!=='undefined'?MODE:'?'),SYNC:SYNC_STATE,"
                    "hash有令牌:location.hash.length>5,本机已存令牌:!!cfg.token,owner:cfg.owner,repo:cfg.repo,branch:cfg.branch,"
                    "有测试按钮:!!document.getElementById('btnTest')});}catch(e){return 'ERR '+e.message;}})()")
        print("   页面状态:", info)
        r = c.send("Page.captureScreenshot", format="png")
        shot_before = os.path.join(HERE, u"同步自检_1_点击前.png")
        io.open(shot_before, "wb").write(base64.b64decode(r["data"]))

        print("== 3. 进入「数据管理 → 同步」分区 ==")
        print("   ", c.js("(function(){var n=document.querySelectorAll('.nav-item,[data-tab],nav div,nav a');"
                          "for(var i=0;i<n.length;i++){if((n[i].textContent||'').trim()==='数据管理'){n[i].click();return '已点「数据管理」';}}"
                          "return '没找到入口，现有: '+[].map.call(n,function(e){return (e.textContent||'').trim().slice(0,8);}).join('/');})()"))
        time.sleep(1.5)
        print("   ", c.js("(function(){var ch=document.querySelector('[data-msec=\"sync\"]');"
                          "if(ch){ch.click();return '已切到「同步」分区';}"
                          "return '没有分区按钮，现有的: '+[].map.call(document.querySelectorAll('[data-msec]'),function(e){return e.getAttribute('data-msec');}).join(',');})()"))
        time.sleep(1.2)
        panel = c.js("(function(){var n=document.querySelector('.card.sec');return n?n.innerText.replace(/\\n+/g,' | ').slice(0,420):'(没找到同步面板)';})()")
        print("   同步面板显示:", panel)

        print("== 4. 点击「测试同步（不改数据）」==")
        click = c.js("(function(){var b=document.getElementById('btnTest');if(!b)return 'no-button';"
                     "if(!b.onclick&&!b.getAttribute('onclick'))return 'no-handler';b.click();return b.textContent;})()")
        print("   点击结果:", click)

        t0 = time.time(); found = None
        while time.time() - t0 < 180:
            time.sleep(1.5)
            try:
                txt = c.js("document.body.innerText") or ""
            except Exception:
                txt = ""
            for pat in [u"测试通过", u"写入成功，但网页暂时没读到", u"测试失败", u"被 GitHub 拦下", u"先填访问令牌"]:
                if pat in txt:
                    i = txt.find(pat)
                    found = txt[max(0, i - 30):i + 90].replace("\n", " ").strip()
                    break
            if found:
                break
        print("== 4. 结果（%.0f 秒）==" % (time.time() - t0))
        print("   " + (found or u"⚠️ 180 秒内没出现任何结果提示"))
        print("   按钮当前文字:", c.js("(function(){var b=document.getElementById('btnTest');return b?b.textContent:'-';})()"))
        sec = c.js("(function(){var n=document.querySelector('.sync');return n?n.innerText.slice(0,600):'(没找到同步面板)';})()")
        print("   同步面板显示:", (sec or "").replace("\n", " | ")[:400])
        r = c.send("Page.captureScreenshot", format="png")
        shot_after = os.path.join(HERE, u"同步自检_2_结果.png")
        io.open(shot_after, "wb").write(base64.b64decode(r["data"]))
        c.ws.close()
    finally:
        subprocess.run(["taskkill", "/F", "/PID", str(proc.pid), "/T"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(prof, ignore_errors=True)

    print("== 5. 从 GitHub 侧独立核对（不是看界面提示，是看仓库真实内容）==")
    time.sleep(6)
    st, cafter = latest_commits(4, token)
    print("   最近提交:", cafter)
    new = [x for x in cafter if x not in cbefore]
    print("   新增提交:", new if new else "（没有新提交 → 说明没写进去）")
    st, ov1 = overrides_content(token)
    print("   data/overrides.js -> HTTP %s | 含自检标记=%s（应为 False：测试完已清除）" % (st, "selfTest" in ov1))
    if ov1:
        try:
            obj = json.loads(ov1.split("=", 1)[1].strip().rstrip(";"))
            print("   写入内容摘要: 键=%s | 真实数据未受影响=%s"
                  % (",".join(list(obj.keys())[:12]), obj.get("team") == {} and not obj.get("results")))
        except Exception as e:
            print("   内容解析:", ov1[:200].replace("\n", " "))
    print("== 6. 测试后：线上展示版是否正常 ==")
    with urllib.request.urlopen(SITE, timeout=25) as r:
        print("   %s -> HTTP %d" % (SITE, r.status))
    print("\n截图:", shot_before, "|", shot_after)


if __name__ == "__main__":
    main()
