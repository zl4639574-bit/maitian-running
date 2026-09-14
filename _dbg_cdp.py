# -*- coding: utf-8 -*-
"""定位 手机检查.py 卡在哪一步"""
import json, os, socket, subprocess, tempfile, time, urllib.request
import websocket

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


port = free_port()
prof = tempfile.mkdtemp(prefix="edge_dbg_")
print("1) 端口", port, "配置目录", prof)

args = [EDGE, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
        "--remote-allow-origins=*", "--remote-debugging-port=%d" % port,
        "--user-data-dir=" + prof, "about:blank"]
p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("2) 已启动 pid", p.pid)

ok = False
for i in range(40):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=1) as r:
            json.loads(r.read()); ok = True; break
    except Exception:
        time.sleep(0.5)
print("3) DevTools 就绪:", ok)

targets = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/json/list" % port, timeout=5).read())
pages = [t for t in targets if t.get("type") == "page"]
print("4) page 目标数:", len(pages), [t.get("url") for t in pages][:3])

if pages:
    ws_url = pages[0]["webSocketDebuggerUrl"]
    print("5) 连接", ws_url[:60], "...")
    ws = websocket.create_connection(ws_url, timeout=30, suppress_origin=True)
    print("6) 已连接，发送 Runtime.evaluate")
    def call(m, prm, timeout=15):
        global _id
        _id += 1
        t0 = time.time()
        ws.send(json.dumps({"id": _id, "method": m, "params": prm}))
        while time.time() - t0 < timeout:
            try:
                msg = json.loads(ws.recv())
            except Exception as e:
                return "TIMEOUT " + str(e)[:50]
            if msg.get("id") == _id:
                return "ok " + str(msg.get("result"))[:70]
        return "TIMEOUT"
    _id = 100
    print("A) Emulation:", call("Emulation.setDeviceMetricsOverride",
          {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True}))
    print("B) 用 JS 跳转:", call("Runtime.evaluate", {"expression":
          "location.assign('https://zl4639574-bit.github.io/maitian-running/'); 'go'", "returnByValue": True}))
    time.sleep(6)
    print("C) 页面状态:", call("Runtime.evaluate", {"expression":
          "document.readyState + ' | ' + location.href + ' | 标题=' + document.title + ' | 卡片=' + document.querySelectorAll('.card').length",
          "returnByValue": True}))
    ws.close()
