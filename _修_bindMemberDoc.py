# -*- coding: utf-8 -*-
"""把嵌套的 bindMemberDoc 提到 bindManage 里（用花括号计数找块尾，避免锚点误差）"""
import io, os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'app.js')
s = io.open(P, encoding='utf-8').read()
key = 'function bindMemberDoc() {'
i = s.index(key)
k = s.index('{', i)
depth, j = 0, k
while True:
    if s[j] == '{':
        depth += 1
    elif s[j] == '}':
        depth -= 1
        if depth == 0:
            break
    j += 1
j += 1                                    # 含最后那个 }
block = s[i:j]
body = block[len(key):-1]                 # 去掉包裹与最后的 }
assert 'btnDocParse' in body, '块内容不对'
s2 = s[:i] + s[j:]
assert '  bindMemberDoc();' in s2
s2 = s2.replace('  bindMemberDoc();', body.rstrip(), 1)
io.open(P, 'w', encoding='utf-8', newline='').write(s2)
print('已内联；剩余 bindMemberDoc 次数 =', s2.count('bindMemberDoc'))
print('  bindManage 起始行 ok =', 'function bindManage() {' in s2)
print('  btnDocParse 绑定行数 =', s2.count("$('#btnDocParse')"))
