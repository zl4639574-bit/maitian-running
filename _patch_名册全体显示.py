# -*- coding: utf-8 -*-
"""名册改成「显示所有人员」（2026-09-20）
把 app.js / health-check.js 里"公开名册只显示正式/预备"的逻辑与文案，统一改成"显示所有身份，只有「已移除」才不显示"。
锚点按 LF 归一化后匹配，写回时保留原来的 CRLF。
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))

APP = [
# ---------- 1. rosterList：所有身份都进名册 ----------
("""/** 名册：只保留正式 / 预备 队员，去掉被删的，套用修改
    ⚠️ 身份必须"先套上改后的、再判断"，否则把原始身份「队员」的人改成「正式」永远不生效
    （2026-09-15 修：队员资料导入 / 队员数据表里把身份填成「正式」，公开名册却一直不出现） */""",
 """/** 名册：**所有身份的人都显示**（2026-09-20 起：不再按身份隐藏「普通 / 队员」的人，
    只把「已移除」名单里的人拿掉），并套用队长改过的资料 */"""),

("""function rosterList() {
  const o = ov();
  const hidden = new Set(o.hidden);
  const KEEP = ['正式', '预备'];
  const fromBase = (BASE.roster || [])
    .filter(m => !hidden.has(m.name))
    .map(m => {
      const e = o.memberEdits[m.name] || {};
      // 明确改过身份（含改成空 = 不进公开名册）就听改后的；从没改过才用原始身份
      const lv = (e.level === undefined || e.level === null) ? (m.level || []) : e.level;
      return Object.assign({}, m, e, { level: (lv || []).filter(l => KEEP.indexOf(l) >= 0) });
    })
    .filter(m => m.level.length);
  // 队长在「队员名册」里手动添加的新队员
  const added = (o.newMembers || [])
    .filter(m => !hidden.has(m.name))
    .filter(m => (m.level || []).some(l => l === '正式' || l === '预备'));
  return fromBase.concat(added);
}""",
 """function rosterList() {
  const o = ov();
  const hidden = new Set(o.hidden);
  const fromBase = (BASE.roster || [])
    .filter(m => !hidden.has(m.name))
    .map(m => {
      const e = o.memberEdits[m.name] || {};
      // 明确改过身份（含改成空 = 未分级）就听改后的；从没改过才用原始身份
      const lv = (e.level === undefined || e.level === null) ? (m.level || []) : e.level;
      return Object.assign({}, m, e, { level: (lv || []).slice() });
    });
  // 队长在「队员名册」里手动添加的新队员
  const added = (o.newMembers || [])
    .filter(m => !hidden.has(m.name))
    .map(m => Object.assign({}, m, { level: (m.level || []).slice() }));
  return fromBase.concat(added);
}"""),

# ---------- 2. LEVELS ----------
("""/** 身份的三档：正式 / 预备 会进公开名册；普通 = 队里的人但不进公开名册（和原始名册里的「队员」同义） */
const LEVELS = ['正式', '预备', '普通'];""",
 """/** 身份可选值：正式 / 预备 / 普通 / 队员（「普通」和原始名册里写的「队员」是一个意思）。
    2026-09-20 起身份不再决定显不显示 —— 名册显示所有人员，身份只当标签用 */
const LEVELS = ['正式', '预备', '普通', '队员'];"""),

# ---------- 3. isVisibleLevel ----------
("""/** 这个身份会不会显示在公开名册里（正式/预备 = 会） */
function isVisibleLevel(lv) {
  const a = lv || [];
  return a.indexOf('正式') >= 0 || a.indexOf('预备') >= 0;
}""",
 """/** 这个身份会不会显示在名册里
    2026-09-20 起：名册显示**所有**人员，身份不再决定显不显示（只有在「已移除」名单里才不显示），
    所以恒为 true。保留这个函数是为了别处（体检、导入提示）的调用不用改。 */
function isVisibleLevel(lv) {
  return true;
}"""),

# ---------- 4. healRosterHidden 停用 ----------
("""/** 自愈：身份已经"从不可见改成可见"（原始身份「队员」→ 正式/预备）的人，
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
}""",
 """/** 以前：身份从「队员」升级成 正式/预备 时，自动把他从「已移除」名单里放回来。
    2026-09-20 起名册显示**所有**身份的人，身份跟"显不显示"已经没关系了 → 不再自动放回：
    进了「已移除」就只有手动点「↺ 恢复显示」才回来（队长明确不想显示的人才在那儿）。
    函数保留成空壳，启动流程还在调它。 */
function healRosterHidden() { return 0; }"""),

# ---------- 5. rosterHint ----------
("""function rosterHint(name) {
  const s = rosterStatus(name);
  if (s.inRoster) return '';
  if (s.inBase) {
    return '他本来就在原始名册里，但身份是「' + ((s.baseLevel || []).join('/') || '未填') + '」，' +
      '而公开名册只显示正式/预备 —— 去「数据管理 → 队员名册」搜他的名字，把「身份」改成「正式」再点「保存名册修改」，他就出现在队员名册里了';
  }
  if (s.isNew) return '他在「队长新增」里但身份不是正式/预备 —— 去「数据管理 → 队员名册」把他的身份改成「正式」';
  if (s.removed) return '他的身份是正式/预备，但他在「已移除」名单里（以前被移除了）—— 去「数据管理 → 队员名册」往下找「已移除」那一栏，点他的「↺ 恢复显示」，再同步一次';
  return '名册里完全没有这个人 —— 用「数据管理 → 队员名册 → 批量添加队员」把他加进来（或点上面的「把他加入公开名册」）';
}""",
 """function rosterHint(name) {
  const s = rosterStatus(name);
  if (s.inRoster) return '';
  // 名册现在显示所有身份的人 → 名册里"看不到"只剩一种原因：在「已移除」名单里
  if (s.inBase || s.isNew || s.removed) {
    return '他名册里有记录，但被列在「已移除显示」名单里（以前手动移除过）—— 去「数据管理 → 队员名册」往下找' +
      '「已从名册移除」那一栏，点他的「↺ 恢复显示」，再点一次「同步我的修改到线上」';
  }
  return '名册里完全没有这个人 —— 用「数据管理 → 队员名册 → 批量添加队员」把他加进来（或点上面的「把他加入名册」）';
}"""),

# ---------- 6. 个人最好成绩榜：名册里的人都算 ----------
("""  // 个人最好成绩只统计「正式队员」；非正式的同学只在当时的比赛榜里出现
  const official = new Set(rosterList().filter(m => (m.level || []).indexOf('正式') >= 0).map(m => m.name));
  allResults().forEach(r => {
    if (!r.name || !r.sec) return;
    if (!official.has(r.name)) return;""",
 """  // 名册里的人都进最好成绩榜（2026-09-20 起不再按身份过滤）；名册外的同学（外院/客串）只在当时的比赛榜里出现
  const inRoster = new Set(rosterList().map(m => m.name));
  allResults().forEach(r => {
    if (!r.name || !r.sec) return;
    if (!inRoster.has(r.name)) return;"""),

("""  // 手工「单独添加」的个人最好成绩（同样只统计正式队员）
  ov().pbAdded.forEach(p => {
    if (!p.name || !p.sec || !official.has(p.name)) return;""",
 """  // 手工「单独添加」的个人最好成绩（同样只认名册里的人）
  ov().pbAdded.forEach(p => {
    if (!p.name || !p.sec || !inRoster.has(p.name)) return;"""),

# ---------- 7. 成绩榜口径说明 ----------
("""  <p class=\"sub sec\">上面按「一场比赛一张榜」看原始名次（含当时参赛的所有同学）；下面这一张是个人最好成绩，把所有比赛合起来、每人每项只留最快的一次，且<b>只统计正式队员</b>。</p>""",
 """  <p class=\"sub sec\">上面按「一场比赛一张榜」看原始名次（含当时参赛的所有同学）；下面这一张是个人最好成绩，把所有比赛合起来、每人每项只留最快的一次，<b>名册里的人都在里面</b>（名册外的同学只出现在上面单场榜）。</p>"""),

# ---------- 8. 队员名册页：身份 chips 自动生成 ----------
("""function renderRoster() {
  let list = rosterList();
  const colleges = Array.from(new Set(list.map(m => m.college).filter(Boolean))).sort();
  const LEVELS = [['', '全部'], ['正式', '正式队员'], ['预备', '预备队员']];

  if (state.rosterLevel) list = list.filter(m => (m.level || []).includes(state.rosterLevel));""",
 """function renderRoster() {
  const all = rosterList();
  let list = all.slice();
  const colleges = Array.from(new Set(list.map(m => m.college).filter(Boolean))).sort();
  // 身份标签按现有的人自动生成（2026-09-20 起名册显示所有身份，chips 只用来分组筛选）
  const lvKey = m => (m.level || []).join('/') || '未分级';
  const lvName = k => (k === '队员' ? '队员（普通）' : k);
  const cnt = {};
  all.forEach(m => { const k = lvKey(m); cnt[k] = (cnt[k] || 0) + 1; });
  const CHIPS = [['', '全部']].concat(Object.keys(cnt).sort((a, b) => cnt[b] - cnt[a]).map(k => [k, lvName(k)]));

  if (state.rosterLevel) list = list.filter(m => lvKey(m) === state.rosterLevel);"""),

("""  return `
  <div class=\"sec-head\"><h1>队员名册</h1>
    <span class=\"tiny\">正式队员 ${rosterList().filter(m => m.level.includes('正式')).length} 人 ·
      预备队员 ${rosterList().filter(m => m.level.includes('预备')).length} 人 · 当前筛选 ${list.length} 人</span></div>

  <div class=\"toolbar\">
    <div class=\"chips\">
      ${LEVELS.map(([v, l]) => `<div class=\"chip ${state.rosterLevel === v ? 'active' : ''}\" data-lvl=\"${esc(v)}\">${esc(l)}
        <span class=\"n\">${v ? rosterList().filter(m => m.level.includes(v)).length : rosterList().length}</span></div>`).join('')}
    </div>""",
 """  const chgTip = CHIPS.filter(c => c[0]).map(c => lvName(c[0]) + ' ' + cnt[c[0]]).join(' · ');

  return `
  <div class=\"sec-head\"><h1>队员名册</h1>
    <span class=\"tiny\">共 ${all.length} 人${chgTip ? '（' + chgTip + '）' : ''} · 当前筛选 ${list.length} 人</span></div>

  <div class=\"toolbar\">
    <div class=\"chips\">
      ${CHIPS.map(([v, l]) => `<div class=\"chip ${state.rosterLevel === v ? 'active' : ''}\" data-lvl=\"${esc(v)}\">${esc(l)}
        <span class=\"n\">${v ? cnt[v] : all.length}</span></div>`).join('')}
    </div>"""),

# ---------- 9. 数据管理：名册列表不再只列正式/预备 ----------
("""  const editList = addedList.map(m => Object.assign({}, m, { _isNew: true }))
    .concat(ros.filter(m => !hiddenSet.has(m.name)).filter(m => state.mRosterQ
      ? m.name.includes(state.mRosterQ) : (m.level || []).some(l => l === '正式' || l === '预备')).slice(0, 60)
      .map(m => Object.assign({}, m, { _isNew: false })));""",
 """  // 名册里的人全都列出来（2026-09-20 起不再只列正式/预备）：没搜索时最多列 300 个，免得一次画太多
  const editList = addedList.map(m => Object.assign({}, m, { _isNew: true }))
    .concat(ros.filter(m => !hiddenSet.has(m.name)).filter(m => state.mRosterQ
      ? m.name.includes(state.mRosterQ) : true).slice(0, 300)
      .map(m => Object.assign({}, m, { _isNew: false })));"""),

# ---------- 10. 数据管理文案 ----------
("""      （展示版显示正式/预备的 ${rosterList().length} 人）。改完记得去「同步」发布。""",
 """      （名册里显示 ${rosterList().length} 人，所有身份都显示）。改完记得去「同步」发布。"""),

("""          <select id=\"nm_level\"><option value=\"正式\">正式</option><option value=\"预备\">预备</option><option value=\"正式,预备\">正式+预备</option></select></div>""",
 """          <select id=\"nm_level\"><option value=\"正式\">正式</option><option value=\"预备\">预备</option><option value=\"普通\">普通（队员）</option><option value=\"正式,预备\">正式+预备</option></select></div>"""),

("""        也可以点右边按钮选一个 Excel / CSV 文件。身份那列填「正式」或「预备」，空着按「正式」算。""",
 """        也可以点右边按钮选一个 Excel / CSV 文件。身份那列可填「正式 / 预备 / 普通 / 队员」，空着按「正式」算
        （身份只是标注，名册里所有人都会显示）。"""),

("""        「个人最好成绩」榜（只统计正式队员）和该队员的名册卡片上；加完点「同步我的修改到线上」即上线。""",
 """        「个人最好成绩」榜（名册里的人都在里面）和该队员的名册卡片上；加完点「同步我的修改到线上」即上线。"""),

# ---------- 11. 名册行内身份下拉：保留原值 ----------
("""            <select ${k} data-mf=\"level\">
              ${[['', '未分级'], ['正式', '正式'], ['预备', '预备'], ['正式,预备', '正式+预备']].map(([v, l]) =>
                `<option value=\"${v}\" ${(e.level ? e.level.join(',') : (m.level || []).join(',')) === v ? 'selected' : ''}>${l}</option>`).join('')}
            </select>""",
 """            <select ${k} data-mf=\"level\">
              ${(() => {
                const curLv = (e.level ? e.level.join(',') : (m.level || []).join(','));
                const OPTS = [['', '未分级'], ['正式', '正式'], ['预备', '预备'], ['普通', '普通'], ['队员', '队员'], ['正式,预备', '正式+预备']];
                if (curLv && !OPTS.some(x => x[0] === curLv)) OPTS.push([curLv, curLv + '（保持原样）']);
                return OPTS.map(([v, l]) => `<option value=\"${v}\" ${curLv === v ? 'selected' : ''}>${l}</option>`).join('');
              })()}
            </select>"""),

("""      level: lvl.length ? lvl : (base.level || []).filter(x => x === '正式' || x === '预备'),""",
 """      level: lvl,                                    // 选什么存什么（「未分级」= 空数组，不会再回退到原身份）"""),

("""  return rosterList().filter(m => FILL_FIELDS.some(f => !String(m[f] || '').trim()));""",
 """  return rosterList().filter(m => FILL_FIELDS.some(f => !String(m[f] || '').trim()));"""),

# ---------- 12. 收集表导入提示 ----------
("""  const hiddenN = q.docs.filter(d => !stOf(d).inRoster && (stOf(d).inBase || stOf(d).isNew)).length;""",
 """  const removedN = q.docs.filter(d => !stOf(d).inRoster && (stOf(d).inBase || stOf(d).isNew)).length;"""),

("""      其中 <b>${inRosterN}</b> 位已经在公开名册里（只更新资料）、
      <b>${brandNewN}</b> 位名册里没有（导入后作为新队员加入，身份按表里的「身份」列，没写就按「正式」）${hiddenN ? '、<b>' + hiddenN + '</b> 位本来就在原始名册里但身份不是正式/预备 —— 光导入资料<b>不会</b>让他出现在名册里，要去「数据管理 → 队员名册」把身份改成「正式」' : ''}。""",
 """      其中 <b>${inRosterN}</b> 位已经在名册里（只更新资料）、
      <b>${brandNewN}</b> 位名册里没有（导入后作为新队员加入，身份按表里的「身份」列，没写就按「正式」）${removedN ? '、<b>' + removedN + '</b> 位被列在「已移除显示」名单里 —— 资料和成绩会存好，但要显示得去「数据管理 → 队员名册」点他的「↺ 恢复显示」' : ''}。"""),

("""            <td>${mem.has(d.name) ? '<span class=\"tagbadge green\">在</span>'
              : (stOf(d).inBase || stOf(d).isNew)
                ? '<span class=\"tagbadge\">原始身份「' + esc(((stOf(d).baseLevel || []).join('/') || '未填')) + '」→ 要改身份才显示</span>'
                : '<span class=\"tagbadge\">新增</span>'}</td></tr>`;""",
 """            <td>${mem.has(d.name) ? '<span class=\"tagbadge green\">在</span>'
              : (stOf(d).inBase || stOf(d).isNew)
                ? '<span class=\"tagbadge\">在「已移除」名单里 → 要 ↺ 恢复显示</span>'
                : '<span class=\"tagbadge\">新增</span>'}</td></tr>`;"""),

("""    let updated = 0, pbs = 0, joined = 0; const stillHidden = [];
    for (const d of q.docs) {
      const st = rosterStatus(d.name);
      const lvS = normLevelOf(d.level);
      const lvArr = (lvS && lvS.length) ? lvS : ['正式'];       // 收集表里没写身份 → 按正式
      const r = await applyMemberDoc(d);
      if (!r) continue;
      pbs += r.pbs || 0;
      if (st.inRoster || rosterStatus(d.name).inRoster) updated++;   // 表里写了「正式/预备」的，导入后就进名册了
      else if (!st.inBase && !st.isNew) {          // 名册里完全没有 → 真把他加进名册（不然\"新增\"只是嘴上说说）
        addNewMemberSilently(d.name, { sex: d.sex, college: d.college, major: d.major,
          grade: d.grade, level: lvArr, note: '收集表导入' });
        joined++;
      } else stillHidden.push(d.name);             // 身份写着「普通」（或没定）：不进公开名册
    }
    docSheetQueue = null;
    const tail = stillHidden.length
      ? ' ⚠️ ' + stillHidden.slice(0, 5).join('、') + (stillHidden.length > 5 ? ' 等 ' + stillHidden.length + ' 位' : '')
        + ' 本来就在原始名册里、身份不是正式/预备，所以队员名册里还看不到他（他们的资料/成绩已经存好了）。' +
        '去「数据管理 → 队员名册」搜名字，把「身份」改成「正式」就出现了。'
      : '';""",
 """    let updated = 0, pbs = 0, joined = 0; const stillRemoved = [];
    for (const d of q.docs) {
      const st = rosterStatus(d.name);
      const lvS = normLevelOf(d.level);
      const lvArr = (lvS && lvS.length) ? lvS : ['正式'];       // 收集表里没写身份 → 按正式
      const r = await applyMemberDoc(d);
      if (!r) continue;
      pbs += r.pbs || 0;
      if (st.inRoster || rosterStatus(d.name).inRoster) updated++;   // 已经在名册里 → 只更新资料
      else if (!st.inBase && !st.isNew) {          // 名册里完全没有 → 真把他加进名册（不然\"新增\"只是嘴上说说）
        addNewMemberSilently(d.name, { sex: d.sex, college: d.college, major: d.major,
          grade: d.grade, level: lvArr, note: '收集表导入' });
        joined++;
      } else if (st.removed) stillRemoved.push(d.name);   // 在「已移除」名单里：资料存好，但要 ↺ 恢复显示才出现在名册
    }
    docSheetQueue = null;
    const tail = stillRemoved.length
      ? ' ⚠️ ' + stillRemoved.slice(0, 5).join('、') + (stillRemoved.length > 5 ? ' 等 ' + stillRemoved.length + ' 位' : '')
        + ' 被列在「已移除显示」名单里，所以名册里还看不到他（他们的资料/成绩已经存好了）。' +
        '去「数据管理 → 队员名册」下面「已从名册移除」那一栏点他的「↺ 恢复显示」。'
      : '';"""),

# ---------- 13. 单份资料预览 ----------
("""  const badge = st.inRoster ? '<span class=\"tagbadge green\">在名册里</span>'
    : (st.inBase || st.isNew)
      ? '<span class=\"tagbadge\">原始名册里有他（身份「' + esc((st.baseLevel || []).join('/') || '未填') + '」）→ 公开名册里还看不到</span>'
      : '<span class=\"tagbadge\">名册里没有 → 导入后新增一位</span>';""",
 """  const badge = st.inRoster ? '<span class=\"tagbadge green\">在名册里</span>'
    : (st.inBase || st.isNew)
      ? '<span class=\"tagbadge\">名册里有他，但在「已移除」名单里 → 要 ↺ 恢复显示才出现</span>'
      : '<span class=\"tagbadge\">名册里没有 → 导入后新增一位</span>';"""),

("""  const lvTxt = (lvDoc && lvDoc.length)
    ? esc(lvDoc.join('/')) + ((lvDoc.indexOf('正式') >= 0 || lvDoc.indexOf('预备') >= 0) ? '（会进公开名册）' : '（不进公开名册）')
    : (d.doc.level ? esc(String(d.doc.level)) + '（看不懂 → 不改身份）' : '（没填 → 身份不动）');""",
 """  const lvTxt = (lvDoc && lvDoc.length)
    ? esc(lvDoc.join('/'))
    : (d.doc.level ? esc(String(d.doc.level)) + '（看不懂 → 不改身份）' : '（没填 → 身份不动）');"""),

("""      ${st.inRoster ? '' : '<button class=\"btn ghost sm\" id=\"btnDocAddRoster\">把他加入公开名册（身份=正式）</button>'}""",
 """      ${st.inRoster ? '' : '<button class=\"btn ghost sm\" id=\"btnDocAddRoster\">把他加入名册（身份=正式）</button>'}"""),

("""    toast('已把「' + d.doc.name + '」加进公开名册（身份：正式）—— 记得点「同步我的修改到线上」', 11000);""",
 """    toast('已把「' + d.doc.name + '」加进名册（身份：正式）—— 记得点「同步我的修改到线上」', 11000);"""),

# ---------- 14. 单独添加最好成绩的确认提示 ----------
("""    if (known && !inPbBoard && !confirm('「' + name + '」在名册里，但身份不是「正式」。\\n\\n' +
        '个人最好成绩榜只统计正式队员，所以这条成绩不会出现在榜上（名册卡片上也看不到）。\\n\\n仍然记下这条吗？')) return;""",
 """    if (known && !inPbBoard && !confirm('「' + name + '」现在不在名册里（多半被列在「已移除显示」名单里）。\\n\\n' +
        '他不在名册，所以这条成绩不会出现在最好成绩榜上。\\n\\n仍然记下这条吗？')) return;"""),

# ---------- 15. 导出 Excel 说明页 ----------
("""    ['· 可改：性别 / 学院 / 专业 / 年级 / 身份（身份填 正式 / 预备 / 普通；正式、预备 会显示在公开名册里，普通 = 队里的人但不进公开名册；留空 = 不进公开名册）'],""",
 """    ['· 可改：性别 / 学院 / 专业 / 年级 / 身份（身份填 正式 / 预备 / 普通 / 队员，只是标注，名册里所有人都会显示；留空 = 显示成「未分级」）'],"""),

("""    ['· 个人最好成绩只统计正式队员；每场比赛的榜包含当时参赛的所有同学'],""",
 """    ['· 个人最好成绩包含名册里的所有人；每场比赛的榜包含当时参赛的所有同学（含名册外的）'],"""),

# ---------- 16. 添加新队员时的重名提示 ----------
("""    const base = (BASE.roster || []).find(m => m.name === name);
    const vis = base && (base.level || []).some(x => x === '正式' || x === '预备');
    const dupNew = l.newMembers.some(m => m.name === name);
    if (base || dupNew) {
      const box = $('#nmAddBox');
      const why = base
        ? (vis
            ? '「' + name + '」已经在名册里了（' + esc(base.college || '未填学院') + '，身份 ' + esc((base.level || []).join('/') || '未分级') + '）。'
            : '「' + name + '」<b>在原始名册里，但身份是「' + esc((base.level || []).join('/') || '未分级') + '」</b>，'
              + '而展示版只显示「正式 / 预备」，所以他没出现在公开名册里 —— 不是没录进来，是身份没定。')
        : '你已经加过一个叫「' + name + '」的人了（同名可以并存，确认不是同一个人就继续）。';
      if (box) {
        box.innerHTML = '<div class=\"notice\" style=\"margin-top:12px\">' + why
          + ((base && !vis) ? '<br><br>👉 想让他出现在公开名册：点「搜出来改他的身份」，把那个人的「身份」改成 正式 或 预备，'
                             + '再点「保存名册修改」（不用新加一个人，也不用同步两次）。' : '')
          + '<div class=\"chips\" style=\"margin-top:10px\">'
          + ((base && !vis) ? '<button class=\"btn sm\" id=\"btnNmFindIt\">搜出来改他的身份</button>' : '')
          + '<button class=\"btn ghost sm\" id=\"btnNmForce\">是另一个人，仍然添加</button></div></div>';
        const b1 = $('#btnNmFindIt'), b2 = $('#btnNmForce');
        if (b1) b1.onclick = () => { state.mRosterQ = name; render(); };
        if (b2) b2.onclick = () => { am.dataset.force = '1'; am.click(); };
      }""",
 """    const base = (BASE.roster || []).find(m => m.name === name);
    const inList = rosterList().some(m => m.name === name);   // 名册显示所有身份，只有在「已移除」里才不在
    const dupNew = l.newMembers.some(m => m.name === name);
    if (base || dupNew) {
      const box = $('#nmAddBox');
      const why = base
        ? (inList
            ? '「' + name + '」已经在名册里了（' + esc(base.college || '未填学院') + '，身份 ' + esc((base.level || []).join('/') || '未分级') + '）。'
            : '「' + name + '」名册里有，但被列在「已移除显示」名单里 → 往下找「已从名册移除」那一栏，'
              + '点他的「↺ 恢复显示」就回来了（不用重新添加一个人）。')
        : '你已经加过一个叫「' + name + '」的人了（同名可以并存，确认不是同一个人就继续）。';
      if (box) {
        box.innerHTML = '<div class=\"notice\" style=\"margin-top:12px\">' + why
          + '<div class=\"chips\" style=\"margin-top:10px\">'
          + '<button class=\"btn ghost sm\" id=\"btnNmForce\">是另一个人，仍然添加</button></div></div>';
        const b2 = $('#btnNmForce');
        if (b2) b2.onclick = () => { am.dataset.force = '1'; am.click(); };
      }"""),

# ---------- 17. 新增队员默认身份注释 ----------
("""      // 新增队员没填身份 → 默认「正式」；不然会被加进去却不出现在公开名册里""",
 """      // 新增队员没填身份 → 默认「正式」（身份只是标注，不影响显不显示）"""),
]

HEALTH = [
("""  function audit() {
    var cnt = scoresOf();
    var hiddenSet = new Set(ov().hidden || []);
    var noOff = [], isRemoved = [];
    Object.keys(cnt).forEach(function (n) {
      var lv = effLevel(n) || [];
      var official = lv.indexOf('正式') >= 0;       // 成绩榜只认「正式」
      if (hiddenSet.has(n)) { isRemoved.push({ name: n, lv: lv, official: official }); return; }
      if (!official) noOff.push({ name: n, lv: lv, vis: isVisibleLevel(lv) });
    });""",
 """  function audit() {
    var cnt = scoresOf();
    var hiddenSet = new Set(ov().hidden || []);
    // 2026-09-20 起：名册显示所有身份，成绩榜也认名册里的所有人
    // → 「上不了榜」只可能是因为他压根不在名册里（名册外的同学只进单场榜）
    var rosterSet = {};
    try { (rosterList() || []).forEach(function (m) { rosterSet[m.name] = 1; }); } catch (e) {}
    var noOff = [], isRemoved = [];
    Object.keys(cnt).forEach(function (n) {
      var lv = effLevel(n) || [];
      if (hiddenSet.has(n)) { isRemoved.push({ name: n, lv: lv }); return; }
      if (!rosterSet[n]) noOff.push({ name: n, lv: lv, vis: isVisibleLevel(lv) });
    });"""),

("""    h.push('<div>' + ICON(a.noOff.length) + ' 有成绩却<b>上不了榜</b>的人：<b style=\"color:' +
      (a.noOff.length ? 'var(--wheat)' : 'var(--green)') + '\">' + a.noOff.length + '</b> 人' +
      (a.noOff.length ? ' —— 身份不到「正式」，成绩榜一条都不显示' + link('noOff', '看名单') : '') + '</div>');""",
 """    h.push('<div>' + ICON(a.noOff.length) + ' 有成绩却<b>不在名册里</b>的人：<b style=\"color:' +
      (a.noOff.length ? 'var(--wheat)' : 'var(--green)') + '\">' + a.noOff.length + '</b> 人' +
      (a.noOff.length ? ' —— 他们只出现在单场榜，不进名册、也不进个人最好成绩榜' + link('noOff', '看名单') : '') + '</div>');"""),

("""      h.push(listLine(a.noOff, function (x) {
        return esc(x.name) + '<span style=\"color:var(--t3)\">（' + esc((x.lv || []).join('、') || '未填') +
          (x.vis ? ' · 已在公开名册' : '') + '）</span>';
      }, '没有'));""",
 """      h.push(listLine(a.noOff, function (x) {
        return esc(x.name) + '<span style=\"color:var(--t3)\">（身份 ' + esc((x.lv || []).join('、') || '未填') + '）</span>';
      }, '没有'));"""),

("""    h.push('<div>' + ICON(a.isRemoved.length) + ' 身份够、却被「<b>已移除显示</b>」挡着的：<b style=\"color:' +
      (a.isRemoved.length ? 'var(--wheat)' : 'var(--green)') + '\">' + a.isRemoved.length + '</b> 人' +
      (a.isRemoved.length ? ' —— 名册里点「↺ 恢复显示」就能放回来' + link('removed', '看名单') : '') + '</div>');""",
 """    h.push('<div>' + ICON(a.isRemoved.length) + ' 被「<b>已移除显示</b>」挡着的：<b style=\"color:' +
      (a.isRemoved.length ? 'var(--wheat)' : 'var(--green)') + '\">' + a.isRemoved.length + '</b> 人' +
      (a.isRemoved.length ? ' —— 名册里点「↺ 恢复显示」就能放回来（这是现在名册里唯一会\"看不到\"的原因）' + link('removed', '看名单') : '') + '</div>');"""),

("""    var official = lv.indexOf('正式') >= 0;
    var known = st.inBase || st.isNew;
    var why = [];
    if (!known) why.push('名册里根本没有这个人 —— 先核对是不是名字写错了（写错会被当成另一个人）');
    if (!official && known) why.push('身份不是「正式」（现在是「' + (lv.join('、') || '空') + '」）—— 成绩榜只统计正式队员，' +
      (isVisibleLevel(lv) ? '他进得了公开名册，但成绩一条都上不了榜' : '他连公开名册都进不去'));
    if (st.removed) why.push('被列在「已移除显示」名单里（身份够也照样不显示）');
    if (!list.length && known) why.push('一条成绩记录都没有 —— 不是被封住了，是确实还没有成绩');

    return { name: n, st: st, lv: lv, list: list, official: official, known: known,
             onBoard: onBoard, why: why };""",
 """    var known = st.inBase || st.isNew;
    var why = [];
    if (!known) why.push('名册里根本没有这个人 —— 先核对是不是名字写错了（写错会被当成另一个人）');
    if (known && st.removed) why.push('被列在「已移除显示」名单里 —— 名册里点他的「↺ 恢复显示」就回来了');
    if (!list.length && known) why.push('一条成绩记录都没有 —— 不是被封住了，是确实还没有成绩');

    return { name: n, st: st, lv: lv, list: list, known: known,
             onBoard: onBoard, why: why };"""),

("""    L.push('<div>' + MARK(d.official) + ' 身份：<b>' + esc((d.lv || []).join('、') || '未填') + '</b>' +
      (d.official ? '（成绩榜认这个身份）' : '（成绩榜<b>不</b>认，只认「正式」）') + '</div>');""",
 """    L.push('<div>' + MARK(d.known) + ' 身份：<b>' + esc((d.lv || []).join('、') || '未填') + '</b>' +
      '<span style=\"color:var(--t3)\">（只是标注，不影响显示）</span></div>');"""),

("""    if (!d.official && d.known) {
      L.push('<div class=\"tiny\" style=\"margin-top:8px;color:var(--t2);line-height:1.9\">' +
        '<b>怎么改：</b>数据管理 → 队员名册 → 搜索框打「' + esc(d.name) + '」→ 把「身份」改成 <b>正式</b> → ' +
        '保存名册修改 → 回到「同步」点一次「同步我的修改到线上」，等 1 分钟。</div>');
    }""",
 """    if (!d.known) {
      L.push('<div class=\"tiny\" style=\"margin-top:8px;color:var(--t2);line-height:1.9\">' +
        '<b>怎么改：</b>数据管理 → 队员名册 →「＋ 批量添加队员」把他加进名册 → 保存 → ' +
        '回到「同步」点一次「同步我的修改到线上」，等 1 分钟。</div>');
    } else if (d.st && d.st.removed) {
      L.push('<div class=\"tiny\" style=\"margin-top:8px;color:var(--t2);line-height:1.9\">' +
        '<b>怎么改：</b>数据管理 → 队员名册 → 往下「已从名册移除」那一栏点他的「↺ 恢复显示」→ ' +
        '「同步我的修改到线上」，等 1 分钟。</div>');
    }"""),
]


def apply(path, pairs, crlf):
    raw = open(path, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    txt = raw.decode('utf-8-sig').replace('\r\n', '\n')
    fails = []
    for i, (old, new) in enumerate(pairs):
        if old == new:
            continue
        n = txt.count(old)
        if n != 1:
            fails.append((i, n, old.splitlines()[0][:70]))
            continue
        txt = txt.replace(old, new, 1)
    if fails:
        print('❌ %s 有 %d 处没匹配上：' % (path, len(fails)))
        for i, n, s in fails:
            print('   #%d 出现 %d 次: %s' % (i, n, s))
        return False
    data = txt.replace('\n', '\r\n') if crlf else txt
    out = (b'\xef\xbb\xbf' if bom else b'') + data.encode('utf-8')
    open(path, 'wb').write(out)
    print('✅ %s：%d 处替换完成' % (path, len([p for p in pairs if p[0] != p[1]])))
    return True


ok = True
ok &= apply(os.path.join(HERE, 'assets', 'app.js'), APP, True)
ok &= apply(os.path.join(HERE, 'assets', 'health-check.js'), HEALTH, True)
sys.exit(0 if ok else 1)
