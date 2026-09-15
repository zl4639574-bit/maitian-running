# -*- coding: utf-8 -*-
"""取证：读用户浏览器里「本机录入的成绩」mt_results_v1 / 草稿 mt_ov_local_v1（只读）
   看 1:24:00 那条到底被存成了什么"""
import io, os, re, json, glob, datetime

D = r"C:\Users\15749\AppData\Local\Microsoft\Edge\User Data\Default\Local Storage\leveldb"


def balanced(text, start):
    op = text[start]
    cl = "}" if op == "{" else "]"
    depth, instr, esc = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if instr:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                instr = False
            continue
        if ch == '"':
            instr = True
        elif ch == op:
            depth += 1
        elif ch == cl:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def grab(path, want):
    """返回 [(偏移, 解析出的对象)]，只匹配含 want 这些键的对象"""
    b = io.open(path, "rb").read()
    out = []
    for enc, pat in (("utf-16-le", b'{\x00"\x00'), ("utf-8", b'{"')):
        for m in re.finditer(re.escape(pat), b):
            off = m.start()
            try:
                t = b[off:off + 300000].decode(enc, "ignore")
            except Exception:
                continue
            s = balanced(t, 0)
            if not s or len(s) < 12:
                continue
            try:
                o = json.loads(s)
            except Exception:
                continue
            if isinstance(o, (list, dict)) and any(k in s for k in want):
                out.append((off, o))
    return out


for p in sorted(glob.glob(os.path.join(D, "*")), key=os.path.getmtime):
    if not p.endswith(".log"):
        continue
    hits = grab(p, ['"raw"', 'results', 'memberEdits'])
    if not hits:
        continue
    print("=" * 78)
    print(os.path.basename(p), datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%m-%d %H:%M:%S"))
    for off, o in sorted(hits, key=lambda x: x[0]):
        if isinstance(o, list):
            print("  -- 偏移 %d：列表 %d 条" % (off, len(o)))
            for r in o[-6:]:
                if isinstance(r, dict):
                    print("     %s | %s | raw=%r | sec=%r | fmt=%r | date=%s | meet=%s"
                          % (r.get("name"), r.get("event"), r.get("raw"), r.get("sec"), r.get("fmt"),
                             r.get("date"), r.get("meet")))
        else:
            l = o.get("results")
            if isinstance(l, list) and l:
                print("  -- 偏移 %d：草稿 results %d 条" % (off, len(l)))
                for r in l[-6:]:
                    print("     %s | %s | raw=%r | sec=%r | fmt=%r" % (r.get("name"), r.get("event"),
                                                                        r.get("raw"), r.get("sec"), r.get("fmt")))
