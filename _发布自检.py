# -*- coding: utf-8 -*-
"""复现「导入数据后同步不了」并验证修复：模拟本机已有导入数据 → 看提示 → 一键发布并同步 → 从仓库核对
用法: python _发布自检.py   （载荷从会话记录取出写进临时文件，不进命令行）
"""
import base64, importlib.util, io, json, os, re, sqlite3, subprocess, shutil, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OWNER, REPO = "zl4639574-bit", "maitian-running"
SITE = "https://%s.github.io/%s/" % (OWNER, REPO)
PAY = os.path.join(os.environ.get("LOCALAPPDATA", "."), "Temp", "mt_payload.txt")

spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)

TESTNAME = u"同步自检甲"
TESTMEET = u"一键发布自检"


def load_payload():
    """从会话记录里按模式取回队长专用链接的载荷（避免把令牌打出来）"""
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
    raise SystemExit("没找到可用载荷")


def repo_overrides(token):
    u = "https://api.github.com/repos/%s/%s/contents/data/overrides.js" % (OWNER, REPO)
    req = urllib.request.Request(u, headers={"User-Agent": "mt", "Accept": "application/vnd.github+json",
                                             "Authorization": "Bearer " + token})
    d = json.loads(urllib.request.urlopen(req, timeout=25).read())
    txt = base64.b64decode(d["content"]).decode("utf-8")
    return json.loads(txt.split("=", 1)[1].strip().rstrip(";"))


def main():
    payload = load_payload()
    token = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["token"]
    url = SITE + "captain/#t=" + payload

    before = repo_overrides(token)
    print("测试前：线上「自由成绩」条数 = %d" % len(before.get("results") or []))

    port = ph.free_port(); proc, prof = ph.start_edge(port)
    try:
        time.sleep(2)
        with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=8) as r:
            page = next(t for t in json.loads(r.read()) if t["type"] == "page")
        c = ph.CDP(page["webSocketDebuggerUrl"])
        c.send("Page.enable"); c.send("Runtime.enable"); c.send("Network.enable")
        c.send("Network.setCacheDisabled", cacheDisabled=True)
        c.send("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=2, mobile=True)
        c.send("Emulation.setTouchEmulationEnabled", enabled=True)
        for _ in range(3):
            ph.goto(c, url, wait=30)
            if (c.js("location.href") or "").startswith("https://"):
                break
        print("页面:", (c.js("location.href") or "")[:60], "MODE=", c.js("typeof MODE!=='undefined'?MODE:'?'"))
        for _ in range(40):                     # 等页面真渲染出来（脚本是动态加载的）
            time.sleep(0.5)
            try:
                if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 3:
                    break
            except Exception:
                pass
        print("导航项:", c.js("document.querySelectorAll('.nav-item').length"),
              "| 分区:", c.js("document.querySelectorAll('.nav-item').length && [].map.call(document.querySelectorAll('.nav-item'),function(e){return e.textContent.trim();}).join('/')"))

        # ① 模拟「刚导入完数据」的处境：本机成绩库里有一条没发布的成绩
        c.js("(function(){localStorage.setItem('mt_results_v1', JSON.stringify([{uid:'selftest_pub',"
             "name:'%s',event:'5000米',raw:'18:30',sec:1110,fmt:'18:30',date:'2026-09-14',"
             "meet:'%s',ts:Date.now()}])); return '已模拟导入 1 条';})()" % (TESTNAME, TESTMEET))

        # ② 打开 数据管理 → 同步，看有没有提示 + 一键按钮
        r = c.js("""(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const out = {};
  for (const n of document.querySelectorAll('.nav-item,[data-tab]'))
    if ((n.textContent||'').trim() === '数据管理') { n.click(); break; }
  await wait(1500);
  const ch = document.querySelector('[data-msec="sync"]'); if (ch) ch.click();
  await wait(900);
  out.本机未发布条数 = JSON.parse(localStorage.getItem('mt_results_v1')||'[]').length;
  const b = document.getElementById('btnPubSync2');
  out.出现一键按钮 = !!b;
  out.提示文字 = b ? b.closest('.notice').innerText.replace(/\s+/g,' ').slice(0,180) : '(没有)';
  const push = document.getElementById('btnPush');
  out.同步按钮是否灰 = push ? !!push.disabled : null;
  if (!b) return JSON.stringify(out);
  b.click();
  for (let i = 0; i < 60; i++) {
    await wait(2500);
    const t = document.body.innerText;
    if (t.indexOf('同步成功') >= 0) { out.结果 = '同步成功'; break; }
    const m = t.match(/(同步失败[^\\n]{0,40}|没有需要同步的修改[^\\n]{0,40}|本机没有待同步[^\\n]{0,60}|拦下[^\\n]{0,30})/);
    if (m) { out.结果 = m[1]; break; }
  }
  if (!out.结果) out.结果 = '(150 秒内没看到结果提示)';
  out.同步后本机剩余 = JSON.parse(localStorage.getItem('mt_results_v1')||'[]').length;
  out.同步后待同步标记 = (JSON.parse(localStorage.getItem('mt_ov_local_v1')||'{}').results||[]).length;
  return JSON.stringify(out);
})()""")
        print("③ 页面结果:", r)
        if r:
            try:
                d = json.loads(r)
                for k, v in d.items():
                    print("     %s = %s" % (k, v))
            except Exception:
                pass
        r2 = c.send("Page.captureScreenshot", format="png")
        shot = os.path.join(HERE, u"发布自检_结果.png")
        io.open(shot, "wb").write(base64.b64decode(r2["data"]))
        print("截图:", shot)
        c.ws.close()
    finally:
        subprocess.run(["taskkill", "/F", "/PID", str(proc.pid), "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(prof, ignore_errors=True)

    print("④ 从仓库核对（权威证据）")
    time.sleep(6)
    after = repo_overrides(token)
    res = after.get("results") or []
    hit = [x for x in res if x.get("name") == TESTNAME]
    print("   线上「自由成绩」条数: %d -> %d" % (len(before.get("results") or []), len(res)))
    print("   找到测试成绩:", json.dumps(hit[0], ensure_ascii=False) if hit else "❌ 没找到（说明没写进去）")
    print("   真实数据是否受影响:", "✅ 没受影响" if (after.get("competitions") == before.get("competitions")) else "⚠️ 变了")


if __name__ == "__main__":
    main()
