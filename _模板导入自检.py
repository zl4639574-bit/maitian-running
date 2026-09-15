# -*- coding: utf-8 -*-
"""自检：三个上传模板「表头对不对、能不能真的导进去」
   做法：照模板表头生成带 2 行示例的文件 → 本地起站 + 临时 Edge → 用 CDP 把文件塞进
        三个 file input（成绩批量导入 / 导入收集表 / 批量添加队员）→ 看预览和落库结果。
   全程只动临时浏览器与临时文件；不碰线上、不碰用户浏览器。
"""
import importlib.util, io, json, os, socket, subprocess, sys, tempfile, time, urllib.request
from openpyxl import Workbook

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)

ROWS = {
    '01': (['姓名', '性别', '学院', '专业', '年级', '800米', '1500米', '3000米', '5000米', '10000米', '半马', '全马'],
           [['测试甲', '男', '林学院', '林学2101', '2023', '无', '无', '10:20', '18:35', '无', '无', '无'],
            ['测试乙', '女', '园艺学院', '园艺2102', '2023', '2:50', '无', '无', '23:10', '无', '无', '无']]),
    '02': (['姓名', '性别', '学院', '成绩', '名次'],
           [['测试甲', '男', '林学院', '18:35', '1'], ['测试乙', '女', '园艺学院', '23:10', '2']]),
    '03': (['姓名', '学院', '专业', '年级', '性别', '身份'],
           [['测试丙', '林学院', '林学2101', '2023', '男', '正式'],
            ['测试丁', '园艺学院', '园艺2102', '2023', '女', '预备']]),
}


def make(path, key):
    head, rows = ROWS[key]
    wb = Workbook(); ws = wb.active
    ws.append(head)
    for r in rows:
        ws.append(r)
    wb.save(path)


def main():
    tmp = tempfile.mkdtemp(prefix="mt_tpl_")
    files = {}
    for k in ('01', '02', '03'):
        p = os.path.join(tmp, 't%s.xlsx' % k)
        make(p, k)
        files[k] = p

    s = socket.socket(); s.bind(("127.0.0.1", 0)); hp = s.getsockname()[1]; s.close()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(hp), "--bind", "127.0.0.1"],
                           cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = "http://127.0.0.1:%d/captain/" % hp
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

        def load(tag=""):
            for _ in range(5):
                ph.goto(c, url + "?r=%d%s" % (int(time.time() * 1000) % 100000, tag), wait=25)
                for _ in range(40):
                    time.sleep(0.3)
                    if int(str(c.js("document.querySelectorAll('.nav-item').length") or 0)) >= 3:
                        return True
            return False

        def setfile(sel, path):
            doc = c.send("DOM.getDocument")
            n = c.send("DOM.querySelector", nodeId=doc["root"]["nodeId"], selector=sel)
            nid = n.get("nodeId") or 0
            if not nid:
                return False
            c.send("DOM.setFileInputFiles", files=[path.replace('/', '\\')], nodeId=nid)
            return True

        def tab(label, wait=1200):
            return c.js("(async()=>{const w=ms=>new Promise(r=>setTimeout(r,ms));"
                        "for(const n of document.querySelectorAll('.nav-item,[data-tab]'))"
                        " if((n.textContent||'').trim()===%s){n.click();break;} await w(%d); return 'ok';})()"
                        % (json.dumps(label, ensure_ascii=False), wait))

        def msec(label, wait=1200):
            return c.js("(async()=>{const w=ms=>new Promise(r=>setTimeout(r,ms));"
                        "const t=Array.from(document.querySelectorAll('[data-msec]')).find(x=>x.textContent.trim()===%s);"
                        "if(t)t.click(); await w(%d); return 'ok';})()"
                        % (json.dumps(label, ensure_ascii=False), wait))

        if not load():
            print("!! 页面没起来"); return 1

        # ① 成绩单模板 → 上传成绩 → ②批量导入
        tab("上传成绩")
        ok_a1 = setfile('#fileInput', files['02'])
        time.sleep(2.5)
        r1 = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms)); await w(500);
  const box = document.getElementById('importArea');
  const t = box ? box.textContent.replace(/\s+/g,' ') : '';
  const m = t.match(/已读取 [^\s]+，(\d+) 行数据/);
  return { rows: m ? +m[1] : null, head: t.slice(0, 150), prev: t.indexOf('测试甲') >= 0 && t.indexOf('18:35') >= 0 };
})()""")
        print("① 上传成绩←02成绩单：", json.dumps(r1, ensure_ascii=False))
        ok_a = ok_a1 and r1["rows"] == 2 and r1["prev"]
        res.append(("① 02_一场比赛成绩单 的表头能被「批量导入」认出来（2 行）", ok_a))

        # ② 收集表模板 → 数据管理→队员名册→导入收集表
        tab("数据管理"); msec("队员名册")
        ok_b1 = setfile('#docSheetFile', files['01'])
        time.sleep(2.5)
        r2 = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms)); await w(500);
  const box = document.getElementById('docSheetArea');
  const t = box ? box.textContent.replace(/\s+/g,' ') : '';
  const m = t.match(/读到\s*(\d+)\s*个人/);
  return { n: m ? +m[1] : null, hasPb: t.indexOf('5000米 18:35') >= 0, head: t.slice(0, 170) };
})()""")
        # 点「全部导入」，看有没有落进本机草稿
        c.js("(function(){const b=document.getElementById('btnSheetDo'); if(b)b.click(); return 1;})()")
        time.sleep(2.5)
        r2b = c.js("""(function(){const d=JSON.parse(localStorage.getItem('mt_ov_local_v1')||'{}');
  return { edited: Object.keys(d.memberEdits||{}), pb: (d.pbAdded||[]).map(p=>p.name+' '+p.event+' '+p.fmt) };})()""")
        print("② 队员名册←01收集表：", json.dumps(dict(r2, **{"落库": r2b}), ensure_ascii=False))
        ok_b = (ok_b1 and r2["n"] == 2 and r2["hasPb"]
                and set(r2b["edited"]) == {"测试甲", "测试乙"} and len(r2b["pb"]) == 4)   # 甲2条(3000/5000) + 乙2条(800/5000)
        res.append(("② 01_队员资料收集表 能被「导入收集表」识别并落库（2 人、2 条成绩）", ok_b))

        # ③ 名册模板 → 批量添加队员
        c.js("localStorage.removeItem('mt_ov_local_v1'); 'ok'")
        c.js("(function(){const t=Array.from(document.querySelectorAll('[data-msec]')).find(x=>x.textContent.trim()==='队员名册');if(t)t.click();return 1;})()")
        time.sleep(1.2)
        ok_c1 = setfile('#nmFileInput', files['03'])
        time.sleep(2.5)
        r3 = c.js(r"""(async () => {
  const w = ms => new Promise(r => setTimeout(r, ms)); await w(600);
  const box = document.getElementById('nmBatchBox');
  const t = box ? box.textContent.replace(/\s+/g,' ') : '';
  return { txt: t.slice(0, 200), has2: t.indexOf('测试丙') >= 0 && t.indexOf('测试丁') >= 0,
           hasLevel: t.indexOf('正式') >= 0 && t.indexOf('预备') >= 0 };
})()""")
        print("③ 队员名册←03名册表：", json.dumps(r3, ensure_ascii=False))
        ok_c = ok_c1 and r3["has2"] and r3["hasLevel"]
        res.append(("③ 03_名册批量添加 能被「批量添加队员」识别（2 人、含身份）", ok_c))

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
