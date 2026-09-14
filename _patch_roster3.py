# -*- coding: utf-8 -*-
"""名册重名处理：
   ① 不再硬拦重名（姓名可能重复），改成给准确提示
   ② 名字在原始名册里但身份是「队员/未分级」（展示版看不到）→ 说明原因 + 「搜出来改他的身份」
   ③ 新增队员各带 uid，同名两人也能分别编辑/删除
   ④ 批量添加：只跳过"完全相同的行"，名字重复照加，只在预览里提醒
"""
import io

p = "assets/app.js"
s = io.open(p, encoding="utf-8", newline="").read().replace("\r\n", "\n")
orig = len(s)

# ── ① uid 生成器 ───────────────────────────────────────────────────────────
old = r"""let nmBatchRows = null;"""
new = r"""let nmBatchRows = null;
function nmUid() { return 'nm' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }"""
assert s.count(old) == 1, "① nmUid"
s = s.replace(old, new)

# ── ② 单条添加表单后面加提示框容器 ─────────────────────────────────────────
old = r"""      <span class="tiny" style="margin-left:10px">添加完点「同步我的修改到线上」，全队名册立刻多这个人</span>
    </div>"""
new = r"""      <span class="tiny" style="margin-left:10px">添加完点「同步我的修改到线上」，全队名册立刻多这个人</span>
      <div id="nmAddBox"></div>
    </div>"""
assert s.count(old) == 1, "② 提示框容器"
s = s.replace(old, new)

# ── ③ 单条添加：重名不再拦，给准确说明 + 两个选择 ──────────────────────────
old = r"""  const am = $('#btnAddMember');
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
  };"""
new = r"""  const am = $('#btnAddMember');
  if (am) am.onclick = () => {
    const name = ($('#nm_name').value || '').trim().replace(/\s/g, '');
    if (!name) return toast('请填姓名');
    if (!/^[\u4e00-\u9fa5·]{2,6}$/.test(name)) return toast('姓名请填 2~6 个汉字');
    const l = ovLocal();
    l.newMembers = l.newMembers || [];
    const doAdd = (note) => {
      l.newMembers.push({
        uid: nmUid(),
        name,
        sex: $('#nm_sex').value,
        college: ($('#nm_college').value || '').trim(),
        major: ($('#nm_major').value || '').trim(),
        grade: ($('#nm_grade').value || '').trim(),
        level: $('#nm_level').value.split(',').map(x => x.trim()).filter(Boolean),
        addedAt: new Date().toISOString().slice(0, 10),
      });
      saveLocalOv();
      toast('已把 ' + name + ' 加进名册' + (note || '') + ' —— 记得点「同步我的修改到线上」发布', 8000);
      render();
    };
    const base = (BASE.roster || []).find(m => m.name === name);
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
        box.innerHTML = '<div class="notice" style="margin-top:12px">' + why
          + ((base && !vis) ? '<br><br>👉 想让他出现在公开名册：点「搜出来改他的身份」，把那个人的「身份」改成 正式 或 预备，'
                             + '再点「保存名册修改」（不用新加一个人，也不用同步两次）。' : '')
          + '<div class="chips" style="margin-top:10px">'
          + ((base && !vis) ? '<button class="btn sm" id="btnNmFindIt">搜出来改他的身份</button>' : '')
          + '<button class="btn ghost sm" id="btnNmForce">是另一个人，仍然添加</button></div></div>';
        const b1 = $('#btnNmFindIt'), b2 = $('#btnNmForce');
        if (b1) b1.onclick = () => { state.mRosterQ = name; render(); };
        if (b2) b2.onclick = () => { am.dataset.force = '1'; am.click(); };
      }
      if (am.dataset.force !== '1') return;
      delete am.dataset.force;
    }
    doAdd(dupNew ? '（同名，已有 ' + l.newMembers.filter(m => m.name === name).length + ' 个同名的人）' : '');
  };"""
assert s.count(old) == 1, "③ 单条添加逻辑"
s = s.replace(old, new)

# ── ④ 名册行：新增队员用 uid 定位（同名也不串）──────────────────────────────
old = r"""      ${editList.map(m => {
        const e = m._isNew ? m : (o.memberEdits[m.name] || {});
        return `
        <div class="mrow">
          <div class="mrow-h"><b>${esc(m.name)}</b>
            ${m._isNew ? '<span class="tagbadge green">新增</span>' : ''}
            <span class="tagbadge ${(m.level || []).some(l => l === '正式' || l === '预备') ? 'wheat' : ''}">${esc((m.level || []).join('/') || '未分级')}</span>
          </div>
          <div class="mrow-f">
            <input data-me="${esc(m.name)}" data-mf="college" value="${esc(e.college != null ? e.college : (m.college || ''))}" placeholder="学院">
            <input data-me="${esc(m.name)}" data-mf="major" value="${esc(e.major != null ? e.major : (m.major || ''))}" placeholder="专业">
            <input data-me="${esc(m.name)}" data-mf="grade" value="${esc(e.grade != null ? e.grade : (m.grade || ''))}" placeholder="年级" class="w60">
            <select data-me="${esc(m.name)}" data-mf="level">"""
new = r"""      ${editList.map(m => {
        const e = m._isNew ? m : (o.memberEdits[m.name] || {});
        const k = m._isNew ? ('data-muid="' + esc(m.uid || m.name) + '"') : ('data-me="' + esc(m.name) + '"');
        return `
        <div class="mrow">
          <div class="mrow-h"><b>${esc(m.name)}</b>
            ${m._isNew ? '<span class="tagbadge green">新增</span>' : ''}
            <span class="tagbadge ${(m.level || []).some(l => l === '正式' || l === '预备') ? 'wheat' : ''}">${esc((m.level || []).join('/') || '未分级')}</span>
          </div>
          <div class="mrow-f">
            <input ${k} data-mf="college" value="${esc(e.college != null ? e.college : (m.college || ''))}" placeholder="学院">
            <input ${k} data-mf="major" value="${esc(e.major != null ? e.major : (m.major || ''))}" placeholder="专业">
            <input ${k} data-mf="grade" value="${esc(e.grade != null ? e.grade : (m.grade || ''))}" placeholder="年级" class="w60">
            <select ${k} data-mf="level">"""
assert s.count(old) == 1, "④ 名册行上半"
s = s.replace(old, new)

old = r"""            <button class="btn danger sm" data-mdel="${esc(m.name)}">删除</button>
          </div>
        </div>`;"""
new = r"""            ${m._isNew
              ? '<button class="btn danger sm" data-muiddel="' + esc(m.uid || m.name) + '">删除</button>'
              : '<button class="btn danger sm" data-mdel="' + esc(m.name) + '">删除</button>'}
          </div>
        </div>`;"""
assert s.count(old) == 1, "④ 名册行删除按钮"
s = s.replace(old, new)

# ── ⑤ 保存名册：新增队员按 uid 保存 ────────────────────────────────────────
old = r"""    Object.entries(byName).forEach(([n, f]) => {
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
new = r"""    Object.entries(byName).forEach(([n, f]) => {
      const lvl = (f.level || '').split(',').map(s => s.trim()).filter(Boolean);
      const base = (BASE.roster || []).find(m => m.name === n) || {};
      edits[n] = {
        college: f.college, major: f.major, grade: f.grade,
        level: lvl.length ? lvl : (base.level || []).filter(l => l === '正式' || l === '预备'),
      };
    });
    // 队长新加的队员：按 uid 精确保存（同名也不会互相覆盖）
    const byUid = {};
    $$('[data-muid]').forEach(el => {
      const u = el.dataset.muid, f = el.dataset.mf;
      byUid[u] = byUid[u] || {};
      byUid[u][f] = el.value;
    });
    Object.entries(byUid).forEach(([u, f]) => {
      const nm = (ovLocal().newMembers || []).find(m => (m.uid || m.name) === u);
      if (!nm) return;
      nm.college = f.college; nm.major = f.major; nm.grade = f.grade;
      const lvl = (f.level || '').split(',').map(x => x.trim()).filter(Boolean);
      nm.level = lvl.length ? lvl : (nm.level || ['正式']);
    });"""
assert s.count(old) == 1, "⑤ 保存名册按 uid"
s = s.replace(old, new)

# ── ⑥ 删除：新增队员按 uid 删 ───────────────────────────────────────────────
old = r"""  $$('[data-mdel]').forEach(b => b.onclick = () => {
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
new = r"""  $$('[data-muiddel]').forEach(b => b.onclick = () => {
    const u = b.dataset.muiddel, l = ovLocal();
    l.newMembers = (l.newMembers || []).filter(m => (m.uid || m.name) !== u);
    saveLocalOv(); toast('已删除这个新增队员'); render();
  });
  $$('[data-mdel]').forEach(b => b.onclick = () => {
    const n = b.dataset.mdel;
    const l = ovLocal();
    l.hidden = (l.hidden || []).concat([n]);
    saveLocalOv(); toast('已从公开名册移除 ' + n); render();
  });"""
assert s.count(old) == 1, "⑥ 删除按 uid"
s = s.replace(old, new)

# ── ⑦ 批量解析：名字重复照加，只跳过"完全相同的行" ──────────────────────────
old = r"""  const out = [], skip = [], seen = new Set(rosterList().map(m => m.name));
  rows.forEach((r, li) => {
    const get = (k) => (map[k] == null || r[map[k]] == null) ? '' : String(r[map[k]]).trim();
    const nm = get('name').replace(/\s/g, '');
    if (!nm) return;
    if (!/^[\u4e00-\u9fa5·]{2,6}$/.test(nm)) { skip.push('第' + (li + 1) + '行「' + nm.slice(0, 10) + '」姓名不规范'); return; }
    if (seen.has(nm)) { skip.push(nm + '（已在名册里）'); return; }
    seen.add(nm);
    let lv = get('level').split(/[,，、/]/).map(x => x.trim()).filter(x => x === '正式' || x === '预备');
    if (!lv.length) lv = ['正式'];
    const sx = get('sex');
    out.push({
      name: nm, college: get('college'), major: get('major'), grade: get('grade'),
      sex: /男/.test(sx) ? '男' : (/女/.test(sx) ? '女' : ''),
      level: lv, addedAt: new Date().toISOString().slice(0, 10),
    });
  });
  return { rows: out, skip };"""
new = r"""  const out = [], skip = [], same = [], seenRow = new Set();
  const existing = new Set([].concat((BASE.roster || []).map(m => m.name), (rosterList().map(m => m.name))));
  rows.forEach((r, li) => {
    const get = (k) => (map[k] == null || r[map[k]] == null) ? '' : String(r[map[k]]).trim();
    const nm = get('name').replace(/\s/g, '');
    if (!nm) return;
    if (!/^[\u4e00-\u9fa5·]{2,6}$/.test(nm)) { skip.push('第' + (li + 1) + '行「' + nm.slice(0, 10) + '」姓名不规范'); return; }
    const rowKey = [nm, get('college'), get('major'), get('grade')].join('|');
    if (seenRow.has(rowKey)) { skip.push('第' + (li + 1) + '行「' + nm + '」与本批前面某行完全相同'); return; }
    seenRow.add(rowKey);
    if (existing.has(nm)) same.push(nm);            // 同名的照加，只做个提醒
    let lv = get('level').split(/[,，、/]/).map(x => x.trim()).filter(x => x === '正式' || x === '预备');
    if (!lv.length) lv = ['正式'];
    const sx = get('sex');
    out.push({
      uid: nmUid(),
      name: nm, college: get('college'), major: get('major'), grade: get('grade'),
      sex: /男/.test(sx) ? '男' : (/女/.test(sx) ? '女' : ''),
      level: lv, addedAt: new Date().toISOString().slice(0, 10),
    });
  });
  return { rows: out, skip: skip, same: same };"""
assert s.count(old) == 1, "⑦ 批量解析"
s = s.replace(old, new)

# ── ⑧ 预览里提示同名情况；确认时不再按名字去重 ──────────────────────────────
old = r"""  const data = nmBatchRows || { rows: [], skip: [] };"""
new = r"""  const data = nmBatchRows || { rows: [], skip: [], same: [] };"""
assert s.count(old) == 1, "⑧a 预览默认值"
s = s.replace(old, new)

old = r"""      解析出 <b>${data.rows.length}</b> 人${data.skip.length ? '；跳过 ' + data.skip.length + ' 条：' + esc(data.skip.slice(0, 3).join('；')) + (data.skip.length > 3 ? ' 等' : '') : ''}
      ${ghCfg().token ? '。点下面按钮一次加入，再去「同步」发布。' : '。点下面按钮加入本机，然后去「同步」配好令牌再发布。'}"""
new = r"""      解析出 <b>${data.rows.length}</b> 人${data.skip.length ? '；跳过 ' + data.skip.length + ' 条：' + esc(data.skip.slice(0, 3).join('；')) + (data.skip.length > 3 ? ' 等' : '') : ''}
      ${(data.same || []).length ? '；其中 <b>' + data.same.length + '</b> 人与名册里现有的人同名（同名可以并存，若其实是同一人，加入后到列表里删掉即可）' : ''}
      ${ghCfg().token ? '。点下面按钮一次加入，再去「同步」发布。' : '。点下面按钮加入本机，然后去「同步」配好令牌再发布。'}"""
assert s.count(old) == 1, "⑧b 预览文案"
s = s.replace(old, new)

old = r"""    let added = 0, dup = 0;
    data.rows.forEach(r => {
      if (l.newMembers.some(m => m.name === r.name) || (BASE.roster || []).some(m => m.name === r.name)) { dup++; return; }
      l.newMembers.push(r); added++;
    });
    saveLocalOv();
    nmBatchRows = null;
    state.mRosterQ = '';
    toast('已把 ' + added + ' 人加进名册' + (dup ? '（' + dup + ' 人已在名册里，跳过）' : '')
          + ' —— 记得点「同步我的修改到线上」发布', 10000);
    render();"""
new = r"""    let added = 0;
    const dupSame = [];
    data.rows.forEach(r => {
      if (l.newMembers.some(m => (m.uid || m.name) === (r.uid || r.name)
            || (m.name === r.name && (m.college || '') === (r.college || '') && (m.major || '') === (r.major || '')))) {
        dupSame.push(r.name); return;               // 完全一样的人（防手抖重复加入）
      }
      if (!r.uid) r.uid = nmUid();
      l.newMembers.push(r); added++;
    });
    saveLocalOv();
    nmBatchRows = null;
    state.mRosterQ = '';
    toast('已把 ' + added + ' 人加进名册'
          + (dupSame.length ? '（' + dupSame.length + ' 人之前已经加过，跳过：' + dupSame.slice(0, 3).join('、') + '）' : '')
          + ' —— 记得点「同步我的修改到线上」发布', 11000);
    render();"""
assert s.count(old) == 1, "⑧c 确认入库"
s = s.replace(old, new)

io.open(p, "w", encoding="utf-8", newline="\r\n").write(s)
print("app.js 重名/uid 补丁完成: %d -> %d 字符" % (orig, len(s)))
