# -*- coding: utf-8 -*-
"""取证 2：把 leveldb 里所有 JSON 值（数组/对象）都捞出来，找 1:24 相关的记录（只读）"""
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


def json_objs(b, enc, start_pat):
    out = []
    for m in re.finditer(re.escape(start_pat), b):
        off = m.start()
        try:
            t = b[off:off + 400000].decode(enc, "ignore")
        except Exception:
            continue
        s = balanced(t, 0)
        if not s or len(s) < 8:
            continue
        try:
            o = json.loads(s)
        except Exception:
            continue
        out.append((off, o, s))
    return out


PAT_KEYS = ('mt_results_v1', 'mt_ov_local_v1')

for p in sorted(glob.glob(os.path.join(D, "*")), key=os.path.getmtime):
    if not p.endswith(".log"):
        continue
    b = io.open(p, "rb").read()
    mt = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%m-%d %H:%M:%S")
    found = []
    for enc, pat in (("utf-16-le", b'[\x00"\x00'), ("utf-8", b'["'), ("utf-16-le", b'{\x00"\x00'), ("utf-8", b'{"')):
        for off, o, s in json_objs(b, enc, pat):
            if isinstance(o, list):
                rows = [x for x in o if isinstance(x, dict) and x.get('name')]
                if rows:
                    found.append((off, enc, rows, s))
            elif isinstance(o, dict) and (o.get('results') or o.get('pbAdded')):
                rows = o.get('results') or o.get('pbAdded')
                found.append((off, enc, rows, s))
            elif isinstance(o, dict) and o.get('name') and 'sec' in o:
                found.append((off, enc, [o], s))
    if not found:
        continue
    print("=" * 78)
    print("%s  %s  （%d 处）" % (os.path.basename(p), mt, len(found)))
    for off, enc, rows, s in sorted(found, key=lambda x: x[0]):
        print("  -- 偏移 %d [%s]" % (off, enc))
        for r in rows:
            print("     %s | %s | raw=%r | sec=%r | fmt=%r | date=%s | meet=%s | src=%s"
                  % (r.get("name"), r.get("event"), r.get("raw"), r.get("sec"), r.get("fmt"),
                     r.get("date"), r.get("meet"), r.get("srcLabel") or r.get("source") or ''))
        if '1:24' in s or ':24:00' in s or '"sec": 84' in s or '"sec":84' in s or '5040' in s:
            i = max(0, s.find('1:24') - 120)
            print("     >>> 命中片段：", s[i:i + 260].replace('\n', ' '))
