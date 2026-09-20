# 统计名册身份分布（base + overrides 合并后的有效身份）
import json, re, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))

def load(name, var):
    txt = open(os.path.join(HERE, 'data', name), encoding='utf-8').read()
    i = txt.index('=')
    js = txt[i+1:].strip().rstrip(';')
    return json.loads(js)

base = load('team-data.js', 'TEAM_DATA')
ov = load('overrides.js', 'TEAM_OVERRIDES')

print('overrides keys:', list(ov.keys()))
roster = base.get('roster', [])
print('BASE.roster 人数:', len(roster))
print('BASE.roster 原始 level 分布:', collections.Counter(tuple(m.get('level') or []) for m in roster))
print('newMembers:', len(ov.get('newMembers') or []), collections.Counter(tuple(m.get('level') or []) for m in (ov.get('newMembers') or [])))
print('hidden:', ov.get('hidden'))
print('shown:', ov.get('shown'))
edits = ov.get('memberEdits') or {}
print('memberEdits 条数:', len(edits), '其中改了 level 的:', sum(1 for k,v in edits.items() if 'level' in v))

hidden = set(ov.get('hidden') or [])
shown = set(ov.get('shown') or [])
eff = collections.Counter()
rows = []
for m in roster:
    n = m.get('name')
    if n in hidden and n not in shown:
        eff['【已移除】'] += 1
        rows.append(('已移除', n, m.get('level')))
        continue
    e = edits.get(n) or {}
    lv = e['level'] if e.get('level') is not None else (m.get('level') or [])
    eff[tuple(lv) or ('(空)',)] += 1
    rows.append((lv, n, m.get('level')))
for m in (ov.get('newMembers') or []):
    n = m.get('name')
    if n in hidden and n not in shown:
        eff['【已移除·新增】'] += 1
        continue
    eff[tuple(m.get('level') or []) or ('(空)',)] += 1

print('\n== 有效身份分布 ==')
for k, v in eff.most_common():
    print(' ', k, v)
print('\n总人(名册里)：', sum(v for k, v in eff.items() if '已移除' not in str(k)))
