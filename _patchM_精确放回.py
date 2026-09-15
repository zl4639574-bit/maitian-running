# -*- coding: utf-8 -*-
"""修正版：把"自动放回名册"改精确 + 补助手函数"""
import io, os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'app.js')
s = io.open(P, encoding='utf-8', newline='').read().replace('\r\n', '\n')
n = 0

# 1) 在 unhideMember 前插入 effLevel / isVisibleLevel，并把注释改准
old1 = """/** 把一个人从「已移除」里放回来（身份被设成正式/预备 = 明确想让他显示）
    ⚠️ 只写本机 shown；同步时会把 hidden 里对应名字扣掉（见 pushToGitHub 的合并），线上才会真的显示 */
function unhideMember(name) {"""
new1 = """/** 这个人此刻的有效身份（改过的优先，没改过看原始 / 队长新增） */
function effLevel(name) {
  const n = String(name || '').trim();
  const e = (ov().memberEdits || {})[n] || {};
  if (e.level !== undefined && e.level !== null) return e.level || [];
  const nw = (ov().newMembers || []).filter(m => m.name === n)[0];
  if (nw && nw.level) return nw.level;
  const base = (BASE.roster || []).filter(m => m.name === n)[0];
  return (base && base.level) || [];
}
/** 这个身份会不会显示在公开名册里（正式/预备 = 会） */
function isVisibleLevel(lv) {
  const a = lv || [];
  return a.indexOf('正式') >= 0 || a.indexOf('预备') >= 0;
}

/** 把一个人从「已移除」里放回来（只在"身份从不可见变成可见"时自动调）
    ⚠️ 只写本机 shown；同步时会把 hidden 里对应名字扣掉（见 pushToGitHub 的合并），线上才会真的显示 */
function unhideMember(name) {"""
assert old1 in s, '1'
s = s.replace(old1, new1, 1); n += 1

# 2) saveRosterEdits：先记下"本来是否可见"
old2 = """  const byName = {};
  $$('[data-me]').forEach(el => {
    const n = el.dataset.me, f = el.dataset.mf;
    byName[n] = byName[n] || {};
    byName[n][f] = el.value;
  });"""
new2 = old2 + """
  const beforeVis = {};                                  // 改之前谁在公开名册里（判断"是不是新变可见"）
  Object.keys(byName).forEach(n2 => { beforeVis[n2] = isVisibleLevel(effLevel(n2)); });"""
assert old2 in s, '2'
s = s.replace(old2, new2, 1); n += 1

# 3) 只给"新变可见"的人解除移除
old3 = """  // 身份被改成正式/预备 = 明确想让他显示：顺手从「已移除」名单里放回来（不然改身份也白改）
  let back = 0;
  Object.entries(byName).forEach(([n]) => {
    const lv = (edits[n] || {}).level || [];
    if (lv.indexOf('正式') >= 0 || lv.indexOf('预备') >= 0) { if (unhideMember(n)) back++; }
  });
  (l.newMembers || []).forEach(m => {
    const lv = m.level || [];
    if (lv.indexOf('正式') >= 0 || lv.indexOf('预备') >= 0) { if (unhideMember(m.name)) back++; }
  });"""
new3 = """  // 身份"从不可见变成可见"（例如原始身份「队员」的人被改成「正式」）→ 顺手从「已移除」放回来，
  // 不然改了身份他还是不显示（这就是"名册同步一直有问题"的一半原因）
  let back = 0;
  Object.entries(byName).forEach(([n2]) => {
    const now = isVisibleLevel((edits[n2] || {}).level);
    if (now && !beforeVis[n2] && unhideMember(n2)) back++;
  });"""
assert old3 in s, '3'
s = s.replace(old3, new3, 1); n += 1

# 4) 资料导入：只处理"本来不在名册里、现在明确设成正式/预备"的
old4 = """    if (lvIn.indexOf('正式') >= 0 || lvIn.indexOf('预备') >= 0) {
      if (unhideMember(doc.name)) levelNote += '、已把他从「已移除」里放回名册';
    }"""
new4 = """    if (isVisibleLevel(lvIn) && !wasInRoster) {        // 本来不在公开名册里 → 这次明确设成正式/预备了
      if (unhideMember(doc.name)) levelNote += '、已把他从「已移除」里放回名册';
    }"""
assert old4 in s, '4'
s = s.replace(old4, new4, 1); n += 1

io.open(P, 'w', encoding='utf-8', newline='').write(s.replace('\n', '\r\n'))
print('改了 %d 处' % n)
