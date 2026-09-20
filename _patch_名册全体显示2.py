# -*- coding: utf-8 -*-
"""名册全体显示 · 第二批（漏掉的文案 + 导入资料不再自动放回「已移除」的人）"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))

APP = [
# 导入资料：不再自动把人从「已移除」里放回来
("""  // 身份（正式 / 预备 / 普通）：只在资料里写了有效身份时才改，空着不动（老的资料文件没有这一项）
  const lvIn = normLevelOf(doc.level);
  let levelNote = '';
  if (lvIn && lvIn.length) {
    e.level = lvIn;
    levelNote = '，身份已设为「' + lvIn.join('/') + '」';
    if (isVisibleLevel(lvIn) && !wasInRoster) {        // 本来不在公开名册里 → 这次明确设成正式/预备了
      if (unhideMember(doc.name)) levelNote += '、已把他从「已移除」里放回名册';
    }
  }""",
 """  // 身份（正式 / 预备 / 普通 / 队员）：只在资料里写了有效身份时才改，空着不动（老的资料文件没有这一项）
  const lvIn = normLevelOf(doc.level);
  let levelNote = '';
  if (lvIn && lvIn.length) {
    e.level = lvIn;
    levelNote = '，身份已设为「' + lvIn.join('/') + '」';
    // 2026-09-20 起名册显示所有身份：导入资料不再自动把人从「已移除」里放回来（要放回得手动点「↺ 恢复显示」）
  }"""),

# 队员端「完善我的资料」的身份说明
("""        ${[['', '未填（让队长核定）'], ['正式', '正式队员'], ['预备', '预备队员'], ['普通', '普通（队里的人，不进公开名册）']].map(([v, l]) =>
          `<option value="${v}" ${dLv === v ? 'selected' : ''}>${l}</option>`).join('')}
      </select>
      <div class="tiny" style="margin-top:4px">不确定就先留「未填」；正式/预备 会显示在公开名册里</div></div>""",
 """        ${[['', '未填（让队长核定）'], ['正式', '正式队员'], ['预备', '预备队员'], ['普通', '普通（队里的队员）']].map(([v, l]) =>
          `<option value="${v}" ${dLv === v ? 'selected' : ''}>${l}</option>`).join('')}
      </select>
      <div class="tiny" style="margin-top:4px">不确定就先留「未填」；身份只是标注，名册里所有人都会显示</div></div>"""),

# normLevelOf 的说明
("""/** 「身份」文本 → 数组；空/看不懂 → null（= 别动这一项）
    注意：返回 [] 表示\"明确写成空\"（数据表的「留空 = 不进公开名册」），跟 null 不是一回事 */""",
 """/** 「身份」文本 → 数组；空/看不懂 → null（= 别动这一项）
    注意：返回 [] 表示\"明确写成空\"（数据表的「留空 = 身份清空，名册里显示成未分级」），跟 null 不是一回事 */"""),

# 完善信息列表的注释
("""/** 名册（正式/预备）里信息不全的人 */""",
 """/** 名册里信息不全的人（所有身份都算） */"""),

# 导出表解析的注释
("""  // 返回 [] = 明确\"不进公开名册\"；返回 null = 这个值看不懂（例如「队员」），保持原样别动""",
 """  // 返回 [] = 明确清空身份（显示成「未分级」）；返回 null = 这个值看不懂，保持原样别动"""),

# 启动时那行已经没用的提示
("""  const healed = healRosterHidden();          // 把\"身份已升级但被「已移除」压着\"的人放回名册
  if (healed) setTimeout(() => toast('有 ' + healed + ' 位身份已改成正式/预备的人之前被「已移除」压着，已自动放回名册 —— 点一次「同步我的修改到线上」他们就会出现在公开名册里', 16000), 1500);""",
 """  healRosterHidden();                         // 空函数（2026-09-20 起身份不影响显示，「已移除」只能手动恢复）"""),
]


def apply(path, pairs, crlf=True):
    raw = open(path, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    txt = raw.decode('utf-8-sig').replace('\r\n', '\n')
    fails = []
    for i, (old, new) in enumerate(pairs):
        n = txt.count(old)
        if n != 1:
            fails.append((i, n, old.splitlines()[0][:70]))
            continue
        txt = txt.replace(old, new, 1)
    if fails:
        print('❌ %s：' % path)
        for i, n, s in fails:
            print('   #%d 出现 %d 次: %s' % (i, n, s))
        return False
    data = txt.replace('\n', '\r\n') if crlf else txt
    open(path, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + data.encode('utf-8'))
    print('✅ %s：%d 处替换完成' % (path, len(pairs)))
    return True


sys.exit(0 if apply(os.path.join(HERE, 'assets', 'app.js'), APP) else 1)
