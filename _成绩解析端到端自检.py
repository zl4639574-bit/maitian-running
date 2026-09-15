# -*- coding: utf-8 -*-
"""端到端自检：成绩「1:24:00」在每条录入路径上都读成 1 小时 24 分（不是 1 分 24 秒）
   ① 上传成绩表单（带成绩栏"识别为"提示 + 项目不对时的提醒）
   ② 单独添加个人最好成绩
   ③ 队员资料导入（pb 列）
   ④ 批量导入成绩单（页面上选的项目要能带进解析）
"""
import importlib.util, io, json, os, socket, subprocess, sys, time, urllib.request
from openpyxl import Workbook

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)


def main():
    tmp = os.path.join(os.environ.get('TEMP', '.'), 'mt_sec_t')
    os.makedirs(tmp, exist_ok=True)
    xl = os.path.join(tmp, 'banshi.xlsx')
    wb = Workbook(); ws = wb.active
    ws.append(['姓名', '性别', '学院', '成绩', '名次'])
    ws.append(['测试跑者', '男', '林学院', '1:24:00', '1'])
    wb.save(xl)

    s = socket.socket(); s.bind(("127.0.0.1", 0)); hp = s.getsockname()[1]; s.close()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(hp), "--bind", "127.0.0.1"],
                           cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d/captain/" % hp
    proc = None
    res = []
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
        for _ in range(5):
            ph.goto(c, base + "?r=%d" % (int(time.time() * 1000) % 100000), wait=25)
            if (c.js("location.href") or "").startswith("http://127.0.0.1"):
                break
        for _ in range(40):
            time.sleep(0.3)
            if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 3:
                break

        c.js("window.confirm = function () { return true; }; 'ok'")   # 页面里的 confirm 会卡住 CDP，一律当"确定"

        def tab(label, wait=1200):
            return c.js("(async()=>{const w=ms=>new Promise(r=>setTimeout(r,ms));"
                        "for(const n of document.querySelectorAll('.nav-item,[data-tab]'))"
                        " if((n.textContent||'').trim()===%s){n.click();break;} await w(%d); return 'ok';})()"
                        % (json.dumps(label, ensure_ascii=False), wait))

        # ① 上传成绩表单
        tab("上传成绩")
        r1 = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  const set = (el, v) => { el.value = v; el.dispatchEvent(new Event('input', {bubbles:true})); };
  // 选「半马」项目
  const chip = Array.from(document.querySelectorAll('[data-ty]')).find(x => x.textContent.trim() === '半马');
  if (chip) chip.click();
  await w(400);
  document.getElementById('f_name').value = '测试跑者';
  const fev = document.getElementById('f_event');
  set(fev, '半马');
  set(document.getElementById('f_result'), '1:24:00');
  await w(200);
  const hintOk = (document.getElementById('f_resultHint').textContent || '').trim();
  document.getElementById('btnAdd').click();
  await w(500);
  const mine = JSON.parse(localStorage.getItem('mt_results_v1') || '[]');
  const rec = mine[mine.length - 1] || {};
  // 再把项目改成 5000 米，看有没有"不太像"的提醒
  set(document.getElementById('f_event'), '5000米');
  set(document.getElementById('f_result'), '1:24:00');
  await w(200);
  const hintWarn = (document.getElementById('f_resultHint').textContent || '').trim();
  return { hintOk: hintOk, sec: rec.sec, fmt: rec.fmt, event: rec.event, hintWarn: hintWarn.slice(0, 40) };
})()""")
        print("① 上传成绩表单：", json.dumps(r1, ensure_ascii=False))
        ok1 = (r1["sec"] == 5040 and r1["fmt"] == "1:24:00" and r1["event"] == "半马"
               and r1["hintOk"].startswith("识别为") and r1["hintWarn"].startswith("⚠️"))
        res.append(("① 上传成绩：半马 1:24:00 → 1:24:00（5040 秒），提示正确", ok1))

        # ② 单独添加个人最好成绩
        tab("数据管理", 1200)
        c.js("(async()=>{const w=ms=>new Promise(r=>setTimeout(r,ms));"
             "const t=Array.from(document.querySelectorAll('[data-msec]')).find(x=>x.textContent.trim()==='队员名册');"
             "if(t)t.click(); await w(1200); return 1;})()")
        r2 = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  document.getElementById('pb_name').value = '测试跑者';
  document.getElementById('pb_event').value = '全马';
  document.getElementById('pb_time').value = '4:20:00';
  document.getElementById('btnAddPb').click();
  await w(500);
  const d = JSON.parse(localStorage.getItem('mt_ov_local_v1') || '{}');
  const last = (d.pbAdded || [])[(d.pbAdded || []).length - 1] || {};
  return { sec: last.sec, fmt: last.fmt, event: last.event };
})()""")
        print("② 单独添加最好成绩：", json.dumps(r2, ensure_ascii=False))
        ok2 = (r2["sec"] == 15600 and r2["fmt"] == "4:20:00")
        res.append(("② 单独添加：全马 4:20:00 → 4:20:00（15600 秒）", ok2))

        # ③ 队员资料导入（pb 列）
        r3 = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  await applyMemberDoc({ type: 'maitian-member', name: '测试跑者', sex: '男', level: '正式',
    pb: { '半马': '1:24:00', '全马': '4:20:00', '5000米': '18:35' } });
  await w(400);
  const d = JSON.parse(localStorage.getItem('mt_ov_local_v1') || '{}');
  return (d.pbAdded || []).filter(p => p.name === '测试跑者').map(p => p.event + '=' + p.fmt + '(' + p.sec + ')');
})()""")
        print("③ 资料导入：", json.dumps(r3, ensure_ascii=False))
        ok3 = ("半马=1:24:00(5040)" in (r3 or []) and "全马=4:20:00(15600)" in (r3 or []) and "5000米=18:35(1115)" in (r3 or []))
        res.append(("③ 资料导入：半马/全马/5000米 三个都对", ok3))

        # ④ 批量导入成绩单（页面上选的项目带进解析）
        tab("上传成绩")
        c.send("DOM.getDocument")
        doc = c.send("DOM.getDocument")
        n = c.send("DOM.querySelector", nodeId=doc["root"]["nodeId"], selector='#fileInput')
        c.send("DOM.setFileInputFiles", files=[xl.replace('/', '\\')], nodeId=n["nodeId"])
        time.sleep(2.5)
        r4 = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  const sel = document.querySelector('[data-map="event"]');
  if (sel) { sel.value = '半马'; sel.dispatchEvent(new Event('change', {bubbles:true})); }
  await w(600);
  const prev = (document.getElementById('importArea').textContent || '').match(/测试跑者[^|]{0,20}/);
  document.getElementById('btnDoImport').click();
  await w(800);
  const mine = JSON.parse(localStorage.getItem('mt_results_v1') || '[]');
  const rec = mine.filter(x => x.name === '测试跑者').pop() || {};
  return { preview: prev ? prev[0] : '', sec: rec.sec, fmt: rec.fmt, event: rec.event };
})()""")
        print("④ 批量导入成绩单：", json.dumps(r4, ensure_ascii=False))
        ok4 = (r4["sec"] == 5040 and r4["event"] == "半马")
        res.append(("④ 批量导入：页面上选「半马」后 1:24:00 也读对", ok4))

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
