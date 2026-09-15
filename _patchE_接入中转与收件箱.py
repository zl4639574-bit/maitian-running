# -*- coding: utf-8 -*-
"""E 补丁：接入云端中转
   ① ov() 增加 relay 字段（中转地址+口令，跟着 overrides.js 同步给所有队员端）
   ② ghList / ghDelete（读收件箱目录、接收后删掉）
   ③ 队员端：「直接提交给队长（不用发微信）」按钮
   ④ 队长版：同步面板填中转地址+口令；上传页新增「① 收件箱」一键接收
"""
import io, os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'app.js')
s = io.open(P, 'rb').read().decode('utf-8').replace('\r\n', '\n')
done = []


def rep(old, new, label, cnt=1):
    global s
    n = s.count(old)
    assert n == cnt, '✗ %s：期望 %d 处，实际 %d 处' % (label, cnt, n)
    s = s.replace(old, new)
    done.append(label)


# ① ov() 加 relay
rep("""    team: Object.assign({}, c.team || {}, l.team || {}),""",
    """    team: Object.assign({}, c.team || {}, l.team || {}),
    relay: l.relay || c.relay || null,          // 成绩/资料收件中转（队员端据此直传）""",
    '① ov() 加 relay')

# ② ghList / ghDelete / relayCfg / 提交
rep("""async function ghGetSha(cfg, path) {""",
    """/** 列出某个目录（收件箱用） */
async function ghList(cfg, dir) {
  const r = await fetch(`${GH}/repos/${cfg.owner}/${cfg.repo}/contents/${encodeURI(dir)}?ref=${encodeURIComponent(cfg.branch || 'master')}`, { headers: ghHeaders(cfg), cache: 'no-store' });
  if (r.status === 404) return [];                       // 目录还不存在 = 空
  if (!r.ok) throw new Error('读取 ' + dir + ' 失败 ' + r.status + ghHint(r.status));
  const j = await r.json();
  return Array.isArray(j) ? j : [];
}

/** 删除仓库里的某个文件（接收完的上报就删掉） */
async function ghDelete(cfg, path, message) {
  const sha = await ghGetSha(cfg, path);
  if (!sha) return true;
  const r = await fetch(`${GH}/repos/${cfg.owner}/${cfg.repo}/contents/${encodeURI(path)}`, {
    method: 'DELETE', headers: ghHeaders(cfg),
    body: JSON.stringify({ message: message || ('删除 ' + path), sha: sha, branch: cfg.branch || 'master' }),
  });
  if (!r.ok) throw new Error('删除 ' + path + ' 失败 ' + r.status);
  return true;
}

/** 中转配置（队员端靠它直传；存在 overrides.js 里同步下去，不含任何令牌） */
function relayCfg() {
  const r = ov().relay;
  return (r && String(r.url || '').trim()) ? { url: String(r.url).trim(), code: String(r.code || '') } : null;
}

/** 提交到中转（队员端用）。返回 {ok, error} */
async function postToRelay(type, payload) {
  const rc = relayCfg();
  if (!rc) return { ok: false, error: '队长还没配置收件地址' };
  try {
    const r = await fetch(rc.url, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: rc.code, type: type, payload: payload }),
    });
    const j = await r.json().catch(() => ({}));
    if (r.ok && j && j.ok) return { ok: true, id: j.id };
    return { ok: false, error: (j && j.error) || ('提交失败 ' + r.status) };
  } catch (e) {
    return { ok: false, error: '连不上收件服务（' + String((e && e.message) || e).slice(0, 40) + '）' };
  }
}

async function ghGetSha(cfg, path) {""",
    '② ghList/ghDelete/relayCfg/postToRelay')

# ③ 队员端提交按钮：成绩上报页
rep("""        ${rep ? `<button class="btn sm" id="btnShare" ${L.length ? '' : 'disabled'}>📤 直接发给队长</button>` : ''}""",
    """        ${rep && relayCfg() ? `<button class="btn sm" id="btnSend" ${L.length ? '' : 'disabled'}>⚡ 直接提交给队长（不用发微信）</button>` : ''}
        ${rep ? `<button class="btn ${relayCfg() ? 'ghost' : ''} sm" id="btnShare" ${L.length ? '' : 'disabled'}>📤 发给队长（微信）</button>` : ''}""",
    '③a 上报页加直传键')

rep("""  const sh = $('#btnShare');
  if (sh) sh.onclick = async () => {""",
    """  const sd = $('#btnSend');
  if (sd) sd.onclick = async () => {
    sd.disabled = true; sd.textContent = '提交中…';
    const payload = { date: todayStr(), rows: myResults().map(r => ({ name: r.name, event: r.event,
      fmt: r.fmt || fmtSec(r.sec), sec: r.sec, date: r.date, meet: r.meet || '', rank: r.rank || '' })) };
    const res = await postToRelay('scores', payload);
    sd.disabled = false; sd.textContent = '⚡ 直接提交给队长（不用发微信）';
    if (res.ok) { toast('已提交给队长 ✅ 不用再发微信了（他想导入时在收件箱里就能看到）', 9000); }
    else { toast('直接提交没成功：' + res.error + '。已改用分享/复制，一样能交给队长', 11000); }
  };

  const sh = $('#btnShare');
  if (sh) sh.onclick = async () => {""",
    '③b 上报页直传逻辑')

# ③c 资料页直传
rep("""      <button class="btn" id="meShare" ${d.name ? '' : 'disabled'}>📤 直接发给队长</button>""",
    """      ${relayCfg() ? `<button class="btn" id="meSend" ${d.name ? '' : 'disabled'}>⚡ 直接提交给队长（不用发微信）</button>` : ''}
      <button class="btn ${relayCfg() ? 'ghost' : ''}" id="meShare" ${d.name ? '' : 'disabled'}>📤 发给队长（微信）</button>""",
    '③c 资料页加直传键')

rep("""  const sh2 = $('#meShare');
  if (sh2) sh2.onclick = async () => {""",
    """  const sd2 = $('#meSend');
  if (sd2) sd2.onclick = async () => {
    sd2.disabled = true; sd2.textContent = '提交中…';
    const d3 = save();
    const res = await postToRelay('member', d3);
    sd2.disabled = false; sd2.textContent = '⚡ 直接提交给队长（不用发微信）';
    if (res.ok) toast('资料已提交给队长 ✅（含照片）', 9000);
    else toast('直接提交没成功：' + res.error + '。已改用分享/复制，一样能交给队长', 11000);
  };

  const sh2 = $('#meShare');
  if (sh2) sh2.onclick = async () => {""",
    '③d 资料页直传逻辑')

# ④a 队长同步面板：中转地址 + 口令
rep("""      <button class="btn ghost" id="btnTokenCheck">检查令牌权限（只看不改）</button>""",
    """      <button class="btn ghost" id="btnTokenCheck">检查令牌权限（只看不改）</button>
    </div>
    <div class="tiny" style="margin:14px 0 6px;line-height:1.7">
      <b>收件中转（队员"直接提交"用，可选）</b>：照 云端中转/scf/部署说明.txt 把云函数建好后，
      把它的访问地址和队伍口令填在这里 → 保存设置 → 同步，队员端就会出现「⚡ 直接提交给队长」。
      地址和口令不含任何令牌，可以放心同步。
    </div>
    <div class="grid2">
      <div class="field"><label>收件服务地址</label><input id="rlUrl" value="${esc((ov().relay && ov().relay.url) || '')}" placeholder="https://xxx.apigw.tencentcs.com/release/"></div>
      <div class="field"><label>队伍口令</label><input id="rlCode" value="${esc((ov().relay && ov().relay.code) || '')}" placeholder="自己起一个，告诉队员"></div>
    </div>
    <div class="chips" style="margin-top:8px"><button class="btn ghost" id="btnRelaySave">保存收件设置</button>
      <button class="btn ghost" id="btnRelayTest">测试收件服务</button>
      <span class="tiny">测试只发一条"连接测试"，队长可在收件箱里丢掉</span>""",
    '④a 同步面板加中转设置')

rep("""  const bChk = $('#btnTokenCheck');
  if (bChk) bChk.onclick = checkToken;""",
    """  const bChk = $('#btnTokenCheck');
  if (bChk) bChk.onclick = checkToken;

  const rSv = $('#btnRelaySave');
  if (rSv) rSv.onclick = () => {
    const l = ovLocal();
    const url = ($('#rlUrl') || {}).value ? $('#rlUrl').value.trim() : '';
    const code = ($('#rlCode') || {}).value ? $('#rlCode').value.trim() : '';
    if (!url) { delete l.relay; } else { l.relay = { url: url, code: code }; }
    saveLocalOv();
    toast(url ? '已保存收件设置（记得点「同步我的修改到线上」队员端才会生效）' : '已清空收件设置', 9000);
  };
  const rTs = $('#btnRelayTest');
  if (rTs) rTs.onclick = async () => {
    rTs.disabled = true; rTs.textContent = '测试中…';
    const l = ovLocal();
    const url = ($('#rlUrl') || {}).value ? $('#rlUrl').value.trim() : '';
    const code = ($('#rlCode') || {}).value ? $('#rlCode').value.trim() : '';
    l.relay = { url: url, code: code }; saveLocalOv();
    const res = await postToRelay('scores', { date: todayStr(), rows: [{ name: '连接测试', event: '5000米', fmt: '20:00', date: todayStr(), meet: '中转测试' }] });
    rTs.disabled = false; rTs.textContent = '测试收件服务';
    toast(res.ok ? '收件服务正常 ✅ 手机上也能直接提交了（这条测试去收件箱丢掉即可）' : ('收件服务不通：' + res.error), 12000);
  };""",
    '④b 中转设置交互')

# ④c 上传页加收件箱
rep("""  <div class="card sec">
    <div class="sec-head"><h2>${rep ? '我填的成绩（'""",
    """  ${batch ? `
  <div class="card sec">
    <h2>① 收件箱（队员直接提交的）</h2>
    <div class="tiny" style="margin-bottom:8px">队员在收集页点「⚡ 直接提交给队长」的内容都在这儿（存在仓库 data/inbox/）。
      <b>接收</b>后就写进你的本机，再去「数据管理 → 比赛成绩 / 队员名册」同步上线；<b>丢弃</b>会把这条从收件箱删掉。</div>
    <div class="chips"><button class="btn ghost" id="btnInboxLoad">读取收件箱</button>
      <span class="tiny">${relayCfg() ? '收件服务已配置' : '（还没配收件服务：去「数据管理 → 同步」填一次）'}</span></div>
    <div id="inboxArea"></div>
  </div>` : ''}

  <div class="card sec">
    <div class="sec-head"><h2>${rep ? '我填的成绩（'""",
    '④c 上传页加收件箱')

rep("""  const pg = $('#btnPasteGo');""",
    """  const ibl = $('#btnInboxLoad');
  if (ibl) ibl.onclick = loadInbox;

  const pg = $('#btnPasteGo');""",
    '④d 绑定读取收件箱')

# ⑤ 收件箱渲染 + 接收
rep("""/* --------------------------------------------- 数据管理交互（队长版） */""",
    """/* ---------------- 收件箱（队员直传的内容，接收后写入本机） ---------------- */

let inboxItems = null;

async function loadInbox() {
  const box = $('#inboxArea');
  if (!box) return;
  const cfg = ghCfg();
  if (!cfg.token) {
    box.innerHTML = '<div class="notice" style="margin-top:12px">先配好访问令牌（上面「数据管理 → 同步」），才能读取收件箱。</div>';
    return;
  }
  box.innerHTML = '<div class="tiny" style="margin-top:12px">正在读取收件箱…</div>';
  try {
    const list = await ghList(cfg, 'data/inbox');
    const files = (list || []).filter(f => f && f.type === 'file' && /\\.json$/.test(f.name));
    files.sort((a, b) => a.name < b.name ? 1 : -1);            // 新的在前
    const items = [];
    for (const f of files.slice(0, 30)) {
      try {
        const txt = await ghGetText(cfg, f.path);
        const j = JSON.parse(txt);
        items.push({ path: f.path, sha: f.sha, id: j.id || f.name, at: j.at || '', type: j.type || '', data: j.data || {} });
      } catch (e) { /* 单个读不了就跳过 */ }
    }
    inboxItems = items;
    renderInbox();
  } catch (e) {
    box.innerHTML = '<div class="notice" style="margin-top:12px">读取失败：' + esc(String((e && e.message) || e)) + '</div>';
  }
}

function inboxSummary(it) {
  if (it.type === 'maitian-member') {
    const pb = it.data.pb || {};
    const keys = Object.keys(pb);
    return '队员资料 · ' + esc(it.data.name || '') + (keys.length ? '（' + keys.map(k => esc(k) + ' ' + esc(pb[k])).join('、') + '）' : '')
      + (it.data.photo ? ' · 含照片' : '');
  }
  const rows = (it.data.rows || []);
  const names = rows.slice(0, 3).map(r => esc(r.name)).join('、');
  return '成绩 · ' + rows.length + ' 条：' + names + (rows.length > 3 ? ' 等' : '');
}

function renderInbox() {
  const box = $('#inboxArea');
  if (!box) return;
  const items = inboxItems || [];
  if (!items.length) { box.innerHTML = '<div class="empty" style="margin-top:12px">收件箱是空的</div>'; return; }
  box.innerHTML = `
    <div class="tiny" style="margin:12px 0 8px">待接收 <b>${items.length}</b> 条</div>
    ${items.map((it, i) => `<div class="comp-row" style="cursor:default">
      <div class="l"><div class="t">${inboxSummary(it)}</div>
        <div class="tiny">${esc(String(it.at || '').replace('T', ' ').slice(0, 16))}${it.type === 'maitian-member' ? ' <span class="tagbadge green">资料</span>' : ' <span class="tagbadge wheat">成绩</span>'}</div></div>
      <div style="display:flex;gap:8px;flex:0 0 auto">
        <button class="btn sm" data-inboxok="${i}">接收</button>
        <button class="btn flat sm" data-inboxdel="${i}">丢弃</button>
      </div></div>`).join('')}`;
  $$('[data-inboxok]').forEach(b => b.onclick = () => acceptInbox(+b.dataset.inboxok));
  $$('[data-inboxdel]').forEach(b => b.onclick = () => dropInbox(+b.dataset.inboxdel));
}

async function acceptInbox(i) {
  const it = (inboxItems || [])[i];
  if (!it) return;
  const cfg = ghCfg();
  if (it.type === 'maitian-member') {
    const r = await applyMemberDoc(it.data);
    if (r) toast('已接收「' + r.name + '」的资料：信息 ' + r.info + ' 项、成绩 ' + r.pbs + ' 条' + r.photoNote, 11000);
  } else {
    const rows = (it.data.rows || []).map(r => ({
      uid: newUid(), name: r.name, event: r.event || '5000米',
      sec: r.sec || secFromCell(r.fmt) || 0, fmt: r.fmt || fmtSec(r.sec || 0),
      date: r.date || it.data.date || '', meet: r.meet || '', rank: r.rank || '', ts: Date.now(),
    })).filter(r => r.name && r.sec);
    addMyResults(rows);
    toast('已接收 ' + rows.length + ' 条成绩（在下面「我录入的成绩」里，接着并进某场比赛）', 11000);
  }
  try { if (cfg.token) await ghDelete(cfg, it.path, '接收上报 ' + it.id); } catch (e) { toast('接收了，但收件箱里的这条没删掉：' + String((e && e.message) || e), 9000); }
  inboxItems.splice(i, 1);
  renderInbox(); render();
}

async function dropInbox(i) {
  const it = (inboxItems || [])[i];
  if (!it) return;
  if (!confirm('丢掉这条上报？（会从收件箱里删掉）')) return;
  try { await ghDelete(ghCfg(), it.path, '丢弃上报 ' + it.id); } catch (e) { toast('删不掉：' + String((e && e.message) || e), 9000); return; }
  inboxItems.splice(i, 1); renderInbox(); toast('已丢掉');
}

/* --------------------------------------------- 数据管理交互（队长版） */""",
    '⑤ 收件箱逻辑')

io.open(P, 'wb').write(s.replace('\n', '\r\n').encode('utf-8'))
print('\n'.join('   ' + d for d in done))
