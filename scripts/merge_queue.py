# -*- coding: utf-8 -*-
"""
把「收集仓库」里队员直传的成绩合并进 data/overrides.js
由 .github/workflows/merge-queue.yml 每 10 分钟自动跑一次，也可以手动触发。
"""
import json, os, re, urllib.request, urllib.error, datetime

OWNER      = "zl4639574-bit"
QUEUE_REPO = "maitian-run-queue"
COMP_ID    = "member-uploads"
COMP_NAME  = "队员直传（队员自己上传）"
OV_PATH    = "data/overrides.js"
ST_PATH    = "data/queue-state.json"


def get_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "maitian-merge-bot",
        "Accept": "application/vnd.github+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        print("HTTP", e.code, url)
        return None
    except Exception as e:
        print("读取失败", url, e)
        return None


def load_overrides():
    if not os.path.exists(OV_PATH):
        return {}
    txt = open(OV_PATH, encoding="utf-8").read()
    m = re.search(r"window\.TEAM_OVERRIDES\s*=\s*([\s\S]*?);\s*$", txt)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except Exception as e:
        print("overrides.js 解析失败，放弃合并：", e)
        return {}


def main():
    # 1. 已处理过哪些提交
    processed = set()
    if os.path.exists(ST_PATH):
        try:
            processed = set(json.load(open(ST_PATH, encoding="utf-8")).get("processed", []))
        except Exception:
            pass

    # 2. 列出收集仓库里的提交
    items = get_json("https://api.github.com/repos/%s/%s/contents/queue" % (OWNER, QUEUE_REPO)) or []
    files = [it for it in items if isinstance(it, dict) and it.get("name", "").endswith(".json")
             and it["name"] not in processed]
    if not files:
        print("队列里没有新的提交")
        return

    # 3. 读内容
    recs, added = [], []
    for it in files:
        d = get_json(it.get("download_url") or "")
        if not d:
            continue
        for r in (d.get("records") or []):
            try:
                sec = float(r.get("sec"))
            except (TypeError, ValueError):
                continue
            name = str(r.get("name") or "").strip()
            if not name or sec <= 0:
                continue
            recs.append({
                "name": name,
                "event": str(r.get("event") or "距离未标注"),
                "sec": round(sec, 1),
                "fmt": str(r.get("fmt") or ""),
                "sex": str(r.get("sex") or ""),
                "college": str(r.get("college") or ""),
                "note": (str(r.get("note") or "") + " " + str(r.get("date") or "")).strip(),
                "srcDate": str(r.get("date") or ""),
            })
        added.append(it["name"])

    if not recs:
        print("提交里没有有效成绩")
        processed.update(added)
    else:
        ov = load_overrides()
        ov.setdefault("competitions", [])
        ov.setdefault("compRecords", {})
        if not any(c.get("id") == COMP_ID for c in ov["competitions"]):
            ov["competitions"].append({
                "id": COMP_ID, "name": COMP_NAME, "date": "",
                "event": "", "note": "队员自己在手机上提交的成绩，系统每 10 分钟自动合并到这里", "records": [],
            })
        cur = ov["compRecords"].get(COMP_ID, [])
        seen = {(r.get("name"), r.get("event"), r.get("sec")) for r in cur}
        n = 0
        for r in recs:
            k = (r["name"], r["event"], r["sec"])
            if k in seen:
                continue
            seen.add(k)
            cur.append(r)
            n += 1
        ov["compRecords"][COMP_ID] = cur
        ov["updated"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(OV_PATH, "w", encoding="utf-8") as f:
            f.write("/* 本文件由队长版「同步」和自动合并机器人维护 */\n")
            f.write("window.TEAM_OVERRIDES = " + json.dumps(ov, ensure_ascii=False, indent=1) + ";\n")
        processed.update(added)
        print("合并了 %d 条新成绩（来自 %d 份提交）" % (n, len(added)))

    with open(ST_PATH, "w", encoding="utf-8") as f:
        json.dump({"processed": sorted(processed),
                   "updated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")},
                  f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
