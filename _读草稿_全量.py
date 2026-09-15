# -*- coding: utf-8 -*-
"""按字节顺序精确读出 leveldb 日志里 mt_ov_local_v1 的每一次写入（只读）"""
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


for p in sorted(glob.glob(os.path.join(D, "*")), key=os.path.getmtime):
    if not p.endswith((".log", ".ldb")):
        continue
    b = io.open(p, "rb").read()
    print("=" * 80)
    print("%s  %d 字节  %s" % (os.path.basename(p),
          len(b), datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%m-%d %H:%M:%S")))
    # 1) 找 UTF-16LE 的 "{" 起始（值以 {\x00"\x00 开头），2) 找 UTF-8 的 {" 起始
    cands = []
    for m in re.finditer(re.escape(b'{\x00"\x00'), b):
        cands.append((m.start(), "utf-16-le"))
    for m in re.finditer(re.escape(b'{"'), b):
        cands.append((m.start(), "utf-8"))
    hits = []
    for off, enc in cands:
        try:
            t = b[off:off + 400000].decode(enc, "ignore")
        except Exception:
            continue
        s = balanced(t, 0)
        if not s or len(s) < 15:
            continue
        try:
            o = json.loads(s)
        except Exception:
            continue
        if not isinstance(o, dict):
            continue
        if not ({"memberEdits", "newMembers"} & set(o)):
            continue
        hits.append((off, enc, o, s))
    hits.sort(key=lambda x: x[0])
    for off, enc, o, s in hits:
        me = o.get("memberEdits") or {}
        print("  -- 偏移 %d [%s] 长度 %d" % (off, enc, len(s)))
        print("     keys: %s" % list(o.keys()))
        print("     newMembers(%d): %s" % (len(o.get("newMembers") or []),
              [x.get("name") for x in (o.get("newMembers") or [])]))
        for k, v in me.items():
            print("     edit[%s] = %s" % (k, json.dumps(v, ensure_ascii=False)))
        print("     hidden=%s pbAdded=%s results=%s" % (o.get("hidden"), len(o.get("pbAdded") or []),
              len(o.get("results") or [])))
