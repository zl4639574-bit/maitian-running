# -*- coding: utf-8 -*-
"""自愈 + 同步载荷：被「已移除」压着的"已升级身份"的人要能出来（李志宏这类）"""
import io, os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'app.js')
s = io.open(P, encoding='utf-8', newline='').read().replace('\r\n', '\n')
n = 0

# 1) 加 healRosterHidden（放在 unhideMember 之后）
old1 = """  l.shown = Array.from(new Set((l.shown || []).concat([n])));
  saveLocalOv();
  return true;
}"""
new1 = old1 + """

/** 自愈：身份已经"从不可见改成可见"（原始身份「队员」→ 正式/预备）的人，
    如果还躺在「已移除」（overrides.hidden）名单里，自动放回名册（写本机 shown）。
    ⚠️ 必须写 shown 而不是只改显示：同步时 hidden 要扣掉 shown 里的名字，线上才真的显示。
    只认"升级"这一种情况 —— 本来身份就是预备/正式、当年被刻意移出显示的那批人不动。 */
function healRosterHidden() {
  const o = ov(), l = ovLocal();
  const hid = o.hidden || [];
  if (!hid.length) return 0;
  const base = {};
  (BASE.roster || []).forEach(m => { base[m.name] = m.level || []; });
  const add = [];
  hid.forEach(n2 => {
    if ((o.shown || []).indexOf(n2) >= 0) return;
    const e = (o.memberEdits || {})[n2] || {};
    if (e.level === undefined || e.level === null) return;              // 没改过身份 → 不动
    if (isVisibleLevel(e.level) && !isVisibleLevel(base[n2])) add.push(n2);   // 升级了 → 放回来
  });
  if (!add.length) return 0;
  l.shown = Array.from(new Set((l.shown || []).concat(add)));
  saveLocalOv();
  return add.length;
}"""
assert old1 in s, '1'
s = s.replace(old1, new1, 1); n += 1

# 2) 启动时（云端数据到齐后）跑一次自愈
old2 = """  await loadCloud(false);
  await loadQueueCfg();"""
new2 = """  await loadCloud(false);
  const healed = healRosterHidden();          // 把"身份已升级但被「已移除」压着"的人放回名册
  if (healed) setTimeout(() => toast('有 ' + healed + ' 位身份已改成正式/预备的人之前被「已移除」压着，已自动放回名册 —— 点一次「同步我的修改到线上」他们就会出现在公开名册里', 16000), 1500);
  await loadQueueCfg();"""
assert old2 in s, '2'
s = s.replace(old2, new2, 1); n += 1

# 3) 同步前再跑一次（保证这次同步就把 hidden 修正掉）
old3 = """  await loadCloud(true);            // 先拉一次最新的云端数据，避免把别人刚提交的覆盖掉"""
new3 = """  await loadCloud(true);            // 先拉一次最新的云端数据，避免把别人刚提交的覆盖掉
  healRosterHidden();               // 同步前再自愈一次，保证这次就把 hidden 里的漏网的扣掉"""
assert old3 in s, '3'
s = s.replace(old3, new3, 1); n += 1

io.open(P, 'w', encoding='utf-8', newline='').write(s.replace('\n', '\r\n'))
print('改了 %d 处' % n)
