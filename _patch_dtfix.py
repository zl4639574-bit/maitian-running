# -*- coding: utf-8 -*-
"""修「导入修正表」3 个 bug：日期比较层级、身份认不出就不动、云端自由成绩支持修改/删除"""
import io

p = "assets/app.js"
s = io.open(p, encoding="utf-8", newline="").read().replace("\r\n", "\n")
orig = len(s)

# ── ① 自由成绩支持"隐藏"（云端发布的也能改/删）────────────────────────────
old = r"""    results: (c.results || []).concat(l.results || []),"""
new = r"""    results: (function () {
      const hid = new Set(c.hiddenResults || []);
      return (c.results || []).concat(l.results || [])
        .filter(r => !hid.has(r.uid || (r.name + '|' + r.sec)));
    })(),"""
assert s.count(old) == 1, "① ov() results"
s = s.replace(old, new)

old = r"""      results: (cloud.results || []).concat(l.results || []),"""
new = r"""      results: (function () {
        const hid = new Set((cloud.hiddenResults || []).concat(l.hiddenResults || []));
        return (cloud.results || []).concat(l.results || [])
          .filter(r => !hid.has(r.uid || (r.name + '|' + r.sec)));
      })(),
      hiddenResults: (cloud.hiddenResults || []).concat(l.hiddenResults || []),"""
assert s.count(old) == 1, "① pushToGitHub results"
s = s.replace(old, new)

# ── ② 身份：认不出来的值（如「队员」）保持原样，不当成"改成空" ───────────────
old = r"""  const normLevel = v => {
    const t = String(v == null ? '' : v).trim();
    if (!t || t === '未分级' || t === '-' || t === '无' || t === '否' || t === '0') return [];
    return t.split(/[,，、+/]/).map(x => x.trim()).filter(x => x === '正式' || x === '预备');
  };"""
new = r"""  // 返回 [] = 明确"不进公开名册"；返回 null = 这个值看不懂（例如「队员」），保持原样别动
  const normLevel = v => {
    const t = String(v == null ? '' : v).trim();
    if (!t || t === '未分级' || t === '-' || t === '无' || t === '否' || t === '0') return [];
    const hit = t.split(/[,，、+/]/).map(x => x.trim()).filter(x => x === '正式' || x === '预备');
    return hit.length ? hit : null;
  };"""
assert s.count(old) == 1, "② normLevel"
s = s.replace(old, new)

old = r"""      const diff = ['sex', 'college', 'major', 'grade'].filter(f => (info[f] || '') !== (cur[f] || ''));
      if (!sameLv(cur.level, info.level)) diff.push('身份');
      if (diff.length) plan.memberFix.push({ name: name, info: info, diff: diff, isNew: !baseByName[name], uid: cur.uid || '' });"""
new = r"""      const diff = ['sex', 'college', 'major', 'grade'].filter(f => (info[f] || '') !== (cur[f] || ''));
      if (info.level && !sameLv(cur.level, info.level)) diff.push('身份');
      if (info.level === null) delete info.level;          // 看不懂就不改身份
      if (diff.length) plan.memberFix.push({ name: name, info: info, diff: diff, isNew: !baseByName[name], uid: cur.uid || '' });"""
assert s.count(old) == 1, "② 身份判断"
s = s.replace(old, new)

# 新增队员时也要处理 null
old = r"""  p.addMember.forEach(x => {
    l.newMembers.push(Object.assign({ uid: nmUid(), name: x.name, addedAt: new Date().toISOString().slice(0, 10) }, x.info));
  });"""
new = r"""  p.addMember.forEach(x => {
    const info = Object.assign({}, x.info);
    if (!info.level) info.level = ['正式'];
    l.newMembers.push(Object.assign({ uid: nmUid(), name: x.name, addedAt: new Date().toISOString().slice(0, 10) }, info));
  });"""
assert s.count(old) == 1, "② addMember level"
s = s.replace(old, new)

# ── ③ 日期/备注比较：跟"导出时那一格的值"比，而不是跟记录里的原始字段比 ──────
old = r"""      if (key.indexOf('comp:') === 0) {
        const parts = key.slice(5).split('|');
        const cid = parts[0], oldSec = Number(parts[parts.length - 1]);
        const orig = all.find(r => r._cid === cid && r.name === name && Math.abs(Number(r.sec) - oldSec) < 0.05);
        if (!orig) { plan.skip.push('找不到：' + name + ' ' + (ev || '') + ' ' + (rawRes || '')); return; }
        if (isDel) {
          plan.recHide.push({ hideKey: cid + '|' + name + '|' + oldSec,
            desc: name + ' ' + (orig.event || '') + ' ' + (orig.fmt || fmtSec(orig.sec)) });
          return;
        }
        if (!sec) { plan.skip.push(name + ' 的成绩看不懂：' + rawRes); return; }
        if (Math.abs(sec - oldSec) > 0.05 || (ev && ev !== orig.event) || date !== (orig.date || '')
            || note !== (orig.note || orig.rank || '')) {"""
new = r"""      if (key.indexOf('comp:') === 0) {
        const parts = key.slice(5).split('|');
        const cid = parts[0], oldSec = Number(parts[parts.length - 1]);
        const orig = all.find(r => r._cid === cid && r.name === name && Math.abs(Number(r.sec) - oldSec) < 0.05);
        if (!orig) { plan.skip.push('找不到：' + name + ' ' + (ev || '') + ' ' + (rawRes || '')); return; }
        if (isDel) {
          plan.recHide.push({ hideKey: cid + '|' + name + '|' + oldSec,
            desc: name + ' ' + (orig.event || '') + ' ' + (orig.fmt || fmtSec(orig.sec)) });
          return;
        }
        if (!sec) { plan.skip.push(name + ' 的成绩看不懂：' + rawRes); return; }
        const comp = comps.filter(c => c.id === cid)[0] || {};
        const expDate = orig.date || comp.date || '';            // 导出时写进"日期"列的值
        const expNote = orig.rank || orig.note || '';            // 导出时写进"名次/备注"列的值
        if (Math.abs(sec - oldSec) > 0.05 || (ev && ev !== orig.event) || date !== expDate || note !== expNote) {"""
assert s.count(old) == 1, "③ 日期比较"
s = s.replace(old, new)

# 修正记录的日期/备注也按"导出格"的语义保存
old = r"""            rec: { name: name, event: ev || orig.event, raw: rawRes, sec: sec, fmt: fmtSec(sec),
                   sex: orig.sex || '', college: orig.college || '', date: date || orig.date || '',
                   note: note || '', keep: true },"""
new = r"""            rec: { name: name, event: ev || orig.event, raw: rawRes, sec: sec, fmt: fmtSec(sec),
                   sex: orig.sex || '', college: orig.college || '',
                   date: (date && date !== expDate) ? date : (orig.date || ''),
                   note: (note && note !== expNote) ? note : (orig.note || orig.rank || ''), keep: true },"""
assert s.count(old) == 1, "③ 修正记录字段"
s = s.replace(old, new)

# ── ④ 自由成绩：能在云端发布过的那一批里找（不再只查本机）──────────────────
old = r"""      if (key.indexOf('res:') === 0) {
        const uid = key.slice(4);
        const cur = (ovLocal().results || []).find(r => (r.uid || (r.name + '|' + r.sec)) === uid);
        if (!cur) { plan.skip.push('找不到自由成绩：' + name); return; }
        if (isDel) { plan.recDel.push({ uid: uid, desc: name + ' ' + (cur.event || '') + ' ' + (cur.fmt || fmtSec(cur.sec)) }); return; }"""
new = r"""      if (key.indexOf('res:') === 0) {
        const uid = key.slice(4);
        const allRes = (ov().results || []);
        const cur = allRes.find(r => (r.uid || (r.name + '|' + r.sec)) === uid);
        if (!cur) { plan.skip.push('找不到自由成绩：' + name); return; }
        const inLocal = (ovLocal().results || []).some(r => (r.uid || (r.name + '|' + r.sec)) === uid);
        if (!inLocal) cur._cloud = true;            // 云端发布过的：改/删都靠 hiddenResults
        if (isDel) { plan.recDel.push({ uid: uid, desc: name + ' ' + (cur.event || '') + ' ' + (cur.fmt || fmtSec(cur.sec)), cloud: !inLocal }); return; }"""
assert s.count(old) == 1, "④ 自由成绩查找"
s = s.replace(old, new)

old = r"""  p.recDel.forEach(x => { l.results = (l.results || []).filter(r => (r.uid || (r.name + '|' + r.sec)) !== x.uid); });
  p.recEdit.forEach(x => {
    (l.results = l.results || []).forEach(r => { if ((r.uid || (r.name + '|' + r.sec)) === x.uid) Object.assign(r, x.rec); });
  });"""
new = r"""  p.recDel.forEach(x => {
    l.results = (l.results || []).filter(r => (r.uid || (r.name + '|' + r.sec)) !== x.uid);
    if (x.cloud) l.hiddenResults = (l.hiddenResults || []).concat([x.uid]);      // 云端那条也要屏蔽
  });
  p.recEdit.forEach(x => {
    let hit = (l.results = l.results || []);
    let found = false;
    hit.forEach(r => { if ((r.uid || (r.name + '|' + r.sec)) === x.uid) { Object.assign(r, x.rec); found = true; } });
    if (!found) {                                    // 改的是云端那条 → 屏蔽旧的 + 本机加新的
      l.hiddenResults = (l.hiddenResults || []).concat([x.uid]);
      l.results.push(x.rec);
    }
  });"""
assert s.count(old) == 1, "④ 自由成绩应用"
s = s.replace(old, new)

io.open(p, "w", encoding="utf-8", newline="\r\n").write(s)
print("修正补丁完成: %d -> %d 字符" % (orig, len(s)))
