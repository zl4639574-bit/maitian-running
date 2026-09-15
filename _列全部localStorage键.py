# -*- coding: utf-8 -*-
"""列出 Edge 里 github.io / file:// 这两个来源下**所有** localStorage 键（不只我猜的那几个）"""
import os, io, re, json

U = os.path.expandvars(r'%LOCALAPPDATA%')
base = os.path.join(U, 'Microsoft', 'Edge', 'User Data', 'Default', 'Local Storage', 'leveldb')
files = [os.path.join(base, f) for f in os.listdir(base) if f.endswith(('.log', '.ldb'))]

def printable(s):
    return re.match(r'[\x20-\x7e\u4e00-\u9fff\-_.]{1,60}', s)

pairs = set()
for p in files:
    b = io.open(p, 'rb').read()
    for enc in ('utf-8', 'utf-16-le'):
        for org in ('https://zl4639574-bit.github.io', 'file://', 'https://haochuanpeng.github.io'):
            pat = org.encode(enc)
            s = 0
            while True:
                i = b.find(pat, s)
                if i < 0:
                    break
                s = i + len(pat)
                tail = b[i + len(pat):i + len(pat) + 240].decode(enc, 'ignore')
                m = re.match(r'[\x00-\x03]*([A-Za-z0-9_\-\.]{1,60})', tail)
                if m and m.group(1):
                    pairs.add((os.path.basename(p), org, m.group(1)))

for f, org, k in sorted(pairs):
    print('%-14s %-40s %s' % (f, org, k))
print('\n共 %d 个 (文件,来源,键)' % len(pairs))
