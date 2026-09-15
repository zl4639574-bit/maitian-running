# -*- coding: utf-8 -*-
"""① 生成上报页二维码 images/report_qr.png（队长发群里，队员扫一下就能填）
   ② 说明书加两节说明：[十四] 队员怎么上报 / [十五] 队长怎么把上报导进来
"""
import io, os

HERE = os.path.dirname(os.path.abspath(__file__))
URL = 'https://zl4639574-bit.github.io/maitian-running/report/'

# ① 二维码
try:
    import qrcode
    qr = qrcode.QRCode(version=None, box_size=12, border=2,
                       error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(URL)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#2F6B39', back_color='white')
    out = os.path.join(HERE, 'images', 'report_qr.png')
    img.save(out)
    print('二维码已生成 images/report_qr.png（%d 字节）' % os.path.getsize(out))
except ImportError:
    print('⚠ 没装 qrcode 库，跳过二维码（不影响网页功能）')

# ② 说明书
SEC = u"""


════════════════════════════════════════════════════════════════════
【十四】队员怎么上报成绩（收集入口）
════════════════════════════════════════════════════════════════════

  上报网址（发给队员，手机直接打开，不用 VPN、不用登录）
    https://zl4639574-bit.github.io/maitian-running/report/
    （队长版「上传成绩」页也有这个网址；images/report_qr.png 是二维码，可以直接发群里）

  队员怎么做：
    ① 打开网址 → 选项目（5000 米 / 半马 / 全马…）→ 填 姓名、成绩、日期、赛事 → 点「添加到我的成绩」
       （填错了在下面列表里点删除重填；可以一次填好几条）
    ② 拉到底点「复制成上报文本（发队长）」，或者点「导出 CSV」存成小文件
    ③ 把这行文字（或文件）发到队群，或者直接发给队长
    特点：不联网、不上传任何东西、不需要密码；填的内容只存在他自己手机里，关掉浏览器前记得复制走。

  ⚠️ 不用给队员配「访问令牌」—— 上报页只负责把成绩整理成标准格式，写入线上仍然由队长做。

【十五】队长怎么把队员上报的成绩导进来
    · 队员在微信里发来的那几行文字：队长版 →「上传成绩」→「② 粘贴文本导入」→ 直接粘进去
      → 点「解析并预览」（会标出谁是队员、谁是非队员）→ 点「把这 N 条加进来」
    · 队员发来的是 CSV 文件：用上面的「② 批量导入 Excel / CSV」拖进来即可（列会自动认）
    · 接着：数据管理 → 比赛成绩 → 新建一场比赛 → 点「把本机录入的成绩并进这场比赛」→ 同步上线
    · 队员上报的文字长这样（带表头，所以两边的列能自动对上）：
        麦田守望 · 成绩上报（2026.09.15）
        姓名    项目    成绩    日期    赛事/名次
        张三    5000米  18:35   2026.09.15      校运会
"""
for fn in ('使用说明.txt', 'guide.txt'):
    p = os.path.join(HERE, fn)
    s = io.open(p, encoding='utf-8-sig').read()
    if u'【十四】' in s:
        print(fn, '已写过，跳过')
        continue
    io.open(p, 'w', encoding='utf-8-sig', newline='').write(s.rstrip() + SEC.replace('\n', '\r\n'))
    print(fn, '已追加【十四】【十五】')
