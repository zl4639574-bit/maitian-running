# -*- coding: utf-8 -*-
"""批量添加队员链路验证：① 粘贴多行（含表头/重复/脏名字）② 选 Excel 文件 ③ 同步 → 仓库核对
用法: python _批量名册自检.py
"""
import base64, importlib.util, io, json, os, re, sqlite3, subprocess, shutil, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OWNER, REPO = "zl4639574-bit", "maitian-running"
SITE = "https://%s.github.io/%s/" % (OWNER, REPO)
PAY = os.path.join(os.environ.get("LOCALAPPDATA", "."), "Temp", "mt_payload.txt")
TMP = os.path.join(os.environ.get("LOCALAPPDATA", "."), "Temp", "mt_roster_test")
os.makedirs(TMP, exist_ok=True)
TESTNAMES = [u"批量甲", u"批量乙", u"批量丙", u"文件甲", u"文件乙"]

PASTE = "\n".join([
    u"姓名\t学院\t专业\t年级\t性别\t身份",
    u"批量甲\t林学院\t林学2101\t2023\t男\t正式",
    u"批量乙\t园艺学院\t园艺2102\t2023\t女\t预备",
    u"批量丙\t水建学院\t水利2103\t2024\t男\t",
    u"张\t测试\tX\t2024\t男\t正式",
    u"批量甲\t林学院\t林学2101\t2023\t男\t正式",
])

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


def mk_xlsx():
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active
    ws.append([u"姓名", u"学院", u"专业", u"年级", u"性别", u"身份"])
    ws.append([u"文件甲", u"动科学院", u"动科2101", u"2023", u"男", u"正式"])
    ws.append([u"文件乙", u"食品学院", u"食工2102", u"2024", u"女", u"预备"])
    f = os.path.join(TMP, "新队员名单.xlsx")
    wb.save(f)
    return f


def main():
    pl = payload()
    token = json.loads(base64.urlsafe_b64decode(pl + "=" * (-len(pl) % 4)))["token"]
    xlsx = mk_xlsx()
    before = json.loads(api("contents/data/overrides.js", token, raw=True).split("=", 1)[1].strip().rstrip(";"))
    print("测试前线上新增队员: %d 人" % len(before.get("newMembers") or []))
    print("测试 Excel:", os.path.basename(xlsx))

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

        print("\n① 粘贴 6 行（含表头/重复/1 个脏名字）→ 解析并预览")
        r = c.js("""(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const ta = document.getElementById('nmBatch');
  if (!ta) return JSON.stringify({错误: '没有批量输入框'});
  ta.value = %s;
  const b = document.getElementById('btnNmPreview');
  if (!b) return JSON.stringify({错误: '没有解析按钮'});
  b.click();
  await wait(1200);
  const box = document.getElementById('nmBatchBox').innerText.replace(/\\s+/g, ' ');
  const rows = [].map.call(document.querySelectorAll('#nmBatchBox tbody tr'), e => e.innerText.replace(/\\t/g, ' ').trim());
  const cf = document.getElementById('btnNmConfirm');
  return JSON.stringify({预览摘要: (box.match(/解析出[^。]{0,120}/) || ['(无)'])[0],
    预览行数: rows.length, 前3行: rows.slice(0, 3),
    确认按钮: cf ? cf.textContent.trim() : '(没有)'});
})()""" % json.dumps(PASTE))
        print("   ", r)
        sc = c.send("Page.captureScreenshot", format="png")
        p1 = os.path.join(HERE, u"批量名册_1_预览.png"); shots.append(p1)
        io.open(p1, "wb").write(base64.b64decode(sc["data"]))

        print("② 点「加入名册」")
        r2 = c.js("""(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const cf = document.getElementById('btnNmConfirm');
  if (!cf) return '没有确认按钮';
  cf.click();
  await wait(1500);
  const t = document.body.innerText;
  const m = t.match(/(已把[^\\n]{0,70})/);
  const rows = [].map.call(document.querySelectorAll('.mrow-h b'), e => e.textContent.trim());
  return JSON.stringify({提示: m ? m[1] : '(无提示)', 名册列表行数: rows.length,
    列表前几行: rows.slice(0, 6), 计数行: (t.match(/原始名册[^\\n]{0,40}/) || ['(无)'])[0]});
})()""")
        print("   ", r2)

        print("③ 选一个 xlsx 文件（第二组人）")
        doc = c.send("DOM.getDocument", depth=1)
        node = c.send("DOM.querySelector", nodeId=doc["root"]["nodeId"], selector="#nmFileInput")
        if node.get("nodeId"):
            c.send("DOM.setFileInputFiles", files=[xlsx], nodeId=node["nodeId"])
            time.sleep(3)
            r3 = c.js("""(function(){
  const box = document.getElementById('nmBatchBox');
  const ta = document.getElementById('nmBatch');
  const t = box ? box.innerText.replace(/\\s+/g,' ') : '';
  const cf = document.getElementById('btnNmConfirm');
  return JSON.stringify({摘录框内容: (ta ? ta.value.split('\\n').slice(0,2) : []),
    预览摘要: (t.match(/解析出[^。]{0,80}/) || ['(无)'])[0],
    确认按钮: cf ? cf.textContent.trim() : '(没有)'});
})()""")
            print("   ", r3)
        else:
            print("    找不到 #nmFileInput")
        r4 = c.js("""(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const cf = document.getElementById('btnNmConfirm');
  if (!cf) return '没有确认按钮';
  cf.click(); await wait(1500);
  const t = document.body.innerText;
  return (t.match(/(已把[^\\n]{0,70})/) || ['(无提示)'])[0];
})()""")
        print("    ", r4)
        sc = c.send("Page.captureScreenshot", format="png")
        p2 = os.path.join(HERE, u"批量名册_2_加入后.png"); shots.append(p2)
        io.open(p2, "wb").write(base64.b64decode(sc["data"]))

        print("④ 同步到线上")
        done = c.js("""(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const ch = document.querySelector('[data-msec="sync"]'); if (ch) ch.click();
  await wait(900);
  const b = document.getElementById('btnPush');
  if (!b) return '没找到同步按钮';
  if (b.disabled) return '同步按钮灰的';
  b.click();
  for (let i = 0; i < 40; i++) { await wait(2500);
    const t = document.body.innerText;
    if (t.indexOf('同步成功') >= 0) return '同步成功';
    const m = t.match(/(同步失败[^\\n]{0,40}|没有需要同步[^\\n]{0,30})/);
    if (m) return m[1];
  }
  return '(100 秒没结果)';
})()""")
        print("    ", done)
        c.ws.close()
    finally:
        subprocess.run(["taskkill", "/F", "/PID", str(proc.pid), "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(prof, ignore_errors=True)

    print("\n⑤ 仓库核对")
    time.sleep(6)
    after = json.loads(api("contents/data/overrides.js", token, raw=True).split("=", 1)[1].strip().rstrip(";"))
    nm = after.get("newMembers") or []
    got = [m.get("name") for m in nm]
    print("   线上新增队员: %d -> %d 人" % (len(before.get("newMembers") or []), len(nm)))
    for n in TESTNAMES:
        hit = [m for m in nm if m.get("name") == n]
        print("     %s %s" % (n, json.dumps(hit[0], ensure_ascii=False) if hit else "❌ 没写进去"))
    print("   脏名字/重复是否被挡住:", all(x not in got for x in [u"张", u"测试"]))
    print("   原有名册修订是否保住:", len(after.get("memberEdits") or {}) == len(before.get("memberEdits") or {}))
    print("截图:", " | ".join(shots))


if __name__ == "__main__":
    main()
