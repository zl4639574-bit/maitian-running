# -*- coding: utf-8 -*-
"""把说明书定稿：使用说明.txt → UTF-8 BOM + CRLF，并同步一份到 guide.txt（线上的纯文本版）"""
import io, os, shutil

PROJ = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(PROJ, '使用说明.txt')
raw = io.open(SRC, encoding='utf-8-sig').read().replace('\r\n', '\n').replace('\r', '\n')
out = raw.replace('\n', '\r\n')
io.open(SRC, 'w', encoding='utf-8-sig', newline='').write(out)
shutil.copyfile(SRC, os.path.join(PROJ, 'guide.txt'))
b = io.open(SRC, 'rb').read()
print('使用说明.txt：BOM=%s  CRLF=%d  行数=%d  大小=%.1fKB'
      % (b[:3] == b'\xef\xbb\xbf', b.count(b'\r\n'), out.count('\r\n') + 1, len(b) / 1024.0))
b2 = io.open(os.path.join(PROJ, 'guide.txt'), 'rb').read()
print('guide.txt  ：BOM=%s  CRLF=%d  与使用说明一致=%s' % (b2[:3] == b'\xef\xbb\xbf', b2.count(b'\r\n'), b2 == b))
