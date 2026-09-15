# -*- coding: utf-8 -*-
"""C 补丁：名册「导入队员资料」的交互绑定 + 名册头像（无照片用队徽）"""
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


# ② 读文件 + 解析绑定
rep("""  const drop = $('#drop'), fi = $('#fileInput');""",
    """  const dF = $('#docFile'), dI = $('#btnDocImport');
  if (dI && dF) dI.onclick = () => dF.click();
  if (dF) dF.onchange = () => {
    const f = dF.files[0];
    dF.value = '';
    if (!f) return;
    const fr = new FileReader();
    fr.onload = () => {
      const doc = parseMemberDoc(fr.result);
      if (!doc) return toast('没看懂这份资料：应该包含「姓名」和各项成绩');
      memberDocQueue = { doc: doc };
      toast('已读取 ' + f.name + '，确认下面这份就点导入');
      renderMemberDocPreview();
    };
    fr.readAsText(f);
  };
  const dP = $('#btnDocParse');
  if (dP) dP.onclick = () => {
    const ta = $('#docText');
    const doc = parseMemberDoc(ta ? ta.value : '');
    if (!doc) return toast('没看懂：每行写成「字段 值」，比如 姓名 张三');
    memberDocQueue = { doc: doc };
    renderMemberDocPreview();
  };

  const drop = $('#drop'), fi = $('#fileInput');""",
    '②a 绑定导入')

# ③ 名册卡片显示头像（没有照片用队徽）
rep("""      return `
      <div class="pcard">
        <div class="nm">${esc(m.name)}</div>
        <div class="meta">${m.grade ? esc(m.grade) + ' 级 · ' : ''}${esc(m.college || '')}${m.major ? ' · ' + esc(m.major) : ''}</div>""",
    """      const av = m.photo && /^data:|^https?:/.test(m.photo) ? m.photo
        : ROOT + (m.photo || 'images/logo.jpg');
      return `
      <div class="pcard">
        <div class="head-row">
          <img class="avatar" src="${esc(av)}" alt="" loading="lazy" onerror="this.src='${ROOT}images/logo.jpg'">
          <div class="who">
            <div class="nm">${esc(m.name)}</div>
            <div class="meta">${m.grade ? esc(m.grade) + ' 级 · ' : ''}${esc(m.college || '')}${m.major ? ' · ' + esc(m.major) : ''}</div>
          </div>
        </div>""",
    '③a 名册卡片头像')

io.open(P, 'wb').write(s.replace('\n', '\r\n').encode('utf-8'))
print('\n'.join('   ' + d for d in done))
