# -*- coding: utf-8 -*-
"""把 AI 生成的背景图一键上线（压缩 + 可选白纱柔化 + 换 style.css + 可选推送）

用法（在本文件夹下运行）：
  python 上线背景图.py 新背景.jpg                    # 手机竖版
  python 上线背景图.py 新背景.jpg --wide 横版.jpg     # 手机竖版 + 电脑横版
  python 上线背景图.py 新背景.jpg --veil 0.45         # 上半部再压一层白色柔纱（文字更清楚）
  python 上线背景图.py 新背景.jpg --push              # 改完顺便提交推送（需能连上 github）

说明：
  · 竖版压到宽 1440、横版压到宽 2400、JPEG 质量 82（手机加载快，肉眼几乎看不出差别）
  · --veil 会在图片上部叠一层从上到下渐隐的白色（0~1，建议 0.35~0.5），
    保证任何屏宽下压在上面的文字都清楚；不想要就不加这个参数
  · 电脑宽屏用 media query 换横版图，手机继续用竖版
"""
import argparse, io, os, re, shutil, subprocess, sys

try:
    from PIL import Image
except ImportError:
    sys.exit('需要 Pillow：C:\\Users\\15749\\.venvs\\bib\\Scripts\\python.exe 里已装，用那个 python 跑本脚本')

HERE = os.path.dirname(os.path.abspath(__file__))
CSS = os.path.join(HERE, 'assets', 'style.css')
IMG = os.path.join(HERE, 'images')


def prep(src, dst, max_w, veil=0.0):
    im = Image.open(src).convert('RGB')
    w, h = im.size
    if w > max_w:
        im = im.resize((max_w, int(h * max_w / float(w))), Image.LANCZOS)
    if veil > 0:
        w, h = im.size
        layer = Image.new('RGBA', (w, h))
        px = layer.load()
        fade_to = int(h * 0.62)                       # 到 62% 高度处白纱完全消失
        for y in range(h):
            a = int(255 * veil * (1 - y / float(fade_to))) if y < fade_to else 0
            if a <= 0:
                break
            for x in range(0, w, 1):
                px[x, y] = (255, 255, 255, a)
        im = Image.alpha_composite(im.convert('RGBA'), layer).convert('RGB')
    im.save(dst, 'JPEG', quality=82, optimize=True, progressive=True)
    return im.size, os.path.getsize(dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('portrait', help='手机竖版背景图路径')
    ap.add_argument('--wide', help='电脑横版背景图路径（可选）')
    ap.add_argument('--veil', type=float, default=0.0, help='上部白色柔纱强度 0~1（建议 0.35~0.5）')
    ap.add_argument('--push', action='store_true', help='改完提交并推送')
    a = ap.parse_args()

    p_out = os.path.join(IMG, 'bg_ai.jpg')
    size, n = prep(a.portrait, p_out, 1440, a.veil)
    print('① 竖版背景 → images/bg_ai.jpg  %dx%d  %.0f KB' % (size[0], size[1], n / 1024.0))
    wide_name = None
    if a.wide:
        wide_name = 'bg_ai_wide.jpg'
        size2, n2 = prep(a.wide, os.path.join(IMG, wide_name), 2400, a.veil)
        print('② 电脑横版 → images/%s  %dx%d  %.0f KB' % (wide_name, size2[0], size2[1], n2 / 1024.0))

    css = io.open(CSS, encoding='utf-8').read()
    bak = CSS + '.bak'
    if not os.path.exists(bak):
        shutil.copy2(CSS, bak)
    new_line = "background:url('../images/bg_ai.jpg') center bottom / cover no-repeat;"
    css2, k = re.subn(r"background:url\('\.\./images/[^']+'\) center bottom / cover no-repeat;", new_line, css)
    assert k == 1, 'style.css 里没找到背景图那一行（期望 1 处，实际 %d 处）' % k
    q = "@media(min-width:721px){body::before{background-image:url('../images/%s') !important}}" % wide_name
    if wide_name:
        if 'body::before{background-image' in css2:
            css2 = re.sub(r"@media\(min-width:721px\)\{body::before\{background-image:url\('\.\./images/[^']+'\) !important\}\}",
                          q, css2)
        else:
            css2 = css2.replace(new_line, new_line + "\n" + q, 1)
        print('③ 电脑宽屏走横版图（已写入 media query）')
    else:
        css2 = re.sub(r"\n@media\(min-width:721px\)\{body::before\{background-image:url\('\.\./images/[^']+'\) ![^}]*\}\}", '', css2)
    io.open(CSS, 'w', encoding='utf-8', newline='').write(css2)
    print('④ style.css 已指向新背景（原文件备份在 style.css.bak）')

    if a.push:
        env = dict(os.environ, HTTPS_PROXY=os.environ.get('HTTPS_PROXY', 'http://127.0.0.1:7897'))
        for cmd in (['git', 'add', 'assets/style.css', 'images/bg_ai.jpg'] + (['images/' + wide_name] if wide_name else []),
                    ['git', 'commit', '-q', '-m', '背景图换成 AI 生成版（%s）' % os.path.basename(a.portrait)],
                    ['git', 'pull', '--no-rebase', '-q'], ['git', 'push']):
            r = subprocess.run(cmd, cwd=HERE, env=env, capture_output=True, text=True)
            print('   $ %s → %s %s' % (' '.join(cmd), r.returncode, (r.stderr or r.stdout).strip()[-120:]))
    else:
        print('\n想上线就执行（或直接让我来）：')
        print('  cd "%s"' % HERE)
        print('  git add assets/style.css images/bg_ai.jpg%s && git commit -m "换背景图" && git push' % (' images/' + wide_name if wide_name else ''))


if __name__ == '__main__':
    main()
