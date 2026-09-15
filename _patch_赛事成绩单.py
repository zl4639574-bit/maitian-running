# -*- coding: utf-8 -*-
"""赛事整体成绩单（含非队员）导入改进：
   ① 姓名识别放宽（原来只认 2~5 个汉字，少数民族名/英文名/长名字会被静默丢掉）
   ② 支持「名次列」映射
   ③ 导入预览 + 上传页清单 + 单场成绩榜：标出「队员 / 非队员」，并汇总非队员人数
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


# ── ① 姓名规则放宽 + 名次列识别 ──
rep("""        nameCol: guessCol(cols, /姓名|名字|人员|队员/),
        resCol: guessCol(cols, /成绩|用时|时间|结果|净计时/),
        sexCol: guessCol(cols, /性别/), colCol: guessCol(cols, /学院|院系|单位/),""",
    """        nameCol: guessCol(cols, /姓名|名字|人员|队员|选手/),
        resCol: guessCol(cols, /成绩|用时|时间|结果|净计时/),
        sexCol: guessCol(cols, /性别/), colCol: guessCol(cols, /学院|院系|单位/),
        rankCol: guessCol(cols, /名次|排名|rank/i),""",
    '①a 自动识别「名次列」')

rep("""        importCfg.nameCol = guessCol(c2, /姓名|名字|人员|队员/);
        importCfg.resCol = guessCol(c2, /成绩|用时|时间|结果|净计时/);
        importCfg.sexCol = guessCol(c2, /性别/);
        importCfg.colCol = guessCol(c2, /学院|院系|单位/);""",
    """        importCfg.nameCol = guessCol(c2, /姓名|名字|人员|队员|选手/);
        importCfg.resCol = guessCol(c2, /成绩|用时|时间|结果|净计时/);
        importCfg.sexCol = guessCol(c2, /性别/);
        importCfg.colCol = guessCol(c2, /学院|院系|单位/);
        importCfg.rankCol = guessCol(c2, /名次|排名|rank/i);""",
    '①b 换表头行时也重认名次列')

rep("""    const name = String(r[importCfg.nameCol] == null ? '' : r[importCfg.nameCol]).trim().replace(/\\s/g, '');
    if (!/^[\\u4e00-\\u9fa5·]{2,5}$/.test(name)) { noName++; return; }""",
    """    // 姓名：去掉括号备注和空格；2~14 个字符，允许 中文 / 维吾尔名里的「·」/ 拼音或英文名
    const name = String(r[importCfg.nameCol] == null ? '' : r[importCfg.nameCol])
      .replace(/[（(].*?[)）]/g, '').replace(/\\s+/g, '');
    if (!/^[\\u4e00-\\u9fa5·a-zA-Z][\\u4e00-\\u9fa5·a-zA-Z0-9]{1,13}$/.test(name)) { noName++; return; }""",
    '①c 姓名识别放宽到 2~14 字符')

rep("""      sex: importCfg.sexCol >= 0 ? String(r[importCfg.sexCol] || '') : '',
      college: importCfg.colCol >= 0 ? String(r[importCfg.colCol] || '') : '',
      date: importCfg.date, meet: importCfg.meet, ts: Date.now(),""",
    """      sex: importCfg.sexCol >= 0 ? String(r[importCfg.sexCol] || '') : '',
      college: importCfg.colCol >= 0 ? String(r[importCfg.colCol] || '') : '',
      rank: importCfg.rankCol >= 0 ? String(r[importCfg.rankCol] == null ? '' : r[importCfg.rankCol]).trim() : '',
      date: importCfg.date, meet: importCfg.meet, ts: Date.now(),""",
    '①d 导入时带上名次')

# ── ② 导入结果提示里说清非队员 ──
rep("""  if (!out.length) return toast('一条都没导入成功，检查一下列对应关系');
  addMyResults(out);
  pendingFile = null;
  toast('已导入 ' + out.length + ' 条' + (bad ? '，跳过 ' + bad + ' 条成绩认不出的' : '')
        + (noName ? '，跳过 ' + noName + ' 条没姓名的' : '')
        + (MODE === 'captain' ? '；点下面「发布并同步到线上」全队才能看到' : ''), 7000);""",
    """  if (!out.length) return toast('一条都没导入成功，检查一下列对应关系');
  const memberSet = new Set(rosterList().map(m => m.name));
  const guests = out.filter(x => !memberSet.has(x.name)).length;
  addMyResults(out);
  pendingFile = null;
  toast('已导入 ' + out.length + ' 条' + (bad ? '，跳过 ' + bad + ' 条成绩认不出的' : '')
        + (noName ? '，跳过 ' + noName + ' 条姓名看不懂的' : '')
        + (guests ? '。其中 ' + guests + ' 位不在名册（非队员）：只会出现在这场比赛的榜上，不进名册、也不进个人最好成绩榜' : '')
        + (MODE === 'captain' ? '；点下面「发布并同步到线上」全队才能看到' : ''), 11000);""",
    '②a 导入提示里点明非队员')

# ── ③ 导入预览：加「是否队员」列 + 汇总 ──
rep("""  const prev = body.slice(0, 6).map(r => {
    const sec = parseSec(r[rs]);
    return `<tr><td>${esc(r[nm])}</td><td>${esc(r[rs])}</td>
      <td class="tm">${sec ? esc(fmtSec(sec)) : '<span style="color:var(--red)">认不出</span>'}</td></tr>`;
  }).join('');""",
    """  const memberSet = new Set(rosterList().map(m => m.name));
  const prev = body.slice(0, 6).map(r => {
    const sec = parseSec(r[rs]);
    const rn = String(r[nm] == null ? '' : r[nm]).replace(/[（(].*?[)）]/g, '').replace(/\\s+/g, '');
    return `<tr><td>${esc(r[nm])}</td><td>${esc(r[rs])}</td>
      <td class="tm">${sec ? esc(fmtSec(sec)) : '<span style="color:var(--red)">认不出</span>'}</td>
      <td>${memberSet.has(rn) ? '<span class="tagbadge green">队员</span>' : '<span class="tagbadge">非队员</span>'}</td></tr>`;
  }).join('');""",
    '③a 预览加「是否队员」列')

rep("""    <div class="tiny" style="margin-bottom:10px">已读取 <b>${esc(pendingFile.name)}</b>，${body.length} 行数据
      ${pendingFile.sheetNames.length > 1 ? '，共 ' + pendingFile.sheetNames.length + ' 个工作表' : ''}。</div>""",
    """    <div class="tiny" style="margin-bottom:10px">已读取 <b>${esc(pendingFile.name)}</b>，${body.length} 行数据
      ${pendingFile.sheetNames.length > 1 ? '，共 ' + pendingFile.sheetNames.length + ' 个工作表' : ''}。<br>
      不认识的姓名（非本队队员）也可以一起导入：他们<b>只出现在这场比赛的榜上</b>，不会进名册、也不会进个人最好成绩榜。</div>""",
    '③b 预览上方说明非队员规则')

rep("""      ${selBox('学院列', 'colCol', true, importCfg.colCol)}""",
    """      ${selBox('学院列', 'colCol', true, importCfg.colCol)}
      ${selBox('名次列', 'rankCol', true, importCfg.rankCol)}""",
    '③c 预览加「名次列」下拉')

rep("""      <thead><tr><th class="no-sort">姓名</th><th class="no-sort">原始成绩</th><th class="no-sort">识别为</th></tr></thead>""",
    """      <thead><tr><th class="no-sort">姓名</th><th class="no-sort">原始成绩</th><th class="no-sort">识别为</th><th class="no-sort">是否队员</th></tr></thead>""",
    '③d 预览表头加一列')

# ── ④ 单场成绩榜：非队员标记 + 头部汇总 ──
rep("""    const rk = {};
    rows.forEach(r => { rk[r.event || ''] = (rk[r.event || ''] || 0) + 1; r._rk = rk[r.event || '']; });""",
    """    const rk = {};
    rows.forEach(r => { rk[r.event || ''] = (rk[r.event || ''] || 0) + 1; r._rk = rk[r.event || '']; });
    // 名册里没有的人 = 非队员（跑团朋友、外校选手…）：只显示在这场的榜里
    const memSet = new Set(rosterList().map(m => m.name));
    const guestN = rows.filter(r => r.name && !memSet.has(r.name)).length;""",
    '④a 单场榜算非队员人数')

rep("""        <br>共 ${cur.records.length} 条记录${evs.length ? '，项目：' + evs.map(esc).join(' / ') : ''}""",
    """        <br>共 ${cur.records.length} 条记录${guestN ? '（含 ' + guestN + ' 条非队员成绩）' : ''}${evs.length ? '，项目：' + evs.map(esc).join(' / ') : ''}""",
    '④b 头部汇总非队员条数')

rep("""            <td><b>${esc(r.name)}</b></td>
            <td class="sex-b hide-sm">${esc(r.sex || '')}</td>""",
    """            <td><b>${esc(r.name)}</b>${memSet.has(r.name) ? '' : ' <span class="tagbadge" title="不在队伍名册里，只进这一场的榜">非队员</span>'}</td>
            <td class="sex-b hide-sm">${esc(r.sex || '')}</td>""",
    '④c 单场榜给非队员加淡色标记')

# ── ⑤ 上传成绩页：我录入的成绩清单里也标出来 + 一句用法说明 ──
rep("""          <tr><td><b>${esc(r.name)}</b>${r.submitted ? ' <span class="tagbadge green">已提交</span>' : ''}</td>""",
    """          <tr><td><b>${esc(r.name)}</b>${r.submitted ? ' <span class="tagbadge green">已提交</span>' : ''}${rosterNames.has(r.name) ? '' : ' <span class="tagbadge">非队员</span>'}</td>""",
    '⑤a 上传页清单标非队员')

rep("""function renderUpload() {
  const L = myResults().sort((a, b) => (b.date || '').localeCompare(a.date || ''));""",
    """function renderUpload() {
  const L = myResults().sort((a, b) => (b.date || '').localeCompare(a.date || ''));
  const rosterNames = new Set(rosterList().map(m => m.name));""",
    '⑤b 预处理名册集合')

rep("""    <div class="tiny" style="margin-top:8px">手机上点这里会打开文件选择器，选微信里收到的成绩表也能用<br>
        支持 .xlsx / .xls / .csv</div>""",
    """    <div class="tiny" style="margin-top:8px">手机上点这里会打开文件选择器，选微信里收到的成绩表也能用<br>
        支持 .xlsx / .xls / .csv｜<b>整场成绩单（含非队员、外校选手）可以直接拖进来</b>：
        导入后在「数据管理 → 比赛成绩」新建一场比赛，点「把本机录入的成绩并进这场比赛」，就成了一张完整的榜；
        非队员只出现在这场榜里，不会进名册、也不会进个人最好成绩榜</div>""",
    '⑤c 用法说明补一句')

io.open(P, 'wb').write(s.replace('\n', '\r\n').encode('utf-8'))
print('\n'.join('   ' + d for d in done))
