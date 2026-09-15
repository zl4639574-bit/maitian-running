# -*- coding: utf-8 -*-
"""跑 _自检.html：本地 http 起站 → 临时 Edge 打开 → 读 #testlog（不碰线上/用户浏览器）
用法：python _跑自检html.py [mode]   默认 captain"""
import importlib.util, io, json, os, socket, subprocess, sys, time, urllib.request, base64

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "captain")
    shot = sys.argv[2] if len(sys.argv) > 2 else ""
    sys.path.insert(0, HERE)
    spec = importlib.util.spec_from_file_location("ph", os.path.join(HERE, "手机检查.py"))
    ph = importlib.util.module_from_spec(spec); spec.loader.exec_module(ph)

    s = socket.socket(); s.bind(("127.0.0.1", 0)); hp = s.getsockname()[1]; s.close()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(hp), "--bind", "127.0.0.1"],
                           cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import urllib.parse
    page = urllib.parse.quote("_自检.html")
    url = "http://127.0.0.1:%d/%s?mode=%s" % (hp, page, mode)
    proc = None
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
        ph.goto(c, url, wait=25)
        log = ""
        for _ in range(40):
            time.sleep(0.5)
            log = c.js("(function(){var d=document.getElementById('testlog');return d?d.textContent:'';})()") or ""
            if log:
                break
        print("MODE =", mode)
        for part in log.split(" ~~ "):
            print("  ", part)
        bad = [p for p in log.split(" ~~ ") if "ERR" in p or "EXCEPTION" in p]
        print("\n异常项：", bad if bad else "无")
        if shot:
            r = c.send("Page.captureScreenshot", format="png", captureBeyondViewport=True)
            io.open(shot, "wb").write(base64.b64decode(r["data"]))
            print("截图：", shot)
        return 1 if bad else 0
    finally:
        try:
            if proc: proc.terminate()
        except Exception:
            pass
        srv.terminate()


if __name__ == "__main__":
    sys.exit(main())
