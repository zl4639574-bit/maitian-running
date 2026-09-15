# -*- coding: utf-8 -*-
"""修自检抓到的两个 bug：
   ① fillParseText 没有表头时也要能按位置认列（姓名,性别,学院,专业,年级）
   ② 完善信息表用 data-fme/data-fmuid，保存时优先级高于下方名册列表（不然会被旧值覆盖）
"""
import io, os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'app.js')
raw = io.open(P, 'rb').read().decode('utf-8')
s = raw.replace('\r\n', '\n')
done = []


def rep(old, new, label, cnt=1):
    global s
    n = s.count(old)
    assert n == cnt, '✗ %s：期望 %d 处，实际 %d 处' % (label, cnt, n)
    s = s.replace(old, new)
    done.append(label)


# ── ① 默认按位置认列 ──
rep("""  const rows = [], skip = [];
  const dir = { name: 0 };
  String(txt || '').split(/\\r?\\n/).forEach((line, i) => {
    const t = line.trim();
    if (!t) return;
    const p = t.split(/[\\t,，、]+/).map(x => x.trim());
    if (i === 0 && /姓名|名字/.test(p[0] || '')) {""",
    """  const rows = [], skip = [];
  // 默认按位置认列：姓名,性别,学院,专业,年级；第一行是表头时再按表头认列
  const dir = { name: 0, sex: 1, college: 2, major: 3, grade: 4 };
  String(txt || '').split(/\\r?\\n/).forEach((line, i) => {
    const t = line.trim();
    if (!t) return;
    const p = t.split(/[\\t,，、]+/).map(x => x.trim());
    if (i === 0 && /姓名|名字/.test(p[0] || '')) {""",
    '① 批量补全按位置认列（无表头也能用）')

# ── ② 完善信息表换独立属性 ──
rep("""        const k = isNewMember(m) ? ('data-muid="' + esc(m.uid || m.name) + '"') : ('data-me="' + esc(m.name) + '"');""",
    """        const k = isNewMember(m) ? ('data-fmuid="' + esc(m.uid || m.name) + '"') : ('data-fme="' + esc(m.name) + '"');""",
    '② 完善信息表用 data-fme / data-fmuid')

# ── ③ 保存时「完善信息表」优先（只覆盖非空值）──
rep("""  saveLocalOv();
  return Object.keys(byName).length + Object.keys(byUid).length;
}""",
    """  // 「完善队员信息」表的值优先级更高：同一个人的两个编辑区同时存在时，以补全表填的为准
  // （只覆盖非空值，避免补全表里空着的一项把列表里已有的内容清掉）
  const fByName = {};
  $$('[data-fme]').forEach(el => {
    const n = el.dataset.fme, f = el.dataset.mf;
    fByName[n] = fByName[n] || {};
    fByName[n][f] = el.value;
  });
  Object.entries(fByName).forEach(([n, f]) => {
    const prev = edits[n] || (edits[n] = {});
    FILL_FIELDS.forEach(k => {
      if (f[k] !== undefined && String(f[k]).trim() !== '') prev[k] = String(f[k]).trim();
    });
  });
  const fByUid = {};
  $$('[data-fmuid]').forEach(el => {
    const u = el.dataset.fmuid, f = el.dataset.mf;
    fByUid[u] = fByUid[u] || {};
    fByUid[u][f] = el.value;
  });
  Object.entries(fByUid).forEach(([u, f]) => {
    const nm = (l.newMembers || []).find(m => (m.uid || m.name) === u);
    if (!nm) return;
    FILL_FIELDS.forEach(k => {
      if (f[k] !== undefined && String(f[k]).trim() !== '') nm[k] = String(f[k]).trim();
    });
  });
  saveLocalOv();
  return Object.keys(byName).length + Object.keys(byUid).length;
}""",
    '③ 保存时完善信息表优先')

io.open(P, 'wb').write(s.replace('\n', '\r\n').encode('utf-8'))
print('\n'.join('  ' + d for d in done))
