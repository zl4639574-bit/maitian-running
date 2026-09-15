# -*- coding: utf-8 -*-
"""修两个导入真实坑：
   ① CSV 按 UTF-8 解码（失败回退 GBK）—— 否则微信里收到的成绩表中文名全变乱码
   ② 成绩单元格支持 Excel 时间格式（0.7326 = 17:35）和纯秒数（1022 = 17:02）
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


# ① CSV 解码 + 成绩解析函数
rep("""function readTableFile(file) {
  const r = new FileReader();
  r.onload = e => {
    try {
      const wb = XLSX.read(new Uint8Array(e.target.result), { type: 'array' });""",
    """/** 成绩单元格 → 秒。支持：17:35 / 1:23:29 / 18'35" / 18.5（分钟）
    / Excel 里存成时间格式（显示 17:35，实际值 0.7326）/ 直接是秒数（1022 = 17:02） */
function secFromCell(v) {
  const t = String(v == null ? '' : v).trim();
  if (t === '') return 0;
  if (/^\\d+(\\.\\d+)?$/.test(t)) {
    const n = parseFloat(t);
    if (n > 0 && n < 1) return Math.round(n * 86400);   // Excel 时间格式（一天的比例）
    if (n >= 60 && n <= 86400) return Math.round(n);    // 直接写秒数
  }
  return parseSec(v);
}

function readTableFile(file) {
  const isCsv = /\\.csv$/i.test(file.name || '');
  const r = new FileReader();
  r.onload = e => {
    try {
      const buf = new Uint8Array(e.target.result);
      let wb;
      if (isCsv) {
        // CSV：先按 UTF-8 解；乱码（微信/国内软件导出的 GBK 表）就改按 GBK 解
        let txt;
        try { txt = new TextDecoder('utf-8', { fatal: true }).decode(buf); }
        catch (err) {
          try { txt = new TextDecoder('gbk').decode(buf); }
          catch (e2) { txt = new TextDecoder('utf-8').decode(buf); }
        }
        wb = XLSX.read(txt.replace(/^\\ufeff/, ''), { type: 'string', raw: true });
      } else {
        wb = XLSX.read(buf, { type: 'array' });
      }""",
    '① CSV 解码（UTF-8→GBK 回退）+ 新增 secFromCell()')

# ② 预览用 secFromCell
rep("""  const prev = body.slice(0, 6).map(r => {
    const sec = parseSec(r[rs]);""",
    """  const prev = body.slice(0, 6).map(r => {
    const sec = secFromCell(r[rs]);""",
    '②a 预览用 secFromCell（能认 Excel 时间格式）')

# ③ 导入用 secFromCell
rep("""    const raw = r[importCfg.resCol];
    const sec = parseSec(raw);
    if (!sec) { bad++; return; }""",
    """    const raw = r[importCfg.resCol];
    const sec = secFromCell(raw);
    if (!sec) { bad++; return; }""",
    '②b 导入用 secFromCell')

# ④ 页面上写清支持的成绩格式
rep("""    <div class="preview"><table class="tbl" style="min-width:auto">
      <thead><tr><th class="no-sort">姓名</th><th class="no-sort">原始成绩</th><th class="no-sort">识别为</th><th class="no-sort">是否队员</th></tr></thead>""",
    """    <div class="tiny" style="margin-bottom:8px">成绩认得出这些：<b>17:35</b>、1:23:29、18'35"、18.5（分钟），
      以及 Excel 里存成时间格式的（单元格显示 17:35 但实际是 0.7326）和直接写秒数的（1022 = 17:02）。</div>
    <div class="preview"><table class="tbl" style="min-width:auto">
      <thead><tr><th class="no-sort">姓名</th><th class="no-sort">原始成绩</th><th class="no-sort">识别为</th><th class="no-sort">是否队员</th></tr></thead>""",
    '②c 页面上写清支持的成绩格式')

io.open(P, 'wb').write(s.replace('\n', '\r\n').encode('utf-8'))
print('\n'.join('   ' + d for d in done))
