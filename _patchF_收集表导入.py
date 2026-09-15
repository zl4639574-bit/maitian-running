# -*- coding: utf-8 -*-
"""F 补丁：收集表（腾讯文档/问卷星导出的 Excel/CSV）批量导入队员资料
   一行一个人；列名认 姓名/性别/学院/专业/年级/800米…；自动忽略「提交时间/填写人」等无关列
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


# ① 名册区加按钮 + 文件输入 + 预览区
rep("""        <button class="btn ghost" id="btnDocImport">＋ 导入队员资料（队员发来的文件）</button>""",
    """        <button class="btn ghost" id="btnDocImport">＋ 导入队员资料（队员发来的文件）</button>
        <button class="btn ghost" id="btnDocSheet">＋ 导入收集表（Excel/CSV，一行一个人）</button>
        <input type="file" id="docSheetFile" accept=".xlsx,.xls,.csv" style="display:none">
        <span class="tiny" style="flex-basis:100%">收集表（腾讯文档 / 问卷星 等）导出的 Excel 直接选进来就行：
          列名认「姓名 / 性别 / 学院 / 专业 / 年级 / 800米 / 1500米 / 3000米 / 5000米 / 10000米 / 半马 / 全马」，
          「提交时间」「填写人」之类的列会自动忽略；没有的距离填「无」即可。</span>
        <div id="docSheetArea" style="flex-basis:100%"></div>""",
    '①a 名册区加收集表导入入口')

# ② 解析 + 预览 + 批量导入
rep("""function renderMemberDocPreview() {""",
    """/** 收集表（一行一个人）→ 多份队员资料 */
function parseMemberSheet(rows) {
  if (!rows || !rows.length) return { docs: [], skip: ['文件是空的'] };
  let hIdx = -1;
  for (let i = 0; i < Math.min(rows.length, 8); i++) {
    const line = (rows[i] || []).map(c => String(c == null ? '' : c));
    if (line.some(c => /姓名|名字/.test(c))) { hIdx = i; break; }
  }
  if (hIdx < 0) return { docs: [], skip: ['没找到表头行（要有一列叫「姓名」）'] };
  const head = (rows[hIdx] || []).map(c => String(c == null ? '' : c).trim());
  const colOf = re => { for (let c = 0; c < head.length; c++) if (re.test(head[c])) return c; return -1; };
  const cName = colOf(/姓名|名字/), cSex = colOf(/性别/), cCol = colOf(/学院|院系/),
    cMaj = colOf(/专业/), cGrd = colOf(/年级/);
  const pbCols = {};
  ME_PB.forEach(ev => { for (let c = 0; c < head.length; c++) if (head[c].indexOf(ev) >= 0) { pbCols[ev] = c; break; } });
  const docs = [], skip = [];
  rows.slice(hIdx + 1).forEach((r, i) => {
    if (!r || !r.some(c => c !== '' && c != null)) return;
    const g = c => (c >= 0 && r[c] != null) ? String(r[c]).trim() : '';
    const name = g(cName).replace(/[（(].*?[)）]/g, '').replace(/\\s+/g, '');
    if (!/^[\\u4e00-\\u9fa5·a-zA-Z][\\u4e00-\\u9fa5·a-zA-Z0-9]{1,13}$/.test(name)) { skip.push('第 ' + (hIdx + 2 + i) + ' 行：姓名「' + g(cName).slice(0, 8) + '」看不懂'); return; }
    const pb = {};
    ME_PB.forEach(ev => { const v = g(pbCols[ev]); pb[ev] = v || '无'; });
    docs.push({ type: 'maitian-member', name: name, sex: g(cSex), college: g(cCol),
      major: g(cMaj), grade: g(cGrd), pb: pb, source: '收集表' });
  });
  return { docs: docs, skip: skip };
}

let docSheetQueue = null;

function renderSheetPreview() {
  const box = $('#docSheetArea');
  if (!box) return;
  const q = docSheetQueue;
  if (!q) { box.innerHTML = ''; return; }
  const mem = new Set(rosterList().map(m => m.name));
  const shown = q.docs.slice(0, 12);
  box.innerHTML = `
    <div class="notice" style="margin-top:12px">
      收集表里读到 <b>${q.docs.length}</b> 个人${q.skip.length ? '，跳过 ' + q.skip.length + ' 行' + (q.skip.length ? '（' + esc(q.skip.slice(0, 3).join('；')) + '）' : '') : ''}；
      其中 <b>${q.docs.filter(d => !mem.has(d.name)).length}</b> 位名册里没有（会新增）。
    </div>
    <div class="tbl-wrap" style="max-height:240px;overflow:auto;margin-top:10px">
      <table class="tbl" style="min-width:auto">
        <thead><tr><th class="no-sort">姓名</th><th class="no-sort hide-sm">性别</th>
          <th class="no-sort hide-sm">学院</th><th class="no-sort">会有成绩项</th><th class="no-sort">在名册</th></tr></thead>
        <tbody>${shown.map(d => {
          const pbs = ME_PB.filter(ev => d.pb[ev] && d.pb[ev] !== '无');
          return `<tr><td><b>${esc(d.name)}</b></td><td class="tiny hide-sm">${esc(d.sex || '')}</td>
            <td class="tiny hide-sm">${esc(d.college || '')}</td>
            <td class="tiny">${pbs.length ? pbs.map(ev => esc(ev) + ' ' + esc(d.pb[ev])).join('、') : '（全填无）'}</td>
            <td>${mem.has(d.name) ? '<span class="tagbadge green">在</span>' : '<span class="tagbadge">新增</span>'}</td></tr>`;
        }).join('')}</tbody>
      </table>
    </div>
    ${q.docs.length > 12 ? `<div class="tiny">（只预览前 12 位，导入时会全部处理）</div>` : ''}
    <div class="chips" style="margin-top:12px">
      <button class="btn" id="btnSheetDo">全部导入这 ${q.docs.length} 位</button>
      <button class="btn flat sm" id="btnSheetCancel">取消</button>
    </div>`;
  const no = $('#btnSheetCancel'), ok = $('#btnSheetDo');
  if (no) no.onclick = () => { docSheetQueue = null; render(); };
  if (ok) ok.onclick = async () => {
    ok.disabled = true; ok.textContent = '导入中…';
    let added = 0, updated = 0, pbs = 0;
    for (const d of q.docs) {
      const before = (ovLocal().memberEdits || {})[d.name];
      const r = await applyMemberDoc(d);
      if (r) { pbs += r.pbs || 0; if (before) updated++; else added++; }
    }
    docSheetQueue = null;
    toast('收集表导入完成：名册更新 ' + updated + ' 人、新增 ' + added + ' 人、最好成绩 ' + pbs + ' 条。'
      + '记得点「同步我的修改到线上」', 12000);
    render();
  };
}

/** 读收集表文件（Excel/CSV）→ 预览 */
function readSheetFile(file) {
  const isCsv = /\\.csv$/i.test(file.name || '');
  const fr = new FileReader();
  fr.onload = (e) => {
    try {
      const buf = new Uint8Array(e.target.result);
      let wb;
      if (isCsv) {
        let txt;
        try { txt = new TextDecoder('utf-8', { fatal: true }).decode(buf); }
        catch (err) { try { txt = new TextDecoder('gbk').decode(buf); } catch (e2) { txt = new TextDecoder('utf-8').decode(buf); } }
        wb = XLSX.read(txt.replace(/^\\ufeff/, ''), { type: 'string', raw: true });
      } else {
        wb = XLSX.read(buf, { type: 'array' });
      }
      const first = XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], { header: 1, raw: true, defval: '' });
      const r = parseMemberSheet(first);
      if (!r.docs.length) return toast('没读出行：' + (r.skip[0] || '检查一下表头有没有「姓名」列'), 9000);
      docSheetQueue = r;
      toast('已读取 ' + file.name + '：' + r.docs.length + ' 位，确认下面这份再点导入');
      renderSheetPreview();
    } catch (err) { toast('这个文件读不了：' + (err && err.message), 9000); }
  };
  fr.readAsArrayBuffer(file);
}

function renderMemberDocPreview() {""",
    '②a 解析/预览/导入函数')

# ③ 绑定
rep("""  const dF = $('#docFile'), dI = $('#btnDocImport');""",
    """  const sF = $('#docSheetFile'), sI = $('#btnDocSheet');
  if (sI && sF) sI.onclick = () => sF.click();
  if (sF) sF.onchange = () => { const f = sF.files[0]; sF.value = ''; if (f) readSheetFile(f); };

  const dF = $('#docFile'), dI = $('#btnDocImport');""",
    '③a 绑定收集表导入')

io.open(P, 'wb').write(s.replace('\n', '\r\n').encode('utf-8'))
print('\n'.join('   ' + d for d in done))
