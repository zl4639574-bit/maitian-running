# -*- coding: utf-8 -*-
"""B 补丁：队员名册收集（信息 + 各距离最好成绩 + 个人照片）
   ① 上报页新增「完善我的资料」tab（队员填，800米~全马，没有填「无」）
   ② 导出：可复制的资料文本 + 含照片的资料文件（.json）
   ③ 队长版「队员名册」新增「导入队员资料」：信息写入名册、最好成绩进个人最好成绩榜、照片上传成头像
   ④ 展示版名册显示头像，没上传的用队徽
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


# ── ① 上报页加第二个 tab ──
rep("""  report:  [['upload', '成绩上报']],          // 队员成绩收集页：只填 + 导出，不需要令牌""",
    """  report:  [['upload', '成绩上报'], ['me', '完善我的资料']],   // 队员收集页：填 + 导出，不需要令牌""",
    '①a TABS 加「完善我的资料」')

rep("""                manage: renderManage, photos: renderPhotos, about: renderAbout };""",
    """                manage: renderManage, photos: renderPhotos, about: renderAbout, me: renderMe };""",
    '①b 路由 map 加 me')

rep("""  if (state.tab === 'upload') bindUpload();""",
    """  if (state.tab === 'upload') bindUpload();
  if (state.tab === 'me') bindMe();""",
    '①c 绑定 bindMe')

# ── ② 收集页 ──
rep("""/* ---------------- 赛事名匹配（上报时自动对到已有赛事）---------------- */""",
    """/* ---------------- 队员「完善我的资料」收集页 ---------------- */

const ME_PB = ['800米', '1500米', '3000米', '5000米', '10000米', '半马', '全马'];
const LS_ME = 'mt_me_v1';

function meDraft() {
  try { return JSON.parse(lsGet(LS_ME) || '{}') || {}; } catch (e) { return {}; }
}
function saveMeDraft(d) { lsSet(LS_ME, d); }

/** 资料文本（队长能直接粘贴导入） */
function meText(d) {
  const pb = d.pb || {};
  const lines = ['#麦田守望 队员资料',
    '姓名\\t' + (d.name || ''),
    '性别\\t' + (d.sex || ''),
    '学院\\t' + (d.college || ''),
    '专业\\t' + (d.major || ''),
    '年级\\t' + (d.grade || '')];
  ME_PB.forEach(ev => { lines.push(ev + '\\t' + ((pb[ev] || '').trim() || '无')); });
  lines.push('照片\\t' + (d.photo ? '（在导出的资料文件里）' : '无'));
  return lines.join('\\n');
}

function renderMe() {
  const d = meDraft();
  const pb = d.pb || {};
  const names = rosterList().map(m => m.name);
  const inRoster = d.name && names.indexOf(d.name) >= 0;
  return `
  <div class="sec-head"><h1>完善我的资料</h1>
    ${d.name ? `<button class="btn ghost sm" data-go="upload">去上报成绩 →</button>` : ''}</div>

  <div class="notice" style="margin-bottom:16px">
    <b>填完怎么交给队长</b><br>
    ① 把下面填好（最好成绩没有的就填「无」）；② 点「复制资料文本」或「导出资料文件（含照片）」；<br>
    ③ 发给队长，队长会把它写进队员名册和成绩榜。<br>
    <span class="tiny">不用登录、不会自动上传；照片只在你自己手机上，随资料文件发给队长。</span>
  </div>

  <div class="card sec">
    <h2>① 基本信息</h2>
    <div class="grid2" style="margin-bottom:14px">
      <div class="field"><label>姓名 *</label><input id="me_name" value="${esc(d.name || '')}" list="meNameList" placeholder="例如 张津浩">
        <datalist id="meNameList">${names.map(n => `<option value="${esc(n)}">`).join('')}</datalist>
        <div class="tiny" style="margin-top:4px">${d.name ? (inRoster ? '✅ 在名册里，队长会更新你的资料' : '❓ 名册里还没有这个名字，队长会新增一位') : '开始输入姓名'}</div>
      </div>
      <div class="field"><label>性别</label><select id="me_sex">
        ${['', '男', '女'].map(v => `<option value="${v}" ${(d.sex || '') === v ? 'selected' : ''}>${v || '未填'}</option>`).join('')}
      </select></div>
      <div class="field"><label>学院</label><input id="me_college" value="${esc(d.college || '')}" placeholder="例如 林学院"></div>
      <div class="field"><label>专业 / 班级</label><input id="me_major" value="${esc(d.major || '')}" placeholder="例如 林学 2301"></div>
      <div class="field"><label>年级</label><input id="me_grade" value="${esc(d.grade || '')}" placeholder="例如 2023"></div>
    </div>

    <h2 style="margin-top:6px">② 个人最好成绩（没有就填「无」）</h2>
    <div class="tiny" style="margin-bottom:10px">从 800 米到全马，跑过的就填最好一次（如 2:15、18:35、1:23:29）；没跑过的填「无」。</div>
    <div class="grid2">
      ${ME_PB.map(ev => `<div class="field"><label>${esc(ev)}</label>
        <div style="display:flex;gap:6px">
          <input id="me_pb_${esc(ev)}" value="${esc(pb[ev] || '')}" placeholder="无 / 成绩" style="flex:1">
          <button class="btn flat sm" data-menone="${esc(ev)}" style="white-space:nowrap">无</button>
        </div></div>`).join('')}
    </div>

    <h2 style="margin-top:18px">③ 个人照片（可选）</h2>
    <div class="tiny" style="margin-bottom:10px">选一张正脸照，会自动压小；没上传的，名册里先用队徽显示。</div>
    <div class="drop" id="mePhotoDrop">
      <div class="big">🖼</div>
      <div><b>点这里选照片</b>（手机可以从相册选）</div>
      <div class="tiny" style="margin-top:6px">jpg / png / heic 截图都行，会压到 360px 左右</div>
      <input type="file" id="mePhotoFile" accept="image/*" style="display:none">
    </div>
    ${d.photo ? `<div style="margin-top:12px;display:flex;align-items:center;gap:12px">
      <img class="avatar" style="width:72px;height:72px" src="${esc(d.photo)}">
      <button class="btn danger sm" id="mePhotoDel">删除照片</button></div>` : ''}

    <div class="chips" style="margin-top:20px">
      <button class="btn" id="meSave">保存资料</button>
      <button class="btn ghost" id="meCopy" ${d.name ? '' : 'disabled'}>复制资料文本</button>
      <button class="btn ghost" id="meExport" ${d.name ? '' : 'disabled'}>导出资料文件（含照片）</button>
    </div>
    <div class="tiny" style="margin-top:8px">「资料文件」是一个 .json 小文件，里面连照片一起打包，队长选这个文件就能一次导入。</div>
  </div>`;
}

function bindMe() {
  const g = id => { const el = $(id); return el ? el.value.trim() : ''; };
  const collect = () => {
    const d = meDraft();
    const pb = {};
    ME_PB.forEach(ev => { pb[ev] = g('#me_pb_' + ev); });
    return Object.assign({}, d, {
      type: 'maitian-member', name: g('#me_name'), sex: g('#me_sex'),
      college: g('#me_college'), major: g('#me_major'), grade: g('#me_grade'),
      pb: pb, updated: new Date().toISOString(),
    });
  };
  const save = () => { saveMeDraft(collect()); return meDraft(); };

  $$('[data-menone]').forEach(b => b.onclick = () => {
    const el = $('#me_pb_' + b.dataset.menone);
    if (el) el.value = '无';
    toast('已填「无」');
  });
  const sv = $('#meSave');
  if (sv) sv.onclick = () => { const d = save(); toast('已保存到本机：' + (d.name || '（还没填姓名）'), 5000); render(); };
  const cp = $('#meCopy');
  if (cp) cp.onclick = () => { copyText(meText(save())); toast('资料文本已复制，粘给队长即可', 6000); };
  const ex = $('#meExport');
  if (ex) ex.onclick = () => {
    const d = save();
    download('麦田守望_我的资料_' + (d.name || '未填') + '.json', JSON.stringify(d, null, 1));
    toast('已导出，把这个文件发给队长', 6000);
  };
  const drop = $('#mePhotoDrop'), fi = $('#mePhotoFile');
  if (drop && fi) {
    drop.onclick = () => fi.click();
    fi.onchange = () => { if (fi.files[0]) shrinkPhoto(fi.files[0]); };
  }
  const pd = $('#mePhotoDel');
  if (pd) pd.onclick = () => { const d = meDraft(); delete d.photo; saveMeDraft(d); toast('已删除照片'); render(); };

  const nm = $('#me_name');
  if (nm) nm.onblur = () => { const d = save(); if (d.name) render(); };
}

/** 照片压到 360px、JPEG 0.82，存成 dataURL（几十 KB） */
function shrinkPhoto(file) {
  const fr = new FileReader();
  fr.onload = () => {
    const img = new Image();
    img.onload = () => {
      const max = 360;
      const sc = Math.min(1, max / Math.max(img.width, img.height));
      const cv = document.createElement('canvas');
      cv.width = Math.round(img.width * sc); cv.height = Math.round(img.height * sc);
      cv.getContext('2d').drawImage(img, 0, 0, cv.width, cv.height);
      const url = cv.toDataURL('image/jpeg', 0.82);
      const d = meDraft();
      d.photo = url;
      saveMeDraft(d);
      toast('照片已就绪（' + Math.round(url.length / 1024) + ' KB），记得点「保存资料」', 6000);
      render();
    };
    img.onerror = () => toast('这张图读不了，换一张试试');
    img.src = fr.result;
  };
  fr.readAsDataURL(file);
}

/* ---------------- 赛事名匹配（上报时自动对到已有赛事）---------------- */""",
    '②a 收集页 renderMe/bindMe/shrinkPhoto')

# ── ③ 队长版：导入队员资料 ──
rep("""function addCompRecords(compId, recs) {""",
    """/* ---------------- 队员资料导入（队长版）---------------- */

/** 文件名用名字的哈希，避免中文文件名 */
function avatarPathFor(name) {
  let h = 0;
  const t = String(name || '');
  for (let i = 0; i < t.length; i++) { h = (h * 31 + t.charCodeAt(i)) % 1000000007; }
  return 'images/avatars/m' + h.toString(36) + '.jpg';
}

function parseMemberDoc(text) {
  const t = String(text || '').trim();
  const out = { pb: {} };
  if (t.charAt(0) === '{') {
    try {
      const j = JSON.parse(t);
      if (j && (j.type === 'maitian-member' || j.name)) return j;
    } catch (e) { /* 不是 JSON 就按文本解析 */ }
  }
  t.split(/\\r?\\n/).forEach(line => {
    const s2 = line.replace(/^#.*$/, '').trim();
    if (!s2) return;
    const p = s2.split(/[\\t:：]+/).map(x => x.trim());
    if (p.length < 2) return;
    const k = p[0], v = p.slice(1).join(' ').trim();
    if (k === '姓名' || k === '名字') out.name = v;
    else if (k === '性别') out.sex = v;
    else if (k === '学院') out.college = v;
    else if (k === '专业' || k === '专业班级') out.major = v;
    else if (k === '年级') out.grade = v;
    else if (ME_PB.indexOf(k) >= 0) out.pb[k] = v;
  });
  if (!out.name && !Object.keys(out.pb).length) return null;
  return out;
}

async function applyMemberDoc(doc) {
  if (!doc || !doc.name) return toast('这份资料里没有姓名，导入不了');
  const o = ovLocal();
  o.memberEdits = o.memberEdits || {};
  const e = o.memberEdits[doc.name] || {};
  ['sex', 'college', 'major', 'grade'].forEach(k => {
    const v = String(doc[k] || '').trim();
    if (v && v !== '无') e[k] = v;
  });
  // 照片：有令牌就直接传成仓库里的头像；没有就先存 dataURL（下次同步一起带上）
  let photoNote = '';
  if (doc.photo && /^data:image\\//.test(doc.photo)) {
    const cfg = ghCfg();
    const path = avatarPathFor(doc.name);
    if (cfg.token) {
      try {
        const b64 = doc.photo.split(',')[1];
        await ghPut(cfg, path, b64, '头像：' + doc.name);
        e.photo = path;
        photoNote = '，头像已上传';
      } catch (err) {
        e.photo = doc.photo;
        photoNote = '，头像暂时存在本机（' + String(err.message || err).slice(0, 40) + '）';
      }
    } else {
      e.photo = doc.photo;
      photoNote = '，头像先存本机（配好令牌后重新导入就会传上去）';
    }
  }
  o.memberEdits[doc.name] = e;
  saveLocalOv();

  // 最好成绩：非「无」的进个人最好成绩榜
  const pbs = doc.pb || {};
  const add = [];
  ME_PB.forEach(ev => {
    const v = String(pbs[ev] || '').trim();
    if (!v || v === '无' || v === '-') return;
    const sec = secFromCell(v);
    if (!sec) return;
    add.push({ uid: newUid(), name: doc.name, event: ev, sec: Math.round(sec * 10) / 10,
      fmt: fmtSec(sec), date: '', meet: '队员自报', rank: '', ts: Date.now(),
      sex: e.sex || '', college: e.college || '' });
  });
  if (add.length) {
    o.pbAdded = mergePbAdded(o.pbAdded || [], add);
    saveLocalOv();
  }
  return { name: doc.name, info: ['sex', 'college', 'major', 'grade'].filter(k => e[k]).length,
    pbs: add.length, photo: !!e.photo, photoNote: photoNote };
}

function renderMemberDocPreview() {
  const box = $('#docArea');
  if (!box) return;
  const d = memberDocQueue;
  if (!d) { box.innerHTML = ''; return; }
  const memNames = new Set(rosterList().map(m => m.name));
  const pbRows = Object.keys(d.doc.pb || {}).filter(k => d.doc.pb[k] && d.doc.pb[k] !== '无');
  box.innerHTML = `
    <div class="notice" style="margin-top:12px">
      <b>${esc(d.doc.name)}</b>　${memNames.has(d.doc.name) ? '<span class="tagbadge green">在名册里</span>' : '<span class="tagbadge">名册里没有 → 会新增一位</span>'}<br>
      信息：${['sex', 'college', 'major', 'grade'].filter(k => d.doc[k]).map(k => esc(d.doc[k])).join(' / ') || '（没填）'}<br>
      最好成绩：${pbRows.length ? pbRows.map(k => esc(k) + ' ' + esc(d.doc.pb[k])).join('　') : '（全填了无）'}<br>
      照片：${d.doc.photo ? '有（' + Math.round(String(d.doc.photo).length / 1024) + ' KB）' : '没有'}
    </div>
    <div class="chips" style="margin-top:10px">
      <button class="btn" id="btnDocApply">导入这份资料</button>
      <button class="btn flat sm" id="btnDocCancel">取消</button>
    </div>`;
  const a = $('#btnDocApply'), c2 = $('#btnDocCancel');
  if (c2) c2.onclick = () => { memberDocQueue = null; render(); };
  if (a) a.onclick = async () => {
    a.disabled = true; a.textContent = '导入中…';
    const r = await applyMemberDoc(d.doc);
    memberDocQueue = null;
    render();
    if (r) toast('已导入「' + r.name + '」：信息 ' + r.info + ' 项、最好成绩 ' + r.pbs + ' 条' + r.photoNote, 10000);
  };
}

let memberDocQueue = null;

function addCompRecords(compId, recs) {""",
    '③a 资料解析/应用函数')

# ── ④ 名册管理区（完善队员信息那一排）加导入入口 ──
rep("""        <button class="btn ghost" id="btnFillAll">列出名册全部 ${rosterList().length} 人</button>""",
    """        <button class="btn ghost" id="btnFillAll">列出名册全部 ${rosterList().length} 人</button>
        <button class="btn ghost" id="btnDocImport">＋ 导入队员资料（队员发来的文件）</button>
        <input type="file" id="docFile" accept=".json,.txt,.csv" style="display:none">
        <span class="tiny" style="flex-basis:100%">队员在「成绩上报 → 完善我的资料」里导出的 .json 小文件（连照片一起）直接选进来；
          队员发来的一段文字也可以粘在下面（每行「字段 值」，Tab 或冒号分隔，和导出的文本一致）。</span>
        <textarea class="ta" id="docText" rows="3" style="flex-basis:100%;width:100%"
          placeholder="姓名	张三&#10;性别	男&#10;学院	林学院&#10;专业	林学&#10;年级	2023&#10;5000米	18:35&#10;半马	无"></textarea>
        <button class="btn ghost" id="btnDocParse">解析这段文字</button>
        <div id="docArea" style="flex-basis:100%"></div>""",
    '④a 名册区加导入入口')

io.open(P, 'wb').write(s.replace('\n', '\r\n').encode('utf-8'))
print('\n'.join('   ' + d for d in done) if done else '(没有改动被写入)')
