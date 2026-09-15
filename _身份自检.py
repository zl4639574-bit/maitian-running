# -*- coding: utf-8 -*-
"""自检：身份（正式 / 预备 / 普通）这一条链路
   ① 队员端「完善我的资料」能选身份并存进草稿、资料文本里带「身份」行
   ② 队长端导入这份资料 → 身份写进名册；原来身份是「队员」的人从此进公开名册
   ③ 身份选「普通」→ 不进公开名册（原来在名册里的也会退出去）
   ④ normLevelOf：正式/预备/普通 认；空 = 不进名册；看不懂（队员）= 不动
"""
import importlib.util, json, os, socket, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)


def main():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); hp = s.getsockname()[1]; s.close()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(hp), "--bind", "127.0.0.1"],
                           cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d/" % hp
    proc = None
    res = []
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

        def load(path):
            for _ in range(5):
                ph.goto(c, base + path + "?r=%d" % (int(time.time() * 1000) % 100000), wait=25)
                for _ in range(40):
                    time.sleep(0.3)
                    if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 2:
                        return True
            return False

        # ① 队员端：完善我的资料 → 选身份 → 保存
        load("report/")
        r1 = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  for (const n of document.querySelectorAll('.nav-item,[data-tab]'))
    if ((n.textContent||'').trim() === '完善我的资料') { n.click(); break; }
  await w(1200);
  const sel = document.getElementById('me_level');
  if (!sel) return { err: '没有身份下拉' };
  const opts = Array.from(sel.options).map(o => o.value + '/' + o.textContent.trim());
  document.getElementById('me_name').value = '张津浩';       // 原始名册里身份是「队员」的人（公开名册看不到）
  document.getElementById('me_college').value = '林学院';
  sel.value = '预备';
  document.getElementById('meSave').click();
  await w(500);
  const d = JSON.parse(localStorage.getItem('mt_me_v1') || '{}');
  const txt = (typeof meText === 'function') ? meText(d) : '';
  return { opts: opts, level: d.level, txtHasLevel: txt.indexOf('身份\t预备') >= 0,
           txt: txt.split('\n').slice(0, 7) };
})()""")
        print("① 队员端完善资料：", json.dumps(r1, ensure_ascii=False))
        ok1 = (not r1.get("err") and r1["level"] == "预备" and r1["txtHasLevel"]
               and any(o.startswith("正式/") for o in r1["opts"]) and any(o.startswith("预备/") for o in r1["opts"])
               and any(o.startswith("普通/") for o in r1["opts"]))
        res.append(("① 完善我的资料有 正式/预备/普通 三档，选了会存进资料（含「身份」行）", ok1))

        # ②③ 队长端：用同一份资料走导入链路
        load("captain/")
        r2 = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  const before = rosterList().map(m => m.name);
  const out = { zjhInBefore: before.indexOf('张津浩') >= 0, gjjInBefore: before.indexOf('郭家俊') >= 0 };
  // 张津浩：原始身份「队员」，资料里写 预备 → 导入后应该进公开名册
  await applyMemberDoc({ type: 'maitian-member', name: '张津浩', sex: '男', college: '林学院',
                         major: '林学2101', grade: '2024', level: '预备', pb: {} });
  await w(300);
  out.zjhInAfter = rosterList().map(m => m.name).indexOf('张津浩') >= 0;
  out.zjhLevel = (ov().memberEdits['张津浩'] || {}).level;
  // 郭家俊：本来在名册里，资料里写 普通 → 导入后应该退出公开名册
  await applyMemberDoc({ type: 'maitian-member', name: '郭家俊', sex: '男', college: '动物科技学院',
                         major: '动科1905', grade: '2017', level: '普通', pb: {} });
  await w(300);
  out.gjjInAfter = rosterList().map(m => m.name).indexOf('郭家俊') >= 0;
  out.gjjLevel = (ov().memberEdits['郭家俊'] || {}).level;
  out.count = rosterList().length;
  // normLevelOf 口径
  out.norm = { '正式': normLevelOf('正式'), '普通': normLevelOf('普通'), '正式,预备': normLevelOf('正式,预备'),
               '空': normLevelOf(''), '队员': normLevelOf('队员') };
  return out;
})()""")
        print("② 队长端导入：", json.dumps(r2, ensure_ascii=False))
        ok2 = (r2["zjhInBefore"] is False and r2["zjhInAfter"] is True and r2["zjhLevel"] == ["预备"])
        ok3 = (r2["gjjInBefore"] is True and r2["gjjInAfter"] is False and r2["gjjLevel"] == ["普通"])
        ok4 = (r2["norm"]["正式"] == ["正式"] and r2["norm"]["普通"] == ["普通"]
               and r2["norm"]["正式,预备"] == ["正式", "预备"] and r2["norm"]["空"] == [] and r2["norm"]["队员"] is None)
        res.append(("② 资料里写「预备」→ 原始身份是「队员」的人进公开名册", ok2))
        res.append(("③ 资料里写「普通」→ 从公开名册里退出（不显示）", ok3))
        res.append(("④ 身份口径：正式/预备/普通 认；空=不进名册；「队员」看不懂=不动", ok4))

        print()
        for name, ok in res:
            print(("✅ " if ok else "❌ ") + name)
        return 0 if all(ok for _, ok in res) else 1
    finally:
        try:
            if proc: proc.terminate()
        except Exception:
            pass
        srv.terminate()


if __name__ == "__main__":
    sys.exit(main())
