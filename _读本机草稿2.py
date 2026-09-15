# -*- coding: utf-8 -*-
"""全量只读扫描：所有浏览器 profile 的 Local Storage，列出 mt_ 键的每条记录 + 来源 origin"""
import os, io, json, datetime, re

U = os.path.expandvars(r'%LOCALAPPDATA%')
BASES = ['Microsoft/Edge', 'Google/Chrome', 'Chromium', 'BraveSoftware/Brave-Browser',
         '360Chrome/Chrome', '360se6/User Data', 'Tencent/QQBrowser', 'Vivaldi', 'Opera Software/Opera Stable']
files = []
for rel in BASES:
    base = os.path.join(U, *rel.split('/'))
    if not os.path.isdir(base):
        continue
    for dirpath, dirnames, filenames in os.walk(base):
        if os.path.basename(dirpath).lower() == 'leveldb' and 'local storage' in dirpath.lower():
            for f in filenames:
                if f.endswith(('.log', '.ldb')):
                    files.append(os.path.join(dirpath, f))
        if dirpath.count(os.sep) - base.count(os.sep) > 3:
            dirnames[:] = []

print('扫描到 LocalStorage 文件 %d 个' % len(files))
KEYS = ['mt_ov_local_v1', 'mt_results_v1', 'mt_sync_cfg_v1', 'mt_token', 'mt_bak']
found = 0
for p in sorted(files, key=lambda x: os.path.getmtime(x)):
    b = io.open(p, 'rb').read()
    rel = p.replace(U, '%LOCALAPPDATA%')
    mt = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime('%m-%d %H:%M:%S')
    for k in KEYS:
        for enc in ('utf-8', 'utf-16-le'):
            pat = k.encode(enc)
            start = 0
            while True:
                i = b.find(pat, start)
                if i < 0:
                    break
                start = i + len(pat)
                found += 1
                ctx = b[max(0, i - 120):i + 40].decode(enc, 'ignore')
                org = ''
                m = re.search(r'([a-z]+://[^\x00-\x1f\x02\x03"]{4,80})[\x00-\x1f\x02\x03]*$', ctx)
                if m:
                    org = m.group(1)
                tail = b[i:i + 40000].decode(enc, 'ignore')
                j = tail.find('{')
                note = ''
                if j >= 0:
                    depth = 0
                    for n in range(j, min(len(tail), j + 300000)):
                        if tail[n] == '{':
                            depth += 1
                        elif tail[n] == '}':
                            depth -= 1
                            if depth == 0:
                                blob = tail[j:n + 1]
                                break
                    else:
                        blob = tail[j:j + 30000]
                    try:
                        o = json.loads(blob)
                        if k == 'mt_ov_local_v1':
                            nm = o.get('newMembers') or []
                            note = '新增队员 %d 人 %s | memberEdits %d | matches %d | hidden %d | 空对象=%s' % (
                                len(nm), [x.get('name') for x in nm][:20], len(o.get('memberEdits') or {}),
                                len(o.get('matches') or []), len(o.get('hiddenResults') or []), len(o) == 0)
                        elif k == 'mt_results_v1':
                            note = json.dumps({kk: (len(v) if hasattr(v, '__len__') else v) for kk, v in o.items()},
                                              ensure_ascii=False)[:300] if isinstance(o, dict) else str(len(o))
                        else:
                            note = '(含令牌，不显示内容)' if 'token' in k else json.dumps(o, ensure_ascii=False)[:200]
                    except Exception as e:
                        note = 'JSON坏/被覆盖 (%.40s)' % blob[:40].replace('\n', ' ')
                print('%-30s %s  %-18s %-6s  origin=%-45s  %s' % (rel.split('User Data')[-1][:30], mt, k, enc, org[:45], note))
if not found:
    print('=> 完全没有 mt_ 开头的记录（说明这台电脑浏览器里没有队长版数据）')
