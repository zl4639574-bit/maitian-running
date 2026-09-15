# -*- coding: utf-8 -*-
"""G 补丁：名册管理里显示"被隐藏的人"并可一键恢复（解决"搜不到某人、改不了他"）"""
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


# ① ov()：本机可以"强行显示"某些被隐藏的人（shown 覆盖 hidden）
rep("""    hidden: Array.from(new Set((c.hidden || []).concat(l.hidden || []))),""",
    """    // 本机"恢复显示"的人（shown）优先：从隐藏集合里剔除，这样同步后所有人也看得到
    hidden: Array.from(new Set((c.hidden || []).concat(l.hidden || [])))
      .filter(n => (l.shown || []).indexOf(n) < 0),""",
    '① ov() 支持 shown 覆盖')

# ② 名册管理卡片里，列出被隐藏的人 + 恢复键
rep("""        <div id="docSheetArea" style="flex-basis:100%"></div>""",
    """        <div id="docSheetArea" style="flex-basis:100%"></div>
        ${(() => {
          const hid = ov().hidden || [];
          if (!hid.length) return '';
          return `<div class="notice" style="flex-basis:100%;margin-top:12px">
            <b>已隐藏 ${hid.length} 人</b>（不在名册和榜单里显示，所以搜不到、也改不了他们的信息）：
            <div style="margin-top:6px">${hid.map(n => `<span style="display:inline-block;margin:4px 10px 0 0;white-space:nowrap">${esc(n)}<button class="btn flat sm" style="margin-left:6px" data-unhide="${esc(n)}">恢复显示</button></span>`).join('')}</div>
            <div class="tiny" style="margin-top:6px">点「恢复显示」后，点「同步我的修改到线上」，他就会回到名册里（名单口径跟着变）。</div>
          </div>`;
        })()}""",
    '② 名册区列出隐藏的人')

# ③ 绑定恢复键
rep("""  const sF = $('#docSheetFile'), sI = $('#btnDocSheet');""",
    """  $$('[data-unhide]').forEach(b => b.onclick = () => {
    const n = b.dataset.unhide;
    const l = ovLocal();
    l.shown = Array.from(new Set((l.shown || []).concat([n])));
    if ((l.hidden || []).indexOf(n) >= 0) l.hidden = l.hidden.filter(x => x !== n);
    saveLocalOv();
    toast('已恢复显示「' + n + '」：他会出现回名册里。记得点「同步我的修改到线上」', 11000);
    render();
  });

  const sF = $('#docSheetFile'), sI = $('#btnDocSheet');""",
    '③ 绑定恢复显示')

io.open(P, 'wb').write(s.replace('\n', '\r\n').encode('utf-8'))
print('\n'.join('   ' + d for d in done))
