# -*- coding: utf-8 -*-
"""更新说明书：①名册口径改成 57 人 ②加「给别人用」章节 ③放一份 ASCII 文件名的副本给手机点开"""
import io, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '给别人用_开通说明.txt')

# ① ASCII 文件名的副本（手机点开更省事）
shutil.copy2(SRC, os.path.join(HERE, 'other-captains.txt'))

OLD1 = '  · 队员名册只保留标记为「正式」和「预备」的 74 人'
NEW1 = ('  · 队员名册 = 《2023年在校正式队员信息表》里的 57 名正式队员（2026-09-15 起）\r\n'
        '    原来另外显示的 18 人（14 预备 + 4 正式）先移出显示，等导入预备队员名单后再一起更新')

OLD2 = '      使用说明.txt        本文件'
NEW2 = ('      使用说明.txt        本文件\r\n'
        '      给别人用_开通说明.txt / other-captains.txt   给别的队长开通写权限的步骤\r\n'
        '                          （加协作者 → 他建自己的令牌 → 队长版里粘令牌）')

NEWSEC = ('\r\n\r\n【十一】别人也能改数据吗（多个队长一起维护）\r\n\r\n'
          '  可以，但要给"写入权"——两种给法：\r\n'
          '    · 让他用自己的 GitHub 账号建一个精细令牌（只勾 maitian-running，Contents 读写），\r\n'
          '      这样仓库提交记录里能看出是谁改的，你也能随时单独撤销他。\r\n'
          '      详细步骤：见同目录「给别人用_开通说明.txt」，手机可直接打开\r\n'
          '      https://zl4639574-bit.github.io/maitian-running/other-captains.txt\r\n'
          '    · 或者你把队长版的「专用链接」发给他（最省事，但等于把写入权交给他，别发大群）。\r\n\r\n'
          '  提醒：两个人同时改同一块数据时，后保存的会覆盖先保存的；\r\n'
          '        批量修改（改身份、导入成绩）尽量一个人做完再让另一个人动。\r\n')

for fn in ('使用说明.txt', 'guide.txt'):
    p = os.path.join(HERE, fn)
    s = io.open(p, encoding='utf-8-sig').read()
    n = 0
    if OLD1 in s:
        s = s.replace(OLD1, NEW1); n += 1
    if OLD2 in s:
        s = s.replace(OLD2, NEW2); n += 1
    if '【十一】' not in s:
        s = s.rstrip('\r\n') + NEWSEC; n += 1
    io.open(p, 'w', encoding='utf-8-sig', newline='').write(s)
    print('%s：改动 %d 处，现 %d 行' % (fn, n, len(s.splitlines())))

for fn in ('给别人用_开通说明.txt', 'other-captains.txt'):
    b = io.open(os.path.join(HERE, fn), 'rb').read()
    ok = b.startswith(b'\xef\xbb\xbf')
    print('%-26s %6d 字节  BOM=%s' % (fn, len(b), ok))
