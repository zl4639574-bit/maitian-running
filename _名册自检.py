# -*- coding: utf-8 -*-
"""名册新增队员链路验证：添加 → 展示版名册可见 → 同步 → 仓库有记录 → 线上展示版可见
用法: python _名册自检.py
"""
import base64, importlib.util, io, json, os, re, sqlite3, subprocess, shutil, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OWNER, REPO = "zl4639574-bit", "maitian-running"
SITE = "https://%s.github.io/%s/" % (OWNER, REPO)
PAY = os.path.join(os.environ.get("LOCALAPPDATA", "."), "Temp", "mt_payload.txt")
NAME = u"自检新队员"
COLLEGE = u"林学院"
MAJOR = u"林学2101"
GRADE = u"2023"

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


def wait_render(c, n=3):
    for _ in range(40):
        time.sleep(0.5)
        try:
            if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= n:
                return True
        except Exception:
            pass
    return False


def open_tab(c, label, wait=1.3):
    return c.js("""(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  for (const n of document.querySelectorAll('.nav-item,[data-tab]'))
    if ((n.textContent||'').trim() === %s) { n.click(); break; }
  await wait(%d);
  return 'ok';
})()""" % (json.dumps(label), int(wait * 1000)))


def main():
    pl = payload()
    token = json.loads(base64.urlsafe_b64decode(pl + "=" * (-len(pl) % 4)))["token"]
    before = json.loads(api("contents/data/overrides.js", token, raw=True).split("=", 1)[1].strip().rstrip(";"))
    print("测试前：线上新增队员 %d 人 | 名册修订 %d 人"
          % (len(before.get("newMembers") or []), len(before.get("memberEdits") or {})))

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
        wait_render(c)

        print("① 数据管理 → 队员名册 → 填表添加")
        open_tab(c, u"数据管理", 1.4)
        c.js("(function(){var ch=document.querySelector('[data-msec=\"member\"]'); if(ch) ch.click(); return 1;})()")
        time.sleep(1.0)
        r = c.js("""(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const set = (id, v) => { const e = document.getElementById(id); if (e) e.value = v; return !!e; };
  const ok = set('nm_name', %s) && set('nm_college', %s) && set('nm_major', %s) && set('nm_grade', %s);
  set('nm_sex', '男'); set('nm_level', '正式');
  const b = document.getElementById('btnAddMember');
  if (!b) return JSON.stringify({错误: '找不到添加按钮', 表单字段齐: ok});
  b.click();
  await wait(1200);
  const t = document.body.innerText;
  const rows = [].map.call(document.querySelectorAll('.mrow-h b'), e => e.textContent.trim());
  const m = t.match(/(已把[^\\n]{0,40}|已经在名册里了[^\\n]{0,20}|姓名请填[^\\n]{0,20})/);
  return JSON.stringify({表单字段齐: ok, 列表里已有该人: rows.indexOf(%s) >= 0,
    列表总行数: rows.length, 提示: m ? m[1] : '(无)', 计数行: (t.match(/原始名册[^\\n]{0,40}/) || ['(无)'])[0]});
})()""" % (json.dumps(NAME), json.dumps(COLLEGE), json.dumps(MAJOR), json.dumps(GRADE), json.dumps(NAME)))
        print("   ", r)
        sc = c.send("Page.captureScreenshot", format="png")
        p1 = os.path.join(HERE, u"名册自检_1_添加后.png"); shots.append(p1)
        io.open(p1, "wb").write(base64.b64decode(sc["data"]))

        print("② 切到「队员名册」页看是否出现")
        open_tab(c, u"队员名册", 1.6)
        r2 = c.js("""(function(){
  const t = document.body.innerText;
  const rows = [].map.call(document.querySelectorAll('table.tbl tbody tr'), e => e.innerText.replace(/\\s+/g,' '));
  return JSON.stringify({出现新队员: t.indexOf(%s) >= 0, 行数: rows.length,
    该队员行: rows.filter(x => x.indexOf(%s) >= 0).slice(0,1)});
})()""" % (json.dumps(NAME), json.dumps(NAME)))
        print("   ", r2)
        sc = c.send("Page.captureScreenshot", format="png")
        p2 = os.path.join(HERE, u"名册自检_2_名册页.png"); shots.append(p2)
        io.open(p2, "wb").write(base64.b64decode(sc["data"]))

        print("③ 点同步（发布到线上）")
        open_tab(c, u"数据管理", 1.4)
        done = c.js("""(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const ch = document.querySelector('[data-msec="sync"]'); if (ch) ch.click();
  await wait(900);
  const t0 = document.body.innerText;
  const b = document.getElementById('btnPush');
  if (!b) return '没找到同步按钮';
  if (b.disabled) return '同步按钮是灰的：' + ((t0.match(/⚠️[^\\n]{0,80}/) || ['(没有提示)'])[0]);
  b.click();
  for (let i = 0; i < 40; i++) { await wait(2500);
    const t = document.body.innerText;
    if (t.indexOf('同步成功') >= 0) return '同步成功';
    const m = t.match(/(同步失败[^\\n]{0,40}|没有需要同步[^\\n]{0,30}|拦下[^\\n]{0,30})/);
    if (m) return m[1];
  }
  return '(100 秒没结果)';
})()""")
        print("   ", done)
        c.ws.close()
    finally:
        subprocess.run(["taskkill", "/F", "/PID", str(proc.pid), "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(prof, ignore_errors=True)

    print("④ 仓库核对")
    time.sleep(6)
    after = json.loads(api("contents/data/overrides.js", token, raw=True).split("=", 1)[1].strip().rstrip(";"))
    nm = after.get("newMembers") or []
    hit = [m for m in nm if m.get("name") == NAME]
    print("   线上新增队员: %d -> %d 人" % (len(before.get("newMembers") or []), len(nm)))
    print("   找到该队员:", json.dumps(hit[0], ensure_ascii=False) if hit else "❌ 没找到")
    print("   原有名册修订是否保住:", len(after.get("memberEdits") or {}) == len(before.get("memberEdits") or {}))
    print("截图:", " | ".join(shots))


if __name__ == "__main__":
    main()
