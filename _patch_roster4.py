# -*- coding: utf-8 -*-
"""① 中文拼音输入时不要边打边检索（IME composition）
   ② 新增队员身份为空 → 自动按「正式」（否则会加进去却不出现在公开名册）
   ③ 名册区显示"还有 N 处没同步" + 一键同步"""
import io

p = "assets/app.js"
s = io.open(p, encoding="utf-8", newline="").read().replace("\r\n", "\n")
orig = len(s)

# ── ① 拼音输入不触发检索 ──────────────────────────────────────────────────
old = r"""document.addEventListener('input', e => {
  if (e.target.id === 'boardQ') {"""
new = r"""/* 中文输入法（拼音）正在组词时不要触发检索 —— 否则会打断输入、边打边搜 */
const IME_IDS = ['boardQ', 'rosterQ', 'mRosterQ', 'nm_name', 'nm_college', 'nm_major', 'nm_grade'];
document.addEventListener('compositionstart', e => {
  if (e.target && IME_IDS.indexOf(e.target.id || '') >= 0) window._imeOn = true;
}, true);
document.addEventListener('compositionend', e => {
  if (e.target && IME_IDS.indexOf(e.target.id || '') >= 0) {
    window._imeOn = false;
    try { e.target.dispatchEvent(new Event('input', { bubbles: true })); } catch (err) {}
  }
}, true);

document.addEventListener('input', e => {
  if (window._imeOn) return;                      // 组词中，先不管
  if (e.target.id === 'boardQ') {"""
assert s.count(old) == 1, "① 输入监听"
s = s.replace(old, new)

old = r"""  const mq = $('#mRosterQ');
  if (mq) mq.oninput = () => {
    state.mRosterQ = mq.value;"""
new = r"""  const mq = $('#mRosterQ');
  if (mq) mq.oninput = () => {
    if (window._imeOn) return;                    // 拼音组词中，不检索
    state.mRosterQ = mq.value;"""
assert s.count(old) == 1, "① 名册管理检索"
s = s.replace(old, new)

# ── ② 新增队员：身份为空就按「正式」（老的坏数据也顺手治好）─────────────────
old = r"""    newMembers: (function () {
      const m = {};
      (c.newMembers || []).forEach(x => { if (x && x.name) m[x.name] = x; });
      (l.newMembers || []).forEach(x => { if (x && x.name) m[x.name] = x; });   // 本机的覆盖云端
      return Object.keys(m).map(k => m[k]);
    })(),"""
new = r"""    newMembers: (function () {
      const m = {};
      (c.newMembers || []).forEach(x => { if (x && x.name) m[x.name] = x; });
      (l.newMembers || []).forEach(x => { if (x && x.name) m[x.name] = x; });   // 本机的覆盖云端
      // 新增队员没填身份 → 默认「正式」；不然会被加进去却不出现在公开名册里
      return Object.keys(m).map(k => {
        const x = m[k];
        if (!(x.level || []).length) return Object.assign({}, x, { level: ['正式'] });
        return x;
      });
    })(),"""
assert s.count(old) == 1, "② ov() 新队员身份"
s = s.replace(old, new)

old = r"""  p.addMember.forEach(x => {
    const info = Object.assign({}, x.info);
    if (!info.level) info.level = ['正式'];"""
new = r"""  p.addMember.forEach(x => {
    const info = Object.assign({}, x.info);
    if (!info.level || !info.level.length) info.level = ['正式'];"""
assert s.count(old) == 1, "② 导入新增的身份"
s = s.replace(old, new)

# pushToGitHub 也要带上（防止把空身份写进云端）
old = r"""      newMembers: (function () {
        const m = {};
        (cloud.newMembers || []).forEach(x => { if (x && x.name) m[x.name] = x; });
        (l.newMembers || []).forEach(x => { if (x && x.name) m[x.name] = x; });
        return Object.keys(m).map(k => m[k]);
      })(),"""
new = r"""      newMembers: (function () {
        const m = {};
        (cloud.newMembers || []).forEach(x => { if (x && x.name) m[x.name] = x; });
        (l.newMembers || []).forEach(x => { if (x && x.name) m[x.name] = x; });
        return Object.keys(m).map(k => {
          const x = m[k];
          return (x.level || []).length ? x : Object.assign({}, x, { level: ['正式'] });
        });
      })(),"""
assert s.count(old) == 1, "② 推送新队员身份"
s = s.replace(old, new)

# ── ③ 名册区：还有多少处没同步 + 一键同步 ──────────────────────────────────
old = r"""    <div class="notice" style="margin-bottom:18px;border-color:var(--wheat)">
      <b>＋ 添加新队员</b>"""
new = r"""    ${(LOCAL_OV && ((LOCAL_OV.newMembers || []).length + Object.keys(LOCAL_OV.memberEdits || {}).length)) ? `
    <div class="notice" style="border-color:var(--wheat);margin-bottom:16px;line-height:2">
      ⚠️ 名册有 <b>${(LOCAL_OV.newMembers || []).length + Object.keys(LOCAL_OV.memberEdits || {}).length}</b> 处修改
      还<b>只在这台设备上</b>（新增 ${(LOCAL_OV.newMembers || []).length} 人 / 修改 ${Object.keys(LOCAL_OV.memberEdits || {}).length} 人）。
      <b>不点同步，展示版的名册不会变。</b>
      ${ghCfg().token ? '<div class="chips" style="margin-top:10px"><button class="btn" id="btnRosterSync">立即同步到线上</button></div>'
                      : '<br>另外还没配「访问令牌」，去「同步」里填一次就能发布了。'}
    </div>` : ''}

    <div class="notice" style="margin-bottom:18px;border-color:var(--wheat)">
      <b>＋ 添加新队员</b>"""
assert s.count(old) == 1, "③ 未同步提示"
s = s.replace(old, new)

old = r"""  const am = $('#btnAddMember');"""
new = r"""  const rsy = $('#btnRosterSync');
  if (rsy) rsy.onclick = () => pushToGitHub();
  const am = $('#btnAddMember');"""
assert s.count(old) == 1, "③ 一键同步事件"
s = s.replace(old, new)

io.open(p, "w", encoding="utf-8", newline="\r\n").write(s)
print("名册补丁完成: %d -> %d 字符" % (orig, len(s)))
