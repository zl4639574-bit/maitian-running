# -*- coding: utf-8 -*-
"""验证重名/未分级处理：① 输入「张津浩」→ 说明原因 + 两个按钮 ② 搜出来改身份 ③ 仍要添加（同名并存）+ 按 uid 删除
   注意：全程不点「保存名册修改」，确保真实数据不被改动
用法: python _重名自检.py
"""
import base64, importlib.util, io, json, os, re, sqlite3, subprocess, shutil, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OWNER, REPO = "zl4639574-bit", "maitian-running"
SITE = "https://%s.github.io/%s/" % (OWNER, REPO)
PAY = os.path.join(os.environ.get("LOCALAPPDATA", "."), "Temp", "mt_payload.txt")
NAME = u"张津浩"

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


def api(path, token, raw=False):
    r = urllib.request.Request("https://api.github.com/repos/%s/%s/%s" % (OWNER, REPO, path),
                               headers={"User-Agent": "mt", "Authorization": "Bearer " + token})
    d = json.loads(urllib.request.urlopen(r, timeout=25).read())
    return base64.b64decode(d["content"]).decode("utf-8") if raw else d


def main():
    pl = payload()
    token = json.loads(base64.urlsafe_b64decode(pl + "=" * (-len(pl) % 4)))["token"]
    ov0 = json.loads(api("contents/data/overrides.js", token, raw=True).split("=", 1)[1].strip().rstrip(";"))
    print("测试前：云端 memberEdits=%d 条, newMembers=%s"
          % (len(ov0.get("memberEdits") or {}), ov0.get("newMembers") or []))

    port = ph.free_port(); proc, prof = ph.start_edge(port)
    shots = []
    try:
        time.sleep(2)
        with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=8) as r:
            pg = next(t for t in json.loads(r.read()) if t["type"] == "page")
        c = ph.CDP(pg["webSocketDebuggerUrl"])
        for d in ("Page.enable", "Runtime.enable", "Network.enable", "DOM.enable"):
            c.send(d)
        c.send("Network.setCacheDisabled", cacheDisabled=True)
        c.send("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=2, mobile=True)
        for _ in range(3):
            ph.goto(c, SITE + "captain/#t=" + pl, wait=30)
            if (c.js("location.href") or "").startswith("https://"):
                break
        for _ in range(40):
            time.sleep(0.5)
            try:
                if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 3:
                    break
            except Exception:
                pass
        c.js("""(async () => {
  for (const n of document.querySelectorAll('.nav-item,[data-tab]'))
    if ((n.textContent||'').trim() === '数据管理') { n.click(); break; }
  await new Promise(r => setTimeout(r, 1400));
  const ch = document.querySelector('[data-msec="member"]'); if (ch) ch.click();
  await new Promise(r => setTimeout(r, 900));
})()""")
        time.sleep(1)

        print("\n① 输入「%s」→ 点「添加到名册」" % NAME)
        r = c.js("""(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  document.getElementById('nm_name').value = %s;
  document.getElementById('btnAddMember').click();
  await wait(1200);
  const box = document.getElementById('nmAddBox');
  return JSON.stringify({
    弹出说明: !!box && box.innerText.trim().length > 0,
    说明原文: box ? box.innerText.replace(/\\s+/g, ' ').slice(0, 260) : '(无)',
    有搜出来改身份按钮: !!document.getElementById('btnNmFindIt'),
    有仍然添加按钮: !!document.getElementById('btnNmForce'),
    本机新增记录数: (JSON.parse(localStorage.getItem('mt_ov_local_v1')||'{}').newMembers||[]).length});
})()""" % json.dumps(NAME))
        print("   ", r)
        sc = c.send("Page.captureScreenshot", format="png")
        p1 = os.path.join(HERE, u"重名_1_说明.png"); shots.append(p1)
        io.open(p1, "wb").write(base64.b64decode(sc["data"]))

        print("② 点「搜出来改他的身份」")
        r2 = c.js("""(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const b = document.getElementById('btnNmFindIt');
  if (!b) return '没有这个按钮';
  b.click(); await wait(900);
  const q = document.getElementById('mRosterQ');
  const rows = [].map.call(document.querySelectorAll('.mrow'), e => e.innerText.replace(/\\s+/g, ' ').trim());
  const hit = rows.filter(x => x.indexOf(%s) === 0 || x.indexOf(%s) >= 0);
  const sel = [].map.call(document.querySelectorAll('.mrow select'), s => ({ 当前值: s.value, 选项: [].map.call(s.options, o => o.textContent) })).slice(0, 2);
  return JSON.stringify({搜索框值: q ? q.value : '(无)', 列表行数: rows.length, 命中行: hit.slice(0, 2), 身份下拉: sel});
})()""" % (json.dumps(NAME), json.dumps(NAME)))
        print("   ", r2)
        sc = c.send("Page.captureScreenshot", format="png")
        p2 = os.path.join(HERE, u"重名_2_搜出来.png"); shots.append(p2)
        io.open(p2, "wb").write(base64.b64decode(sc["data"]))

        print("③ 再输一次并点「是另一个人，仍然添加」")
        r3 = c.js("""(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const q = document.getElementById('mRosterQ');
  if (q) { q.value = ''; q.dispatchEvent(new Event('input', {bubbles: true})); await wait(700); }
  document.getElementById('nm_name').value = %s;
  document.getElementById('btnAddMember').click();
  await wait(1000);
  const b = document.getElementById('btnNmForce');
  if (!b) return '没出现「仍然添加」按钮';
  b.click(); await wait(1400);
  const nm = JSON.parse(localStorage.getItem('mt_ov_local_v1')||'{}').newMembers || [];
  const t = document.body.innerText;
  return JSON.stringify({提示: (t.match(/已把[^\\n]{0,60}/) || ['(无)'])[0],
    本机新增记录数: nm.length, 新增的这条: nm[nm.length - 1],
    列表里带新增徽章的行: [].map.call(document.querySelectorAll('.mrow-h'), e => e.innerText.replace(/\\s+/g,' ').trim()).slice(0, 2)});
})()""" % json.dumps(NAME))
        print("   ", r3)

        print("④ 按 uid 删掉这条新增（验证同名不串）")
        r4 = c.js("""(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const b = document.querySelector('[data-muiddel]');
  if (!b) return '没找到 uid 删除按钮';
  b.click(); await wait(1200);
  const nm = JSON.parse(localStorage.getItem('mt_ov_local_v1')||'{}').newMembers || [];
  const edits = JSON.parse(localStorage.getItem('mt_ov_local_v1')||'{}').memberEdits || {};
  return JSON.stringify({删除后本机新增记录数: nm.length, 改过的原始队员数: Object.keys(edits).length,
    提示: (document.body.innerText.match(/已删除[^\\n]{0,20}/) || ['(无)'])[0]});
})()""")
        print("   ", r4)
        c.ws.close()
    finally:
        subprocess.run(["taskkill", "/F", "/PID", str(proc.pid), "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(prof, ignore_errors=True)

    print("\n⑤ 云端数据有没有被误改")
    time.sleep(4)
    ov1 = json.loads(api("contents/data/overrides.js", token, raw=True).split("=", 1)[1].strip().rstrip(";"))
    print("   memberEdits: %d -> %d 条 | newMembers: %s -> %s"
          % (len(ov0.get("memberEdits") or {}), len(ov1.get("memberEdits") or {}),
             ov0.get("newMembers") or '[]', ov1.get("newMembers") or '[]'))
    print("   原始队员是否被改动:", "❌ 有改动" if (ov1.get("memberEdits") or {}) != (ov0.get("memberEdits") or {}) else "✅ 没有")
    print("截图:", " | ".join(shots))


if __name__ == "__main__":
    main()
