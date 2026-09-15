# -*- coding: utf-8 -*-
"""修第三个 bug：「↺ 恢复显示」/「移除」只动了本机 hidden，没动 shown ——
   而人多数是云端 hidden（云端 hidden 本机删不掉），所以点恢复永远没反应。
   两边必须互斥：恢复 = 出 hidden + 进 shown；移除 = 进 hidden + 出 shown。"""
import io, os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'app.js')
s = io.open(P, encoding='utf-8', newline='').read().replace('\r\n', '\n')
n = 0

old1 = """  $$('[data-mdel]').forEach(b => b.onclick = () => {
    const n = b.dataset.mdel;
    const l = ovLocal();
    l.hidden = (l.hidden || []).concat([n]);
    saveLocalOv(); toast('已从公开名册移除 ' + n); render();
  });"""
new1 = """  $$('[data-mdel]').forEach(b => b.onclick = () => {
    const n = b.dataset.mdel;
    const l = ovLocal();
    l.hidden = (l.hidden || []).concat([n]).filter((x, i, a) => a.indexOf(x) === i);
    l.shown = (l.shown || []).filter(x => x !== n);      // 和「恢复显示」互斥，不然移除了又被 shown 顶回来
    saveLocalOv(); toast('已从公开名册移除 ' + n + ' —— 记得同步，线上才会消失', 10000); render();
  });"""
assert old1 in s, '1'
s = s.replace(old1, new1, 1); n += 1

old2 = """  $$('[data-mrestore]').forEach(b => b.onclick = () => {
    const n = b.dataset.mrestore, l = ovLocal();
    l.hidden = (l.hidden || []).filter(x => x !== n);
    saveLocalOv(); render();
  });"""
new2 = """  $$('[data-mrestore]').forEach(b => b.onclick = () => {
    const n = b.dataset.mrestore, l = ovLocal();
    l.hidden = (l.hidden || []).filter(x => x !== n);
    // ⚠️ 大多数人是**云端** hidden 的，只删本机 hidden 等于没删 —— 必须同时进 shown，
    //    同步时才会把名字从 hidden 里扣掉（2026-09-15 修：以前点「恢复显示」永远没反应）
    l.shown = Array.from(new Set((l.shown || []).concat([n])));
    saveLocalOv();
    toast('已把 ' + n + ' 放回名册 —— 记得点「同步我的修改到线上」，线上才会显示', 12000);
    render();
  });"""
assert old2 in s, '2'
s = s.replace(old2, new2, 1); n += 1

io.open(P, 'w', encoding='utf-8', newline='').write(s.replace('\n', '\r\n'))
print('改了 %d 处' % n)
