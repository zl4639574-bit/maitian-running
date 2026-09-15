# -*- coding: utf-8 -*-
"""D 补丁：一键发给队长（系统分享面板，可带 .json 文件，不用复制）
   ① 上报页「成绩上报」+「完善我的资料」两个页签都加「📤 直接发给队长」
   ② 队长端「粘贴文本导入」改成「接收上报」：自动识别是成绩上报还是队员资料
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


# ① 分享函数
rep("""/* ---------------- 队员「完善我的资料」收集页 ---------------- */""",
    """/** 一键发给队长：手机原生分享面板（能带文件），不行再退回复制
    返回 'share-file' | 'share-text' | 'copy' | 'cancel' */
async function shareToCaptain(o) {
  const text = o.text || '';
  try {
    if (o.json && o.fname && navigator.canShare) {
      const f = new File([o.json], o.fname, { type: 'application/json' });
      if (navigator.canShare({ files: [f] })) {
        await navigator.share({ files: [f], title: '麦田守望 · 上报', text: o.tip || '队里上报，请队长导入' });
        return 'share-file';
      }
    }
    if (navigator.share) {
      await navigator.share({ title: '麦田守望 · 上报', text: text });
      return 'share-text';
    }
  } catch (e) {
    if (e && e.name === 'AbortError') return 'cancel';
  }
  copyText(text);
  return 'copy';
}

/** 统一的分享结果提示 */
function shareToast(r, what) {
  if (r === 'share-file') toast('已打开分享面板：选微信 → 发给队长就行（' + what + '已经打包好）', 8000);
  else if (r === 'share-text') toast('已打开分享面板：选微信 → 发给队长就行', 8000);
  else if (r === 'cancel') toast('已取消（数据还在本机，随时可以再发）');
  else toast('这个浏览器不支持直接分享，已经帮你复制好了：粘给队长即可', 8000);
}

/* ---------------- 队员「完善我的资料」收集页 ---------------- */""",
    '①a shareToCaptain')

# ② 成绩上报页加按钮
rep("""      <div class="chips">
        <button class="btn ${rep ? '' : 'ghost'} sm" id="btnCopy" ${L.length ? '' : 'disabled'}>${rep ? '复制成上报文本（发队长）' : '复制成文本'}</button>""",
    """      <div class="chips">
        ${rep ? `<button class="btn sm" id="btnShare" ${L.length ? '' : 'disabled'}>📤 直接发给队长</button>` : ''}
        <button class="btn ${rep ? 'ghost' : ''} sm" id="btnCopy" ${L.length ? '' : 'disabled'}>${rep ? '复制成上报文本（发队长）' : '复制成文本'}</button>""",
    '②a 上报页加分享键')

rep("""  const cp = $('#btnCopy');
  if (cp) cp.onclick = () => {
    const txt = '麦田守望 · 成绩上报（' + todayStr() + '）\\n'""",
    """  const sh = $('#btnShare');
  if (sh) sh.onclick = async () => {
    const lines = ['麦田守望 · 成绩上报（' + todayStr() + '）',
      '姓名\\t项目\\t成绩\\t日期\\t赛事/名次']
      .concat(myResults().map(r => [r.name, r.event, r.fmt || fmtSec(r.sec), r.date, r.meet || r.rank || ''].join('\\t')));
    const txt = lines.join('\\n');
    const json = JSON.stringify({ type: 'maitian-scores', date: todayStr(),
      rows: myResults().map(r => ({ name: r.name, event: r.event, fmt: r.fmt || fmtSec(r.sec),
        sec: r.sec, date: r.date, meet: r.meet || '', rank: r.rank || '' })) }, null, 1);
    const r = await shareToCaptain({ text: txt, json: json, fname: '麦田守望_成绩上报_' + todayStr() + '.json',
      tip: '麦田守望 成绩上报（' + myResults().length + ' 条），请队长导入' });
    shareToast(r, '成绩');
  };

  const cp = $('#btnCopy');
  if (cp) cp.onclick = () => {
    const txt = '麦田守望 · 成绩上报（' + todayStr() + '）\\n'""",
    '②b 上报页分享逻辑')

# ③ 资料页加按钮
rep("""    <div class="chips" style="margin-top:20px">
      <button class="btn" id="meSave">保存资料</button>""",
    """    <div class="chips" style="margin-top:20px">
      <button class="btn" id="meSave">保存资料</button>
      <button class="btn" id="meShare" ${d.name ? '' : 'disabled'}>📤 直接发给队长</button>""",
    '③a 资料页加分享键')

rep("""  const cp = $('#meCopy');
  if (cp) cp.onclick = () => { copyText(meText(save())); toast('资料文本已复制，粘给队长即可', 6000); };""",
    """  const sh2 = $('#meShare');
  if (sh2) sh2.onclick = async () => {
    const d2 = save();
    const n = String(d2.pb && (d2.pb['5000米'] || d2.pb['3000米'] || '') || '').trim();
    const r = await shareToCaptain({ text: meText(d2),
      json: JSON.stringify(d2, null, 1), fname: '麦田守望_我的资料_' + (d2.name || '未填') + '.json',
      tip: '麦田守望 队员资料：' + (d2.name || '') + (n ? '（5000米 ' + n + '）' : '') + '，请队长导入' });
    shareToast(r, '资料' + (d2.photo ? '和照片' : ''));
  };

  const cp = $('#meCopy');
  if (cp) cp.onclick = () => { copyText(meText(save())); toast('资料文本已复制，粘给队长即可', 6000); };""",
    '③b 资料页分享逻辑')

# ④ 队长端「接收上报」：自动识别成绩 / 资料
rep("""    <h2>② 粘贴文本导入（队员上报贴这里）</h2>""",
    """    <h2>② 接收上报（成绩 / 资料都能贴）</h2>""",
    '④a 标题改成接收上报')

rep("""  const pg = $('#btnPasteGo');
  if (pg) pg.onclick = () => {
    const ta = $('#pasteBox');
    pasteRows = pasteParseText(ta ? ta.value : '');
    renderPasteArea();
  };""",
    """  const pg = $('#btnPasteGo');
  if (pg) pg.onclick = () => {
    const ta = $('#pasteBox');
    const txt = ta ? ta.value : '';
    // 自动识别：队员资料（含「姓名」字段且带各项距离/教育信息）还是成绩上报
    const isDoc = /^\\s*\\{/.test(txt) && /maitian-member/.test(txt)
      || /队员资料|性别\\s*[\\t:：]|学院\\s*[\\t:：]|(800米|1500米|半马|全马)\\s*[\\t:：]/.test(txt);
    if (isDoc) {
      const doc = parseMemberDoc(txt);
      if (!doc) return toast('像是队员资料，但没解析出姓名，检查一下内容');
      memberDocQueue = { doc: doc };
      toast('识别为「队员资料」，确认下面这份就点导入', 6000);
      renderMemberDocPreview();
      return;
    }
    pasteRows = pasteParseText(txt);
    renderPasteArea();
  };""",
    '④b 接收时自动识别类型')

io.open(P, 'wb').write(s.replace('\n', '\r\n').encode('utf-8'))
print('\n'.join('   ' + d for d in done))
