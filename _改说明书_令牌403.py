# -*- coding: utf-8 -*-
"""说明书补：403 报错自己怎么查（令牌体检）"""
import io, os

HERE = os.path.dirname(os.path.abspath(__file__))
SEC = u"""


════════════════════════════════════════════════════════════════════
【十六】提交/同步报 403「Resource not accessible by permission token」
════════════════════════════════════════════════════════════════════

  含义：GitHub 说"这个令牌不许写这个仓库"。99% 是令牌设错了，不是你操作错。
  最快的自查：队长版 →「数据管理」→「同步」→ 点「检查令牌权限（只看不改）」
    · 会显示：令牌属于哪个账号、能不能读到仓库、有没有写入权限，缺什么直接写出来；
    · 如果显示「能读到仓库，但没有写入权限」——按它给的①②两处改：
        ① 令牌页面 → Repository access → Only select repositories → 勾上 zl4639574-bit/maitian-running
        ② 同一页面 → Permissions → Repository permissions → Contents → 选 Read and write
      改完必须**重新生成一个令牌**（旧令牌不会自动升级），把新令牌粘回「访问令牌」→ 保存设置；
    · 如果显示令牌属于别人（不是你自己的账号）——先让仓库主人在
      Settings → Collaborators 里把这个人加为协作者，然后再用那个账号生成令牌；
    · 如果显示「令牌无效」（401）——令牌过期或被删了，重新生成一个即可。

  日常拿不准哪个按钮会写数据：只有「同步我的修改到线上」「立即同步到线上」「测试同步」会写，
  「检查令牌权限」只读不写，随便点。
"""
for fn in ('使用说明.txt', 'guide.txt'):
    p = os.path.join(HERE, fn)
    s = io.open(p, encoding='utf-8-sig').read()
    if u'【十六】' in s:
        print(fn, '已写过，跳过')
        continue
    io.open(p, 'w', encoding='utf-8-sig', newline='').write(s.rstrip() + SEC.replace('\n', '\r\n'))
    print(fn, '已追加【十六】')
