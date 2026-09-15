# -*- coding: utf-8 -*-
"""把 使用说明.txt 转成 Markdown（桌面 + 仓库各一份），并单独出一份「网址」md
   · 【一】→ ## 一、…（章节变标题）
   · 装饰横线 ── xxx ──── → ### xxx
   · 4 空格缩进 → 2 空格（否则 Markdown 会当成代码块）
"""
import io, os, re

PROJ = r'E:\Desktop\麦田\麦田守望数据中心'
DESK = r'E:\Desktop'
SRC = os.path.join(PROJ, '使用说明.txt')
raw = io.open(SRC, encoding='utf-8-sig').read().replace('\r\n', '\n')
lines = raw.split('\n')

# ── 网址清单（从说明书【一】里抽 + 补充）──
URLS = [
    ('展示版（发群里给大家看 · 只读）', 'https://zl4639574-bit.github.io/maitian-running/'),
    ('成绩上报（发给队员填 · 不用登录）', 'https://zl4639574-bit.github.io/maitian-running/report/'),
    ('队长版（你自己改数据用）', 'https://zl4639574-bit.github.io/maitian-running/captain/'),
    ('说明书（手机也能直接打开）', 'https://zl4639574-bit.github.io/maitian-running/guide.txt'),
    ('给别人用 · 开通步骤（发给新队长看）', 'https://zl4639574-bit.github.io/maitian-running/other-captains.txt'),
    ('GitHub 仓库（数据提交记录都在这里）', 'https://github.com/zl4639574-bit/maitian-running'),
]

# ── 正文转换 ──
out = []
for ln in lines:
    s = ln.rstrip()
    # 开头那块装饰横幅 → 标题块
    if set(s.strip()) <= set('═') and s.strip():
        continue
    if '数据中心 —— 使用说明' in s or '（两个版本：展示版 + 队长版）' in s:
        continue
    m = re.match(r'^【([零一二三四五六七八九十]+)】(.*)$', s.strip())   # 只把'【六】'这种章节号当标题，'【第一次】'这类保持原文
    if m:
        out.append('')
        out.append('## %s、%s' % (m.group(1), m.group(2).strip(' ——-')))
        out.append('')
        continue
    m2 = re.match(r'^\s*──\s*(.+?)\s*─*\s*$', s)
    if m2:
        out.append('')
        out.append('### %s' % m2.group(1))
        continue
    if set(s.strip()) <= set('─') and s.strip():
        out.append('---')
        continue
    # 缩进压缩：每 4 个空格 → 2 个，且最多 3 个（4 个以上 Markdown 会当成代码块）
    if s:
        lead = len(s) - len(s.lstrip(' '))
        if lead:
            s = ' ' * min(int(lead / 2), 3) + s.lstrip(' ')
    out.append(s)
body = '\n'.join(out)
body = re.sub(r'\n{4,}', '\n\n\n', body).strip()

HEAD = u"""# 麦田守望长跑队 · 数据中心

> 西北农林科技大学 麦田守望长跑队 —— 队伍数据（名册 / 成绩榜 / 照片墙 / 荣誉）在线网页
> 两个版本：**展示版**（只读，发群里）＋ **队长版**（可改数据并同步上线）

## 快速链接

| 用途 | 网址 |
|---|---|
""" + '\n'.join('| %s | %s |' % (k, v) for k, v in URLS) + u"""

> ⚠️ 队长版的「专用链接」里带写入令牌（长这样：`.../captain/#t=...`），
> 只能发给你信任的队长，**不要发群里、不要写进任何文件**。丢了就用队长版的「一键打开建令牌页面」重做一个。

---

"""

md = HEAD + body + '\n'
md_path = os.path.join(DESK, '麦田守望长跑队_使用说明.md')
io.open(md_path, 'w', encoding='utf-8', newline='').write(md)

# 仓库里也放一份（GitHub 网页上能直接渲染阅读，方便转给别的队长）
repo_path = os.path.join(PROJ, '使用说明.md')
io.open(repo_path, 'w', encoding='utf-8', newline='').write(md)

# ── 单独的「网址」md ──
u = u"""# 麦田守望长跑队 · 网址清单

> 手机直接打开，不用 VPN、不用装 App。建议存成书签或加到桌面。

## 正式入口

| 用途 | 网址 | 谁能改数据 |
|---|---|---|
| **展示版**（给全队/外界看 · 只读） | https://zl4639574-bit.github.io/maitian-running/ | 没人能改（只读） |
| **队长版**（改数据、传照片、同步上线） | https://zl4639574-bit.github.io/maitian-running/captain/ | 有令牌的队长 |
| **成绩上报**（发给队员填，不用登录） | https://zl4639574-bit.github.io/maitian-running/report/ | 谁都能填，但只是填给自己看，要交给队长导入 |

## 说明与帮助

| 内容 | 网址 |
|---|---|
| 使用说明（纯文本，手机可开） | https://zl4639574-bit.github.io/maitian-running/guide.txt |
| 给别人用 · 怎么开通写权限 | https://zl4639574-bit.github.io/maitian-running/other-captains.txt |
| 数据仓库（提交记录 / 回滚在这里） | https://github.com/zl4639574-bit/maitian-running |

## 两个版本的区别

- **展示版**：只有「总览 / 成绩榜 / 队员名册 / 照片墙 / 荣誉与资料」这些看的内容，**没有管理入口**，发给队友、发朋友圈都安全。
- **队长版**：多出「上传成绩 / 数据管理」两个入口，能改名册、录成绩、传照片、单独加个人最好成绩、完善队员信息，改完点「同步」就上线。

## 队长版的登录方式（两种，任选）

1. **专用链接**：`https://zl4639574-bit.github.io/maitian-running/captain/#t=...`
   打开即已填好用户名/仓库/令牌，点一次「记住到这台设备」以后就不用管了。
   ⚠️ 链接里带令牌 = 谁拿到谁能改数据，**只发给自己和信任的队长，不要发群、不要存进文件或截图**。
2. **自己的令牌**：别人用自己 GitHub 账号建一个只对本仓库有权限的令牌，粘进队长版即可。
   步骤见：https://zl4639574-bit.github.io/maitian-running/other-captains.txt

## 常见问题

| 问题 | 答案 |
|---|---|
| 手机上打不开？ | 用手机自带浏览器打开（微信里点「···→ 在浏览器打开」）；网址不会变，存成书签即可 |
| 页面显示的数据不是最新的？ | 展示版每 30 秒自动检查一次；也可下拉刷新。页头会显示「数据更新于 xx-xx xx:xx」 |
| 改了数据别人看不到？ | 队长版改完要点「同步我的修改到线上」，约 1 分钟内所有人可见 |
| 电脑上双击打不开 .md？ | 用记事本/VS Code 打开，或者看同目录的 `麦田守望长跑队_使用说明.txt` |
| 想要数据备份？ | 线上仓库就是完整备份（含全部历史），本机也有一份工作副本 |
"""
u_path = os.path.join(DESK, '麦田守望长跑队_网址.md')
io.open(u_path, 'w', encoding='utf-8', newline='').write(u)

# ── 纯文本合并版（.md 双击打不开，这份是给双击看的；正文沿用原始 txt，不做二次加工）──
plain_urls = u"""════════════════════════════════════════════════════════════
  麦田守望长跑队 · 网址 + 使用说明
  （同内容的 Markdown 版：麦田守望长跑队_网址.md、麦田守望长跑队_使用说明.md）
  生成时间：2026-09-15    网址永久有效，存成书签即可
════════════════════════════════════════════════════════════


【网址清单】（手机直接打开，不用 VPN；建议加到主屏幕）

  展示版（给全队/外界看 · 只读）
    https://zl4639574-bit.github.io/maitian-running/

  队长版（改数据、传照片、同步上线 —— 需要令牌）
    https://zl4639574-bit.github.io/maitian-running/captain/

  使用说明（纯文本，手机也能直接打开）
    https://zl4639574-bit.github.io/maitian-running/guide.txt

  给别人用 · 怎么给新队长开通写权限
    https://zl4639574-bit.github.io/maitian-running/other-captains.txt

  GitHub 仓库（所有提交记录 / 数据回滚在这里）
    https://github.com/zl4639574-bit/maitian-running

  ⚠ 队长版的「专用链接」里带写入令牌（长这样：.../captain/#t=...），
    只能发给你信任的队长，不要发群里、不要写进任何文件。丢了就在队长版里重做一个。


════════════════════════════════════════════════════════════
"""
io.open(os.path.join(DESK, '麦田守望长跑队_网址与使用说明.txt'), 'w',
        encoding='utf-8-sig', newline='\r\n').write(plain_urls + raw.lstrip('\ufeff'))

print('已生成：')
for p in (md_path, u_path, os.path.join(DESK, '麦田守望长跑队_网址与使用说明.txt'), repo_path):
    print('  %-56s %6.1f KB' % (p, os.path.getsize(p) / 1024.0))
print('\nmarkdown 结构自检：')
print('  ## 章节数 =', md.count('\n## '), '｜ ### 小节数 =', md.count('\n### '))
bad = [l for l in md.split('\n') if l.startswith('    ')]
print('  还有 4 空格缩进（会被当代码块）的行数 =', len(bad))
if bad:
    print('   例：', bad[:3])
