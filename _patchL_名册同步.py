# -*- coding: utf-8 -*-
"""修名册同步的两个真 bug：
   A) 身份改成正式/预备后，如果这个人在「已移除」名单里（overrides.hidden），他照样不显示
      → 改身份/导入资料时自动把他从「已移除」里放回来（写进本机 shown）
   B) 同步的合并结果里 hidden 只做并集、从来没被本机 shown 扣掉
      → 点「↺ 恢复显示」后同步，线上依然把他藏起来（公开页看不到）
"""
import io, os, sys

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'app.js')
s = io.open(P, encoding='utf-8', newline='').read().replace('\r\n', '\n')
n_changed = 0

# ── 1) 加 unhideMember 助手 + rosterStatus 带出"被移除"状态 + 提示文案 ──
old = """function rosterStatus(name) {
  const n = String(name || '').trim();
  const base = (BASE.roster || []).filter(m => m.name === n)[0];
  const nw = (ov().newMembers || []).filter(m => m.name === n)[0];
  return { inRoster: rosterList().some(m => m.name === n),
    inBase: !!base, baseLevel: base ? (base.level || []) : [], isNew: !!nw };
}"""
new = """function rosterStatus(name) {
  const n = String(name || '').trim();
  const base = (BASE.roster || []).filter(m => m.name === n)[0];
  const nw = (ov().newMembers || []).filter(m => m.name === n)[0];
  const o = ov();
  return { inRoster: rosterList().some(m => m.name === n),
    inBase: !!base, baseLevel: base ? (base.level || []) : [], isNew: !!nw,
    removed: (o.hidden || []).indexOf(n) >= 0 && (o.shown || []).indexOf(n) < 0 };   // 在「已移除」名单里
}

/** 把一个人从「已移除」里放回来（身份被设成正式/预备 = 明确想让他显示）
    ⚠️ 只写本机 shown；同步时会把 hidden 里对应名字扣掉（见 pushToGitHub 的合并），线上才会真的显示 */
function unhideMember(name) {
  const n = String(name || '').trim();
  if (!n) return false;
  const l = ovLocal();
  if ((l.shown || []).indexOf(n) >= 0) return false;
  const isHidden = (ov().hidden || []).indexOf(n) >= 0 && (ov().shown || []).indexOf(n) < 0;
  if (!isHidden) return false;
  l.shown = Array.from(new Set((l.shown || []).concat([n])));
  saveLocalOv();
  return true;
}"""
assert old in s, 'rosterStatus 没找到'
s = s.replace(old, new, 1); n_changed += 1

old = """  if (s.isNew) return '他在「队长新增」里但身份不是正式/预备 —— 去「数据管理 → 队员名册」把他的身份改成「正式」';"""
new = """  if (s.isNew) return '他在「队长新增」里但身份不是正式/预备 —— 去「数据管理 → 队员名册」把他的身份改成「正式」';
  if (s.removed) return '他的身份是正式/预备，但他在「已移除」名单里（以前被移除了）—— 去「数据管理 → 队员名册」往下找「已移除」那一栏，点他的「↺ 恢复显示」，再同步一次';"""
assert old in s, 'rosterHint 没找到'
s = s.replace(old, new, 1); n_changed += 1

# ── 2) 保存名册修改时：身份是正式/预备 → 自动从「已移除」放回来 ──
old = """  saveLocalOv();
  return Object.keys(byName).length + Object.keys(byUid).length;
}"""
new = """  // 身份被改成正式/预备 = 明确想让他显示：顺手从「已移除」名单里放回来（不然改身份也白改）
  let back = 0;
  Object.entries(byName).forEach(([n]) => {
    const lv = (edits[n] || {}).level || [];
    if (lv.indexOf('正式') >= 0 || lv.indexOf('预备') >= 0) { if (unhideMember(n)) back++; }
  });
  (l.newMembers || []).forEach(m => {
    const lv = m.level || [];
    if (lv.indexOf('正式') >= 0 || lv.indexOf('预备') >= 0) { if (unhideMember(m.name)) back++; }
  });
  saveLocalOv();
  if (back) toast('已保存，并把这 ' + back + ' 位从「已移除」里放回了名册 —— 记得点「同步我的修改到线上」', 12000);
  return Object.keys(byName).length + Object.keys(byUid).length + back;
}"""
assert old in s, 'saveRosterEdits 结尾没找到'
s = s.replace(old, new, 1); n_changed += 1

# ── 3) 资料导入：写了正式/预备就顺手放回来 ──
old = """  const lvIn = normLevelOf(doc.level);
  let levelNote = '';
  if (lvIn && lvIn.length) {
    e.level = lvIn;
    levelNote = '，身份已设为「' + lvIn.join('/') + '」';
  }"""
new = """  const lvIn = normLevelOf(doc.level);
  let levelNote = '';
  if (lvIn && lvIn.length) {
    e.level = lvIn;
    levelNote = '，身份已设为「' + lvIn.join('/') + '」';
    if (lvIn.indexOf('正式') >= 0 || lvIn.indexOf('预备') >= 0) {
      if (unhideMember(doc.name)) levelNote += '、已把他从「已移除」里放回名册';
    }
  }"""
assert old in s, 'applyMemberDoc 身份段没找到'
s = s.replace(old, new, 1); n_changed += 1

# ── 4) 同步合并：hidden 要扣掉本机 shown，线上才真的显示 ──
old = """      hidden: Array.from(new Set((cloud.hidden || []).concat(l.hidden || []))),"""
new = """      // ⚠️ 必须扣掉本机「↺ 恢复显示」的人，否则恢复只在本地有效、线上永远看不见（2026-09-15 修）
      hidden: Array.from(new Set((cloud.hidden || []).concat(l.hidden || [])))
        .filter(n => (l.shown || []).indexOf(n) < 0),"""
assert old in s, '同步 hidden 那行没找到'
s = s.replace(old, new, 1); n_changed += 1

io.open(P, 'w', encoding='utf-8', newline='').write(s.replace('\n', '\r\n'))
print('改了 %d 处' % n_changed)
