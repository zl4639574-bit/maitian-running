# -*- coding: utf-8 -*-
"""名册：新增「添加新队员」入口（姓名/性别/学院/专业/年级/身份）+ 进同步链路（newMembers）"""
import io

p = "assets/app.js"
s = io.open(p, encoding="utf-8", newline="").read().replace("\r\n", "\n")
orig = len(s)

# ── ① 数据模型：EMPTY_OV 加 newMembers ─────────────────────────────────────
old = r"""const EMPTY_OV = { team: {}, honors: null, activities: null, hidden: [], memberEdits: {},
                   results: [], photos: [], competitions: [], hiddenRecords: [],
                   hall: null, queue: null };"""
new = r"""const EMPTY_OV = { team: {}, honors: null, activities: null, hidden: [], memberEdits: {},
                   newMembers: [], results: [], photos: [], competitions: [], hiddenRecords: [],
                   hall: null, queue: null };"""
assert s.count(old) == 1, "① EMPTY_OV"
s = s.replace(old, new)

# ── ② 云端+本机合并：newMembers（同名的本机优先，防止重复）─────────────────
old = r"""    memberEdits: Object.assign({}, c.memberEdits || {}, l.memberEdits || {}),"""
new = r"""    memberEdits: Object.assign({}, c.memberEdits || {}, l.memberEdits || {}),
    newMembers: (function () {
      const m = {};
      (c.newMembers || []).forEach(x => { if (x && x.name) m[x.name] = x; });
      (l.newMembers || []).forEach(x => { if (x && x.name) m[x.name] = x; });   // 本机的覆盖云端
      return Object.keys(m).map(k => m[k]);
    })(),"""
assert s.count(old) == 1, "② ov() newMembers"
s = s.replace(old, new)

# ── ③ rosterList 把新增队员也算进名册 ───────────────────────────────────────
old = r"""function rosterList() {
  const o = ov();
  const hidden = new Set(o.hidden);
  return (BASE.roster || [])
    .filter(m => !hidden.has(m.name))
    .filter(m => (m.level || []).some(l => l === '正式' || l === '预备'))
    .map(m => {
      const e = o.memberEdits[m.name] || {};
      return Object.assign({}, m, e, {
        level: e.level || (m.level || []).filter(l => l === '正式' || l === '预备'),
      });
    });
}"""
new = r"""function rosterList() {
  const o = ov();
  const hidden = new Set(o.hidden);
  const fromBase = (BASE.roster || [])
    .filter(m => !hidden.has(m.name))
    .filter(m => (m.level || []).some(l => l === '正式' || l === '预备'))
    .map(m => {
      const e = o.memberEdits[m.name] || {};
      return Object.assign({}, m, e, {
        level: e.level || (m.level || []).filter(l => l === '正式' || l === '预备'),
      });
    });
  // 队长在「队员名册」里手动添加的新队员
  const added = (o.newMembers || [])
    .filter(m => !hidden.has(m.name))
    .filter(m => (m.level || []).some(l => l === '正式' || l === '预备'));
  return fromBase.concat(added);
}"""
assert s.count(old) == 1, "③ rosterList"
s = s.replace(old, new)

# ── ④ 管理列表：把新增队员也列进来（带"新增"标记）─────────────────────────
old = r"""  const editList = ros.filter(m => !hiddenSet.has(m.name)).filter(m => state.mRosterQ
    ? m.name.includes(state.mRosterQ) : (m.level || []).some(l => l === '正式' || l === '预备')).slice(0, 60);"""
new = r"""  const addedList = (o.newMembers || []).filter(m => !state.mRosterQ || m.name.includes(state.mRosterQ));
  const editList = ros.filter(m => !hiddenSet.has(m.name)).filter(m => state.mRosterQ
    ? m.name.includes(state.mRosterQ) : (m.level || []).some(l => l === '正式' || l === '预备')).slice(0, 60)
    .map(m => Object.assign({}, m, { _isNew: false }))
    .concat(addedList.map(m => Object.assign({}, m, { _isNew: true })));"""
assert s.count(old) == 1, "④ editList"
s = s.replace(old, new)

# ── ⑤ 名册分区：提示改写 + 添加新队员表单 ─────────────────────────────────
old = r"""    <div class="tiny" style="margin-bottom:12px">
      名册共 ${ros.length} 人（展示版只显示标记为正式/预备的 ${rosterList().length} 人）。
      可以改学院/专业/年级/身份，或把某人从公开名册里删掉。改完记得去「同步」发布。
    </div>"""
new = r"""    <div class="tiny" style="margin-bottom:12px">
      原始名册 ${ros.length} 人${(o.newMembers || []).length ? '，队长新增 ' + (o.newMembers || []).length + ' 人' : ''}
      （展示版显示正式/预备的 ${rosterList().length} 人）。改完记得去「同步」发布。
    </div>

    <div class="notice" style="margin-bottom:18px;border-color:var(--wheat)">
      <b>＋ 添加新队员</b>
      <div class="grid2" style="margin:10px 0 4px">
        <div class="field"><label>姓名 *</label><input id="nm_name" placeholder="例如 张三"></div>
        <div class="field"><label>性别</label>
          <select id="nm_sex"><option value="">未填</option><option value="男">男</option><option value="女">女</option></select></div>
        <div class="field"><label>学院</label><input id="nm_college" placeholder="例如 林学院"></div>
        <div class="field"><label>专业</label><input id="nm_major" placeholder="例如 林学2101"></div>
        <div class="field"><label>年级</label><input id="nm_grade" placeholder="例如 2023" class="w60"></div>
        <div class="field"><label>身份</label>
          <select id="nm_level"><option value="正式">正式</option><option value="预备">预备</option><option value="正式,预备">正式+预备</option></select></div>
      </div>
      <button class="btn" id="btnAddMember" style="margin-top:8px">添加到名册</button>
      <span class="tiny" style="margin-left:10px">添加完点「同步我的修改到线上」，全队名册立刻多这个人</span>
    </div>"""
assert s.count(old) == 1, "⑤ 名册提示 + 表单"
s = s.replace(old, new)

# ── ⑥ 名册行：新增的人显示「新增」标记，编辑值取记录本身 ────────────────────
old = r"""      ${editList.map(m => {
        const e = o.memberEdits[m.name] || {};
        return `
        <div class="mrow">
          <div class="mrow-h"><b>${esc(m.name)}</b>
            <span class="tagbadge ${(m.level || []).some(l => l === '正式' || l === '预备') ? 'wheat' : ''}">${esc((m.level || []).join('/') || '未分级')}</span>
          </div>"""
new = r"""      ${editList.map(m => {
        const e = m._isNew ? m : (o.memberEdits[m.name] || {});
        return `
        <div class="mrow">
          <div class="mrow-h"><b>${esc(m.name)}</b>
            ${m._isNew ? '<span class="tagbadge green">新增</span>' : ''}
            <span class="tagbadge ${(m.level || []).some(l => l === '正式' || l === '预备') ? 'wheat' : ''}">${esc((m.level || []).join('/') || '未分级')}</span>
          </div>"""
assert s.count(old) == 1, "⑥ 名册行"
s = s.replace(old, new)

# ── ⑦ 保存名册：新增队员直接改记录，别人仍写 memberEdits ────────────────────
old = r"""    Object.entries(byName).forEach(([n, f]) => {
      const base = (BASE.roster || []).find(m => m.name === n) || {};
      const lvl = (f.level || '').split(',').map(s => s.trim()).filter(Boolean);
      edits[n] = {
        college: f.college, major: f.major, grade: f.grade,
        level: lvl.length ? lvl : (base.level || []).filter(l => l === '正式' || l === '预备'),
      };
    });"""
new = r"""    Object.entries(byName).forEach(([n, f]) => {
      const lvl = (f.level || '').split(',').map(s => s.trim()).filter(Boolean);
      const nm = (ovLocal().newMembers || []).find(m => m.name === n);
      if (nm) {                                  // 队长新加的队员：直接改记录
        nm.college = f.college; nm.major = f.major; nm.grade = f.grade;
        nm.level = lvl.length ? lvl : (nm.level || ['正式']);
        return;
      }
      const base = (BASE.roster || []).find(m => m.name === n) || {};
      edits[n] = {
        college: f.college, major: f.major, grade: f.grade,
        level: lvl.length ? lvl : (base.level || []).filter(l => l === '正式' || l === '预备'),
      };
    });"""
assert s.count(old) == 1, "⑦ 保存名册"
s = s.replace(old, new)

# ── ⑧ 删除：新增的人直接删掉，原始名册的人进 hidden ─────────────────────────
old = r"""  $$('[data-mdel]').forEach(b => b.onclick = () => {
    const n = b.dataset.mdel;
    const l = ovLocal();
    l.hidden = (l.hidden || []).concat([n]);
    saveLocalOv(); toast('已从公开名册移除 ' + n); render();
  });"""
new = r"""  $$('[data-mdel]').forEach(b => b.onclick = () => {
    const n = b.dataset.mdel;
    const l = ovLocal();
    l.newMembers = l.newMembers || [];
    if (l.newMembers.some(m => m.name === n)) {          // 队长新增的人：直接删掉
      l.newMembers = l.newMembers.filter(m => m.name !== n);
      saveLocalOv(); toast('已删除新队员 ' + n); render(); return;
    }
    l.hidden = (l.hidden || []).concat([n]);
    saveLocalOv(); toast('已从公开名册移除 ' + n); render();
  });"""
assert s.count(old) == 1, "⑧ 删除"
s = s.replace(old, new)

# ── ⑨ 添加入口的事件 ───────────────────────────────────────────────────────
old = r"""  const mq = $('#mRosterQ');"""
new = r"""  const am = $('#btnAddMember');
  if (am) am.onclick = () => {
    const name = ($('#nm_name').value || '').trim().replace(/\s/g, '');
    if (!name) return toast('请填姓名');
    if (!/^[\u4e00-\u9fa5·]{2,6}$/.test(name)) return toast('姓名请填 2~6 个汉字');
    const l = ovLocal();
    l.newMembers = l.newMembers || [];
    if (l.newMembers.some(m => m.name === name) || rosterList().some(m => m.name === name)
        || (BASE.roster || []).some(m => m.name === name))
      return toast(name + ' 已经在名册里了', 6000);
    l.newMembers.push({
      name,
      sex: $('#nm_sex').value,
      college: ($('#nm_college').value || '').trim(),
      major: ($('#nm_major').value || '').trim(),
      grade: ($('#nm_grade').value || '').trim(),
      level: $('#nm_level').value.split(',').map(x => x.trim()).filter(Boolean),
      addedAt: new Date().toISOString().slice(0, 10),
    });
    saveLocalOv();
    toast('已把 ' + name + ' 加进名册 —— 记得点「同步我的修改到线上」发布', 7000);
    render();
  };
  const mq = $('#mRosterQ');"""
assert s.count(old) == 1, "⑨ 添加事件"
s = s.replace(old, new)

# ── ⑩ 待同步计数 / 推送内容里带上 newMembers ────────────────────────────────
old = r"""  if (l.memberEdits) n += Object.keys(l.memberEdits).length;"""
new = r"""  if (l.memberEdits) n += Object.keys(l.memberEdits).length;
  if (l.newMembers && l.newMembers.length) n += l.newMembers.length;"""
assert s.count(old) == 1, "⑩ pendingCount"
s = s.replace(old, new)

old = r"""      memberEdits: Object.assign({}, cloud.memberEdits || {}, l.memberEdits || {}),"""
new = r"""      memberEdits: Object.assign({}, cloud.memberEdits || {}, l.memberEdits || {}),
      newMembers: (function () {
        const m = {};
        (cloud.newMembers || []).forEach(x => { if (x && x.name) m[x.name] = x; });
        (l.newMembers || []).forEach(x => { if (x && x.name) m[x.name] = x; });
        return Object.keys(m).map(k => m[k]);
      })(),"""
assert s.count(old) == 1, "⑩ pushToGitHub"
s = s.replace(old, new)

io.open(p, "w", encoding="utf-8", newline="\r\n").write(s)
print("app.js 名册补丁完成: %d -> %d 字符" % (orig, len(s)))
