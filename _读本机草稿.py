# -*- coding: utf-8 -*-
"""只读扫描本机浏览器 localStorage，找还没同步的队长版草稿（不修改任何文件）"""
import os, re, io, glob, json, sys

U = os.path.expandvars(r'%LOCALAPPDATA%')
CAND = []
for base in [os.path.join(U, 'Microsoft', 'Edge', 'User Data'),
             os.path.join(U, 'Google', 'Chrome', 'User Data'),
             os.path.join(U, 'Chromium', 'User Data')]:
    if not os.path.isdir(base):
        continue
    for prof in os.listdir(base):
        d = os.path.join(base, prof, 'Local Storage', 'leveldb')
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith(('.log', '.ldb')):
                    CAND.append(os.path.join(d, f))

print('浏览器 LocalStorage 文件数：%d' % len(CAND))

KEYS = ['mt_ov_local_v1', 'mt_results_v1', 'mt_sync_cfg_v1', 'mt_token']
hits = {}
for p in sorted(CAND, key=lambda x: os.path.getmtime(x)):
    try:
        b = io.open(p, 'rb').read()
    except Exception:
        continue
    if b'mt_' not in b and 'mt_'.encode('utf-16-le') not in b:
        continue
    for k in KEYS:
        for enc, tag in ((None, 'utf8'), ('utf-16-le', 'u16')):
            pat = k.encode() if enc is None else k.encode('utf-16-le')
            i = b.rfind(pat)
            if i < 0:
                continue
            tail = b[i:i + 60000]
            try:
                s = tail.decode(enc or 'utf-8', 'ignore')
            except Exception:
                continue
            hits.setdefault(k, []).append((os.path.getmtime(p), tag, os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(p)))), s))

if not hits:
    print('=> 没找到队长版的本地数据键。说明这台电脑的浏览器里没有队长版数据（可能是在别的浏览器/无痕窗口加的）')
    sys.exit(0)

for k in KEYS:
    if k not in hits:
        continue
    for mt, tag, prof, s in hits[k]:
        print('\n' + '=' * 70)
        print('键 %s   [%s/%s]   %s' % (k, prof, tag, __import__('datetime').datetime.fromtimestamp(mt)))
        if k == 'mt_token' or 'token' in k:
            print('  （令牌内容不打印）')
            continue
        # 提取 JSON 主体
        j = s.find('{')
        if j >= 0:
            depth = 0
            for n in range(j, min(len(s), j + 300000)):
                if s[n] == '{':
                    depth += 1
                elif s[n] == '}':
                    depth -= 1
                    if depth == 0:
                        blob = s[j:n + 1]
                        break
            else:
                blob = s[j:j + 200000]
        else:
            blob = s[:4000]
        try:
            o = json.loads(blob)
        except Exception as e:
            print('  （JSON 解析失败：%s，下面给原始片段）' % e)
            print('  ' + blob[:1200].replace('\n', ' '))
            continue
        if k == 'mt_ov_local_v1':
            nm = o.get('newMembers') or []
            me = o.get('memberEdits') or {}
            hr = o.get('hiddenResults') or []
            mc = o.get('matches') or []
            print('  newMembers 新增队员 = %d 人' % len(nm))
            for m in nm:
                print('     · %s / %s / %s / %s / 身份=%s / uid=%s' % (
                    m.get('name'), m.get('sex'), m.get('college'), m.get('grade'),
                    (m.get('level') or '(空)'), m.get('uid')))
            print('  memberEdits 修改过的老队员 = %d 人' % len(me))
            for uid, info in list(me.items())[:40]:
                print('     · %s -> %s' % (uid, json.dumps(info, ensure_ascii=False)))
            print('  matches 比赛 = %d 场' % len(mc))
            print('  hiddenResults 隐藏成绩 = %d 条' % len(hr))
            print('  其它键：%s' % ', '.join(sorted(o.keys())))
        elif k == 'mt_results_v1':
            r = o.get('results') if isinstance(o, dict) else o
            print('  本机成绩草稿 = %s 条' % (len(r) if hasattr(r, '__len__') else '?'))
            if isinstance(o, dict):
                print('  键：%s' % ', '.join(sorted(o.keys())))
                for kk in o:
                    v = o[kk]
                    if isinstance(v, list):
                        print('     %s: %d 条' % (kk, len(v)))
                    elif isinstance(v, dict):
                        print('     %s: %d 项' % (kk, len(v)))
                    else:
                        print('     %s = %s' % (kk, str(v)[:80]))
        else:
            print('  ' + json.dumps(o, ensure_ascii=False)[:1500])
