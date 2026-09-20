# -*- coding: utf-8 -*-
"""把同一批说明书改动套到纯文本版（使用说明.txt / guide.txt）：
这两个文件内容一样，但缩进和 .md 不同（同义段落缩进多几格），所以按"去掉行首空白后的整行序列"定位，
再按目标文件自己的缩进风格重排新文本。
"""
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("patchmd", os.path.join(HERE, "_patch_说明书_名册全体显示.py"))
pm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pm)
PAIRS = pm.PAIRS


def indent_of(s):
    return len(s) - len(s.lstrip(' '))


def reindent(old_block, new_block, first_ind, cont_ind):
    """新文本按目标文件的两档缩进重排：与旧首行同缩进的 → first_ind，更深的 → cont_ind"""
    old_lines = [l for l in old_block.split('\n') if l.strip()]
    base = indent_of(old_lines[0])
    out = []
    for l in new_block.split('\n'):
        if not l.strip():
            out.append('')
            continue
        out.append((' ' * (first_ind if indent_of(l) == base else cont_ind)) + l.strip())
    return out


def apply_txt(path):
    raw = open(path, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    txt = raw.decode('utf-8-sig')
    crlf = '\r\n' in txt
    lines = txt.replace('\r\n', '\n').split('\n')
    fails = []
    for i, (old, new) in enumerate(PAIRS):
        sig = [l.strip() for l in old.split('\n') if l.strip()]
        hit = None
        for j in range(len(lines) - len(sig) + 1):
            if all(lines[j + k].strip() == sig[k] for k in range(len(sig))):
                if hit is not None:
                    hit = 'dup'
                    break
                hit = j
        if hit is None or hit == 'dup':
            fails.append((i, '未找到' if hit is None else '匹配到多段', sig[0][:50]))
            continue
        first_ind = indent_of(lines[hit])
        cont_ind = max([indent_of(lines[hit + k]) for k in range(1, len(sig))] + [first_ind + 2])
        new_lines = reindent(old, new, first_ind, cont_ind)
        lines[hit:hit + len(sig)] = new_lines
    if fails:
        print('❌ %s：' % os.path.basename(path))
        for i, why, s in fails:
            print('   #%d %s: %s' % (i, why, s))
        return False
    out = '\n'.join(lines)
    if crlf:
        out = out.replace('\n', '\r\n')
    open(path, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + out.encode('utf-8'))
    print('✅ %s：%d 段替换完成' % (os.path.basename(path), len(PAIRS)))
    return True


ok = True
for f in ['使用说明.txt', 'guide.txt']:
    ok &= apply_txt(os.path.join(HERE, f))
sys.exit(0 if ok else 1)
