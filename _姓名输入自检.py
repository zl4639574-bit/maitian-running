# -*- coding: utf-8 -*-
"""自检：姓名输入不再给下拉提示（成绩上报 / 完善我的资料 / 名册管理里的添加成绩），
        检索框不再有浏览器自带的下拉（autocomplete=off），且输入不存在的名字会有提醒。"""
import importlib.util, json, os, socket, subprocess, sys, time, urllib.request, urllib.parse, base64, io

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)


def main():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); hp = s.getsockname()[1]; s.close()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(hp), "--bind", "127.0.0.1"],
                           cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d/" % hp
    proc = None
    results = []
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen(base + "index.html", timeout=1).read(100); break
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

        def load(path, tab=""):
            for _ in range(5):
                ph.goto(c, base + path + "?r=%d%s" % (int(time.time() * 1000) % 100000, tab), wait=25)
                for _ in range(40):
                    time.sleep(0.3)
                    if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 2:
                        return True
            return False

        # ── 队员端：成绩上报页 ──
        load("report/")
        r = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  const fn = document.getElementById('f_name');
  const before = { hasList: !!(fn && fn.getAttribute('list')), dl: document.querySelectorAll('datalist').length,
                   names: Array.from(document.querySelectorAll('datalist')).map(d => d.id) };
  fn.value = '张津浩'; fn.dispatchEvent(new Event('input'));      // 原始名册里的人 → 不该有提醒
  await w(120);
  const okHint = (document.getElementById('f_nameHint').textContent || '').trim();
  fn.value = '张金豪'; fn.dispatchEvent(new Event('input'));      // 名册里没有 → 要有提醒
  await w(120);
  const badHint = (document.getElementById('f_nameHint').textContent || '').trim();
  return { before: before, okHint: okHint, badHint: badHint.slice(0, 40), autocomplete: fn.getAttribute('autocomplete') };
})()""")
        print("① 成绩上报页：", json.dumps(r, ensure_ascii=False))
        ok1 = (r["before"]["hasList"] is False and "nameList" not in r["before"]["names"]
               and r["okHint"] == "" and r["badHint"].startswith("⚠️") and r["autocomplete"] == "off")
        results.append(("① 成绩上报姓名：无下拉、直接输入、名字不对有提醒", ok1))

        # ── 队员端：完善我的资料 ──
        c.js("(async()=>{const w=ms=>new Promise(r=>setTimeout(r,ms));"
             "for(const n of document.querySelectorAll('.nav-item,[data-tab]'))"
             " if((n.textContent||'').trim()==='完善我的资料'){n.click();break;} await w(1200); return 1;})()")
        r2 = c.js(r"""(function(){const el=document.getElementById('me_name');
  return { hasList: !!(el && el.getAttribute('list')), ac: el && el.getAttribute('autocomplete'),
           dl: Array.from(document.querySelectorAll('datalist')).map(d => d.id) };})()""")
        print("② 完善我的资料：", json.dumps(r2, ensure_ascii=False))
        ok2 = (r2["hasList"] is False and r2["ac"] == "off" and "meNameList" not in r2["dl"])
        results.append(("② 完善资料姓名：无下拉", ok2))

        # ── 展示版队员名册：检索框无浏览器推荐 ──
        load("index.html", "#roster")
        r3 = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  for (const n of document.querySelectorAll('.nav-item,[data-tab]'))
    if ((n.textContent||'').trim() === '队员名册') { n.click(); break; }
  await w(1200);
  const q = document.getElementById('rosterQ');
  if (!q) return { err: '没找到检索框' };
  q.value = '王金豪'; q.dispatchEvent(new Event('input', { bubbles: true }));
  await w(700);
  const cards = Array.from(document.querySelectorAll('.pcard')).map(x => ((x.querySelector('.nm')||{}).textContent||'').trim());
  return { ac: q.getAttribute('autocomplete'), list: q.getAttribute('list'),
           cardsAfterSearch: cards, n: cards.length };
})()""")
        print("③ 队员名册检索：", json.dumps(r3, ensure_ascii=False))
        ok3 = (r3.get("ac") == "off" and not r3.get("list") and r3.get("n") == 1 and "王金豪" in (r3.get("cardsAfterSearch") or []))
        results.append(("③ 队员名册检索：无推荐下拉，检索出最终结果", ok3))

        # ── 队长版：名册管理搜索 + 单独添加成绩的姓名 ──
        load("captain/")
        c.js("(async()=>{const w=ms=>new Promise(r=>setTimeout(r,ms));"
             "for(const n of document.querySelectorAll('.nav-item,[data-tab]'))"
             " if((n.textContent||'').trim()==='数据管理'){n.click();break;} await w(1000);"
             "const t=Array.from(document.querySelectorAll('[data-msec]')).find(x=>x.textContent.trim()==='队员名册');"
             "if(t)t.click(); await w(1200); return 1;})()")
        r4 = c.js(r"""(function(){const m=document.getElementById('mRosterQ'), p=document.getElementById('pb_name');
  return { mq: m && m.getAttribute('autocomplete'), pb: p ? p.getAttribute('list') : 'no-input',
           dl: Array.from(document.querySelectorAll('datalist')).map(d => d.id),
           pbNames: !!document.getElementById('pbNames') };})()""")
        print("④ 队长版名册管理：", json.dumps(r4, ensure_ascii=False))
        ok4 = (r4["mq"] == "off" and r4["pb"] is None and r4["pbNames"] is False)
        results.append(("④ 队长版：名册搜索无推荐、添加成绩姓名直接输入", ok4))

        print()
        for name, ok in results:
            print(("✅ " if ok else "❌ ") + name)
        return 0 if all(ok for _, ok in results) else 1
    finally:
        try:
            if proc: proc.terminate()
        except Exception:
            pass
        srv.terminate()


if __name__ == "__main__":
    sys.exit(main())
