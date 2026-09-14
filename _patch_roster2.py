# -*- coding: utf-8 -*-
"""名册：加「批量添加队员」——粘贴 Excel 行（Tab/逗号/空格分隔）或选 xlsx/csv，解析→预览→一次加入"""
import io

p = "assets/app.js"
s = io.open(p, encoding="utf-8", newline="").read().replace("\r\n", "\n")
orig = len(s)

# ── ① 名册分区：单条添加表单后面，加批量添加入口 ─────────────────────────────
old = r"""      <button class="btn" id="btnAddMember" style="margin-top:8px">添加到名册</button>
      <span class="tiny" style="margin-left:10px">添加完点「同步我的修改到线上」，全队名册立刻多这个人</span>
    </div>"""
new = r"""      <button class="btn" id="btnAddMember" style="margin-top:8px">添加到名册</button>
      <span class="tiny" style="margin-left:10px">添加完点「同步我的修改到线上」，全队名册立刻多这个人</span>
    </div>

    <div class="notice" style="margin-bottom:18px">
      <b>＋ 批量添加队员（一次加一批）</b>
      <div class="tiny" style="margin:8px 0">
        从 Excel / 微信表格里<b>复制几行直接粘到下面</b>（一行一个人）。列的默认顺序是
        <b>姓名、学院、专业、年级、性别、身份</b>；如果第一行是表头（含"姓名/学院/…"）会自动按表头认列。
        也可以点右边按钮选一个 Excel / CSV 文件。身份那列填「正式」或「预备」，空着按「正式」算。
      </div>
      <textarea class="ta" id="nmBatch" rows="5" placeholder="张伟&#9;林学院&#9;林学2101&#9;2023&#9;男&#9;正式&#10;李娜&#9;园艺学院&#9;园艺2102&#9;2023&#9;女&#9;预备"></textarea>
      <div class="chips" style="margin-top:10px">
        <button class="btn" id="btnNmPreview">解析并预览</button>
        <button class="btn ghost" id="btnNmFile">选 Excel / CSV 文件</button>
        <input type="file" id="nmFileInput" accept=".xlsx,.xls,.csv" style="display:none">
      </div>
      <div id="nmBatchBox"></div>
    </div>"""
assert s.count(old) == 1, "① 批量区 HTML"
s = s.replace(old, new)

# ── ② 新增队员排在名册列表最前面（一加就看得见）─────────────────────────────
old = r"""  const addedList = (o.newMembers || []).filter(m => !state.mRosterQ || m.name.includes(state.mRosterQ));
  const editList = ros.filter(m => !hiddenSet.has(m.name)).filter(m => state.mRosterQ
    ? m.name.includes(state.mRosterQ) : (m.level || []).some(l => l === '正式' || l === '预备')).slice(0, 60)
    .map(m => Object.assign({}, m, { _isNew: false }))
    .concat(addedList.map(m => Object.assign({}, m, { _isNew: true })));"""
new = r"""  const addedList = (o.newMembers || []).filter(m => !state.mRosterQ || m.name.includes(state.mRosterQ));
  const editList = addedList.map(m => Object.assign({}, m, { _isNew: true }))
    .concat(ros.filter(m => !hiddenSet.has(m.name)).filter(m => state.mRosterQ
      ? m.name.includes(state.mRosterQ) : (m.level || []).some(l => l === '正式' || l === '预备')).slice(0, 60)
      .map(m => Object.assign({}, m, { _isNew: false })));"""
assert s.count(old) == 1, "② editList 排序"
s = s.replace(old, new)

# ── ③ 解析 / 预览 / 入库 三个函数 ───────────────────────────────────────────
old = r"""function bindManage() {"""
new = r"""/* ---------------- 批量添加队员：粘贴表格或选文件 → 解析预览 → 一次入库 ---------------- */

let nmBatchRows = null;
const NM_COLS = [['name', /姓名|名字|人员|队员/], ['college', /学院|院系/], ['major', /专业|班级/],
                 ['grade', /年级|入学|届/], ['sex', /性别/], ['level', /身份|级别|状态/]];

function parseRosterText(txt) {
  const lines = String(txt || '').split(/\r?\n/).map(x => x.trim()).filter(Boolean);
  if (!lines.length) return { rows: [], skip: [] };
  const splitLine = (l) => l.indexOf('\t') >= 0 ? l.split('\t')
                        : (l.indexOf(',') >= 0 || l.indexOf('，') >= 0 ? l.split(/[,，]/) : l.split(/\s+/));
  let rows = lines.map(splitLine);
  const head = rows[0].map(x => String(x).trim());
  let map;
  if (/姓名|名字|人员|队员/.test(head.join(' '))) {          // 第一行是表头 → 按表头认列
    map = {};
    NM_COLS.forEach(([k, re]) => { const i = head.findIndex(h => re.test(h)); if (i >= 0) map[k] = i; });
    rows = rows.slice(1);
  } else {                                                   // 没表头 → 用默认顺序
    map = { name: 0, college: 1, major: 2, grade: 3, sex: 4, level: 5 };
  }
  const out = [], skip = [], seen = new Set(rosterList().map(m => m.name));
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
  return { rows: out, skip };
}

function renderNmBatch() {
  const box = $('#nmBatchBox');
  if (!box) return;
  const data = nmBatchRows || { rows: [], skip: [] };
  if (!data.rows.length) {
    box.innerHTML = '<div class="notice" style="margin-top:12px">没解析出可用的人'
      + (data.skip.length ? '：' + esc(data.skip.slice(0, 3).join('；')) + (data.skip.length > 3 ? ' 等' : '') : '')
      + '。检查一下粘贴的内容（至少要有一列姓名）。</div>';
    return;
  }
  box.innerHTML = `
    <div class="tiny" style="margin:12px 0 8px">
      解析出 <b>${data.rows.length}</b> 人${data.skip.length ? '；跳过 ' + data.skip.length + ' 条：' + esc(data.skip.slice(0, 3).join('；')) + (data.skip.length > 3 ? ' 等' : '') : ''}
      ${ghCfg().token ? '。点下面按钮一次加入，再去「同步」发布。' : '。点下面按钮加入本机，然后去「同步」配好令牌再发布。'}
    </div>
    <div class="tbl-wrap" style="max-height:300px;overflow:auto">
      <table class="tbl" style="min-width:auto"><thead><tr>
        <th class="no-sort">姓名</th><th class="no-sort hide-sm">学院</th><th class="no-sort hide-sm">专业</th>
        <th class="no-sort hide-sm">年级</th><th class="no-sort hide-sm">性别</th><th class="no-sort">身份</th>
      </tr></thead><tbody>
      ${data.rows.slice(0, 80).map(r => `<tr><td><b>${esc(r.name)}</b></td>
        <td class="tiny hide-sm">${esc(r.college)}</td><td class="tiny hide-sm">${esc(r.major)}</td>
        <td class="tiny hide-sm">${esc(r.grade)}</td><td class="tiny hide-sm">${esc(r.sex)}</td>
        <td class="tiny">${esc(r.level.join('+'))}</td></tr>`).join('')}
      </tbody></table>
    </div>
    <div class="chips" style="margin-top:12px">
      <button class="btn" id="btnNmConfirm">把这 ${data.rows.length} 人加入名册</button>
      <button class="btn ghost" id="btnNmCancel">取消</button>
    </div>`;
  const ok = $('#btnNmConfirm'), no = $('#btnNmCancel');
  if (no) no.onclick = () => { nmBatchRows = null; render(); };
  if (ok) ok.onclick = () => {
    const l = ovLocal();
    l.newMembers = l.newMembers || [];
    let added = 0, dup = 0;
    data.rows.forEach(r => {
      if (l.newMembers.some(m => m.name === r.name) || (BASE.roster || []).some(m => m.name === r.name)) { dup++; return; }
      l.newMembers.push(r); added++;
    });
    saveLocalOv();
    nmBatchRows = null;
    state.mRosterQ = '';
    toast('已把 ' + added + ' 人加进名册' + (dup ? '（' + dup + ' 人已在名册里，跳过）' : '')
          + ' —— 记得点「同步我的修改到线上」发布', 10000);
    render();
  };
}

function bindManage() {"""
assert s.count(old) == 1, "③ 批量函数插入"
s = s.replace(old, new)

# ── ④ 事件：解析按钮 / 选文件 ───────────────────────────────────────────────
old = r"""    saveLocalOv();
    toast('已把 ' + name + ' 加进名册 —— 记得点「同步我的修改到线上」发布', 7000);
    render();
  };"""
new = r"""    saveLocalOv();
    toast('已把 ' + name + ' 加进名册 —— 记得点「同步我的修改到线上」发布', 7000);
    render();
  };
  const nbp = $('#btnNmPreview');
  if (nbp) nbp.onclick = () => {
    nmBatchRows = parseRosterText($('#nmBatch').value);
    renderNmBatch();
  };
  const nbf = $('#btnNmFile'), nbfi = $('#nmFileInput');
  if (nbf && nbfi) {
    nbf.onclick = () => nbfi.click();
    nbfi.onchange = () => {
      const f = nbfi.files && nbfi.files[0];
      if (!f) return;
      const fr = new FileReader();
      fr.onerror = () => toast('文件读不出来，换一个试试', 8000);
      fr.onload = () => {
        try {
          const wb = XLSX.read(new Uint8Array(fr.result), { type: 'array' });
          const ws = wb.Sheets[wb.SheetNames[0]];
          const aoa = XLSX.utils.sheet_to_json(ws, { header: 1, raw: false, defval: '' });
          const txt = aoa.map(r => r.map(c => String(c == null ? '' : c).trim()).join('\t')).join('\n');
          $('#nmBatch').value = txt.slice(0, 30000);
          nmBatchRows = parseRosterText(txt);
          renderNmBatch();
        } catch (e) {
          toast('这个文件读不出来：' + String((e && e.message) || e).slice(0, 40), 9000);
        }
      };
      fr.readAsArrayBuffer(f);
    };
  }"""
assert s.count(old) == 1, "④ 批量事件"
s = s.replace(old, new)

io.open(p, "w", encoding="utf-8", newline="\r\n").write(s)
print("app.js 批量添加补丁完成: %d -> %d 字符" % (orig, len(s)))
