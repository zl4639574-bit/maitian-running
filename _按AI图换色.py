# -*- coding: utf-8 -*-
"""按即梦生成的线条图（队徽线稿版）重调整站配色 + 换背景图
   图里线条核心色：绿 #1F461F~#2D542D、金 #BCA944；底色 #FAFAF8
   目标：柔和的鼠尾草绿 + 古金，白底、低对比，和线条画气质一致
"""
import io, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'assets', 'style.css')
s = io.open(P, encoding='utf-8').read().replace('\r\n', '\n')
done = []


def rep(old, new, label, cnt=1):
    global s
    n = s.count(old)
    assert n == cnt, '✗ %s：期望 %d 处，实际 %d 处' % (label, cnt, n)
    s = s.replace(old, new)
    done.append(label)


# ① 变量：换成这张图的色系
rep(""":root{
  /* ===== 配色取自队徽（images/logo.jpg）=====
     主绿 #14781F / #178522 / #5D9A62 / #A5D0A8
     麦金 #E9C821 / #E5D45F      底色米白 #FBFDFA            */
  --green:#14781F;        /* 主绿：按钮、链接、数字、选中态 */
  --green-2:#178522;      /* 亮绿：渐变上端、描边 */
  --green-3:#5D9A62;      /* 中绿：次级线条 */
  --green-soft:#EAF4E7;   /* 浅绿底：徽章、悬停 */
  --green-line:#DCEBD8;   /* 卡片描边 */
  --wheat:#C9A600;        /* 深金：金色文字（保证对比度） */
  --wheat-bright:#E9C821; /* 亮金：奖牌、强调底 */
  --wheat-soft:#FBF6DC;   /* 浅金底：提示条 */
  --bg:#F7FAF5; --card:#ffffff; --t1:#12261A; --t2:#5F6F62; --t3:#9AAAA0;
  --line:#E6EDE2;
  --field:#14781F; --blue:#1E7A6B; --red:#C0392B; --orange:#E08A00;
  --gold:#D9A800; --silver:#9AA79C; --bronze:#B0793A;
  --r:18px; --shadow:0 4px 14px rgba(20,120,31,.07);
}""",
    """:root{
  /* ===== 配色取自背景线条画（即梦生成 · 队徽线稿版）=====
     线条核心色：绿 #1F461F→#2D542D、金 #BCA944；画面底色 #FAFAF8
     整体走"柔和鼠尾草绿 + 古金"，白底低对比             */
  --green:#2F6B39;        /* 主绿：按钮、链接、数字、选中态（白底对比 5.4:1） */
  --green-2:#3E8A48;      /* 亮绿：渐变上端 */
  --green-3:#7FA786;      /* 中绿：次级线条、名次圆标 */
  --green-soft:#EDF3E9;   /* 浅绿底：徽章、悬停 */
  --green-line:#DDE7D7;   /* 卡片描边 */
  --wheat:#8A7314;        /* 深金：金色文字（白底 5.1:1） */
  --wheat-bright:#D6C05A; /* 亮金：奖牌、强调底、时间轴圆点 */
  --wheat-soft:#F8F4DC;   /* 浅金底：提示条 */
  --bg:#FAFAF7; --card:#ffffff; --t1:#1E2A1B; --t2:#66705F; --t3:#98A192;
  --line:#E7EBE0;
  --field:#2F6B39; --blue:#4C7A6B; --red:#C0392B; --orange:#D08A2A;
  --gold:#B8930F; --silver:#9AA79C; --bronze:#A9762F;
  --r:18px; --shadow:0 4px 14px rgba(47,107,57,.06);
}""", '① 变量换成线条画色系')

# ② 底色：极淡的暖白到浅绿渐变（配合线条图的白底）
rep("""html{background:var(--bg)}""",
    """html{background:linear-gradient(#FDFDFB 0%, #FAFAF7 55%, #F0F5EA 100%)}""",
    '② 底色改暖白→浅绿渐变')

# ③ 背景图换成 AI 线条图（柔化版，固定在视口底部，等比缩放不裁切）
rep("""/* 背景图：按队徽配色生成的麦田（images/bg_field.svg，另有 bg_night / bg_plain 两个备选） */
body::before{
  content:''; position:fixed; inset:0; z-index:-1; pointer-events:none;
  background:url('../images/bg_field.svg') center bottom / cover no-repeat;
}""",
    """/* 背景图：即梦生成的队徽线条画（bg_ai_soft.jpg = 线条柔化 45% 版，另存 bg_ai.jpg 原强度）
   用 contain 等比缩放、居中偏下，不裁切图形；换图只改这一处文件名即可 */
body::before{
  content:''; position:fixed; inset:0; z-index:-1; pointer-events:none;
  background-image:url('../images/bg_ai_soft.jpg');
  background-repeat:no-repeat;
  background-position:center bottom 6vh;
  background-size:contain;
}
@media(min-width:721px){
  body::before{background-position:center bottom 4vh; background-size:contain}
}""", '③ 背景图换成 AI 线条图')

io.open(P, 'w', encoding='utf-8', newline='').write(s.replace('\n', '\r\n'))
print('\n'.join('   ' + d for d in done))
print('\nstyle.css 已更新（背景图 = images/bg_ai_soft.jpg）')
print('换回原强度版：把 style.css 里 bg_ai_soft.jpg 改成 bg_ai.jpg')
print('换回麦田矢量图：改成 ../images/bg_field.svg 并把 background-size 改回 cover')
