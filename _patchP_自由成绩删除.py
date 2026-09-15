# -*- coding: utf-8 -*-
"""修「自由成绩」删不掉：
  ① 列表用的 ov().results 只按**云端** hiddenResults 过滤 → 本机记下的"删"根本不生效（点了没反应）
  ② 每行的「删」按钮按下标去删**本机** results 数组 → 但列表里云端成绩排在前面，
     下标对不上（删云端那条时删掉/什么都没删），而且没有任何提示
  ③ 顺手补一条"已删除（可 ↺ 恢复）"，和照片墙一个套路，靠本机 shownResults 顶掉云端的 hiddenResults
"""
import io, os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'app.js')
s = io.open(P, encoding='utf-8', newline='').read().replace('\r\n', '\n')
n = 0

# ① ov().results 的过滤：云端 + 本机 hiddenResults，再减掉本机 shownResults
old1 = """    results: (function () {
      const hid = new Set(c.hiddenResults || []);
      return (c.results || []).concat(l.results || [])
        .filter(r => !hid.has(r.uid || (r.name + '|' + r.sec)));
    })(),"""
new1 = """    results: (function () {
      // ⚠️ 必须把本机删过的（l.hiddenResults）也算进去，并减掉本机恢复的（l.shownResults），
      //    只按云端 hiddenResults 过滤的话，队长点了「删」页面毫无反应（2026-09-15 修）
      const hid = new Set((c.hiddenResults || []).concat(l.hiddenResults || []));
      (l.shownResults || []).forEach(k => hid.delete(k));
      return (c.results || []).concat(l.results || [])
        .filter(r => !hid.has(resultKey(r)));
    })(),"""
assert old1 in s, '①'
s = s.replace(old1, new1, 1); n += 1

# 结果主键助手 + 已删除列表
old2 = """function rosterList() {"""
new2 = """/** 一条成绩的身份（删除/恢复都按它认，不能用下标 —— 列表里云端成绩排在前面，下标对不上） */
function resultKey(r) {
  if (!r) return '';
  return String(r.uid || ((r.name || '') + '|' + (r.sec === undefined ? '' : r.sec)));
}
/** 被删掉的成绩（云端 + 本机记的，减掉本机恢复的）—— 用来渲染"已删除（可恢复）" */
function removedResults() {
  const c = CLOUD_OV || {}, l = LOCAL_OV || {};
  const shown = l.shownResults || [];
  const keys = Array.from(new Set((c.hiddenResults || []).concat(l.hiddenResults || [])))
    .filter(k => shown.indexOf(k) < 0);
  const all = (c.results || []).concat(l.results || []);
  return keys.map(k => all.filter(r => resultKey(r) === k)[0] || { _key: k }).filter(Boolean);
}

function rosterList() {"""
assert old2 in s, '②'
s = s.replace(old2, new2, 1); n += 1

# ② 自由成绩区：按"身份"渲染 + 已删除区 + 恢复按钮
old3 = """        <tbody>${added.map((r, i) => `
          <tr><td><b>${esc(r.name)}</b></td><td class="tiny">${esc(r.event)}</td>
            <td class="tm">${esc(r.fmt || fmtSec(r.sec))}</td>
            <td class="tiny hide-sm">${esc(r.date || '')}</td><td class="tiny hide-sm">${esc(r.meet || '')}</td>
            <td><button class="btn danger sm" data-pubdel="${i}">删</button></td></tr>`).join('')}
        </tbody>
      </table>
    </div>
    <button class="btn" id="btnPublishMine" style="margin-top:14px">把「上传成绩」里录入的 ${myResults().length} 条发布到线上</button>`
      : '<div class="empty">还没有发布过成绩</div>'}
  </div>` : ''}`;"""
new3 = """        <tbody>${added.map(r => `
          <tr><td><b>${esc(r.name)}</b></td><td class="tiny">${esc(r.event)}</td>
            <td class="tm">${esc(r.fmt || fmtSec(r.sec))}</td>
            <td class="tiny hide-sm">${esc(r.date || '')}</td><td class="tiny hide-sm">${esc(r.meet || '')}</td>
            <td><button class="btn danger sm" data-resdel="${esc(resultKey(r))}">删</button></td></tr>`).join('')}
        </tbody>
      </table>
    </div>
    <button class="btn" id="btnPublishMine" style="margin-top:14px">把「上传成绩」里录入的 ${myResults().length} 条发布到线上</button>`
      : '<div class="empty">还没有发布过成绩</div>'}
    ${removedResults().length ? `
    <h2 style="margin-top:22px">已删除的成绩（${removedResults().length} 条，可恢复）</h2>
    <div class="tiny" style="margin-bottom:10px">删错的在这里点「↺ 恢复」，再点一次「同步我的修改到线上」就回来了。</div>
    <div class="tbl-wrap">
      <table class="tbl" style="min-width:auto">
        <thead><tr><th class="no-sort">姓名</th><th class="no-sort">项目</th><th class="no-sort">成绩</th>
          <th class="no-sort hide-sm">赛事</th><th class="no-sort"></th></tr></thead>
        <tbody>${removedResults().map(r => `
          <tr><td><b>${esc(r.name || '（找不到原始记录）')}</b></td><td class="tiny">${esc(r.event || '')}</td>
            <td class="tm">${esc(r.fmt || (r.sec ? fmtSec(r.sec) : ''))}</td>
            <td class="tiny hide-sm">${esc(r.meet || '')}</td>
            <td><button class="btn ghost sm" data-resrestore="${esc(r._key || resultKey(r))}">↺ 恢复</button></td></tr>`).join('')}
        </tbody>
      </table>
    </div>` : ''}
  </div>` : ''}`;"""
assert old3 in s, '③'
s = s.replace(old3, new3, 1); n += 1

# ④ 删除/恢复的处理：按身份找，云端那条靠 hiddenResults 屏蔽
old4 = """  $$('[data-pubdel]').forEach(b => b.onclick = () => {
    const l = ovLocal();
    const arr = ovLocal().results.slice();
    arr.splice(+b.dataset.pubdel, 1);
    l.results = arr;
    saveLocalOv(); render();
  });"""
new4 = """  $$('[data-resdel]').forEach(b => b.onclick = () => {
    const key = b.dataset.resdel;
    if (!key) return;
    const l = ovLocal();
    const own = (l.results || []).filter(r => resultKey(r) === key);
    if (own.length) {                                       // 本机发布的 → 直接从本机删
      l.results = (l.results || []).filter(r => resultKey(r) !== key);
      l.shownResults = (l.shownResults || []).filter(x => x !== key);   // 和「恢复」互斥
      saveLocalOv();
      toast('已删除这条成绩 —— 记得点「同步我的修改到线上」', 10000);
    } else {                                                // 云端已发布的 → 记进 hiddenResults 屏蔽掉
      l.hiddenResults = (l.hiddenResults || []).concat([key]).filter((x, i, a) => a.indexOf(x) === i);
      l.shownResults = (l.shownResults || []).filter(x => x !== key);
      saveLocalOv();
      toast('已删除这条线上成绩 —— 记得点「同步我的修改到线上」，线上才会真的消失', 12000);
    }
    render();
  });
  $$('[data-resrestore]').forEach(b => b.onclick = () => {
    const key = b.dataset.resrestore;
    if (!key) return;
    const l = ovLocal();
    l.hiddenResults = (l.hiddenResults || []).filter(x => x !== key);
    // 云端那份 hiddenResults 本机删不掉 → 必须显式记进 shownResults，同步时才会扣掉
    if ((CLOUD_OV && CLOUD_OV.hiddenResults || []).indexOf(key) >= 0) {
      l.shownResults = (l.shownResults || []).concat([key]).filter((x, i, a) => a.indexOf(x) === i);
    }
    saveLocalOv();
    toast('已恢复这条成绩 —— 记得点「同步我的修改到线上」，线上才会重新显示', 12000);
    render();
  });"""
assert old4 in s, '④'
s = s.replace(old4, new4, 1); n += 1

# ⑤ 同步载荷：hiddenResults 扣掉本机 shownResults；results 过滤也用它
old5 = """      results: (function () {
        const hid = new Set((cloud.hiddenResults || []).concat(l.hiddenResults || []));
        return (cloud.results || []).concat(l.results || [])
          .filter(r => !hid.has(r.uid || (r.name + '|' + r.sec)));
      })(),
      hiddenResults: (cloud.hiddenResults || []).concat(l.hiddenResults || []),"""
new5 = """      results: (function () {
        const hid = new Set((cloud.hiddenResults || []).concat(l.hiddenResults || []));
        (l.shownResults || []).forEach(k => hid.delete(k));      // 本机"恢复"的要顶掉云端的删除记录
        return (cloud.results || []).concat(l.results || [])
          .filter(r => !hid.has(resultKey(r)));
      })(),
      hiddenResults: (cloud.hiddenResults || []).concat(l.hiddenResults || [])
        .filter(k => (l.shownResults || []).indexOf(k) < 0),
      shownResults: (l.shownResults || []),"""
assert old5 in s, '⑤'
s = s.replace(old5, new5, 1); n += 1

io.open(P, 'w', encoding='utf-8', newline='').write(s.replace('\n', '\r\n'))
print('改了 %d 处' % n)
