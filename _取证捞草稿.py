# -*- coding: utf-8 -*-
"""取证：把 Edge LevelDB 里历史版本的 mt_ov_local_v1 全部抠出来，尽量还原用户加的队员"""
import os, io, json, re, datetime

U = os.path.expandvars(r'%LOCALAPPDATA%')
base = os.path.join(U, 'Microsoft', 'Edge', 'User Data', 'Default', 'Local Storage', 'leveldb')
files = [os.path.join(base, f) for f in os.listdir(base)]
files.sort(key=lambda p: os.path.getmtime(p))
print('文件：')
for p in files:
    print('   %s  %8d  %s' % (datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime('%m-%d %H:%M:%S'),
                              os.path.getsize(p), os.path.basename(p)))

def extract_objs(b, enc):
    """在字节流里找每个 mt_ov_local_v1 之后第一个配平的 JSON 对象"""
    out = []
    pat = 'mt_ov_local_v1'.encode(enc)
    start = 0
    while True:
        i = b.find(pat, start)
        if i < 0:
            break
        start = i + len(pat)
        tail = b[i:i + 400000].decode(enc, 'ignore')
        j = tail.find('{')
        if j < 0:
            continue
        depth = 0
        instr = False
        esc = False
        for n in range(j, len(tail)):
            ch = tail[n]
            if instr:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    instr = False
                continue
            if ch == '"':
                instr = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    out.append((i, tail[j:n + 1]))
                    break
    return out

seen = set()
for p in files:
    try:
        b = io.open(p, 'rb').read()
    except Exception:
        continue
    for enc in ('utf-8', 'utf-16-le'):
        for off, blob in extract_objs(b, enc):
            try:
                o = json.loads(blob)
            except Exception:
                continue
            nm = o.get('newMembers') or []
            me = o.get('memberEdits') or {}
            key = json.dumps(o, ensure_ascii=False, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            print('\n--- %s @%d [%s]  keys=%s' % (os.path.basename(p), off, enc, ','.join(sorted(o.keys())) or '(空)'))
            if nm:
                print('    新增队员 %d 人：' % len(nm))
                for m in nm:
                    print('      · %s | %s | %s | %s | 身份=%s | uid=%s | addedAt=%s' % (
                        m.get('name'), m.get('sex'), m.get('college'), m.get('grade'),
                        m.get('level'), m.get('uid'), m.get('addedAt')))
            if me:
                print('    修改 %d 人：' % len(me))
                for k, v in list(me.items())[:60]:
                    print('      · %s -> %s' % (k, json.dumps(v, ensure_ascii=False)))
            for kk in ('matches', 'hiddenResults', 'photos', 'albums'):
                if o.get(kk):
                    print('    %s: %d 项' % (kk, len(o[kk])))
print('\n(共 %d 个不同版本对象)' % len(seen))
