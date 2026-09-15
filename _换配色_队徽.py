# -*- coding: utf-8 -*-
"""按队徽配色生成背景图（3 个方案）+ 把整站配色换成队徽色系
   队徽取色：绿 #14781F / #178522 / #5D9A62 / #A5D0A8，麦金 #E9C821 / #E5D45F，底 #FBFDFA
"""
import io, os

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, 'images')
G1, G2, G3, G4 = '#14781F', '#178522', '#5D9A62', '#A5D0A8'
Y1, Y2 = '#E9C821', '#E5D45F'

# ── 方案 A：麦田·晨光（米白底 + 底部麦浪 + 中央淡金晕 + 淡圆环，呼应队徽）──
SVG_A = u"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 1600" preserveAspectRatio="xMidYMax slice">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FDFEFB"/><stop offset=".55" stop-color="#F5FAF1"/><stop offset="1" stop-color="#EAF4E5"/>
    </linearGradient>
    <radialGradient id="sun" cx=".5" cy=".78" r=".55">
      <stop offset="0" stop-color="%s" stop-opacity=".34"/><stop offset="1" stop-color="%s" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="w1" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="%s" stop-opacity=".22"/><stop offset="1" stop-color="%s" stop-opacity=".05"/>
    </linearGradient>
    <linearGradient id="w2" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="%s" stop-opacity=".34"/><stop offset="1" stop-color="%s" stop-opacity=".07"/>
    </linearGradient>
  </defs>
  <rect width="1440" height="1600" fill="url(#sky)"/>
  <!-- 呼应队徽的大圆环 -->
  <circle cx="720" cy="560" r="430" fill="none" stroke="%s" stroke-width="26" opacity=".10"/>
  <circle cx="720" cy="560" r="360" fill="none" stroke="%s" stroke-width="10" opacity=".07"/>
  <!-- 中央淡金晕（麦穗的暖光） -->
  <rect width="1440" height="1600" fill="url(#sun)"/>
  <!-- 底部麦浪：由远到近四层 -->
  <path d="M0 1180 C 240 1120 420 1240 720 1190 C 1020 1140 1200 1250 1440 1196 L1440 1600 L0 1600 Z" fill="%s" opacity=".10"/>
  <path d="M0 1260 C 260 1206 470 1318 720 1272 C 980 1224 1210 1330 1440 1276 L1440 1600 L0 1600 Z" fill="url(#w1)"/>
  <path d="M0 1360 C 300 1310 500 1412 760 1370 C 1020 1328 1230 1424 1440 1376 L1440 1600 L0 1600 Z" fill="url(#w2)"/>
  <path d="M0 1470 C 320 1428 560 1518 820 1482 C 1080 1446 1250 1524 1440 1486 L1440 1600 L0 1600 Z" fill="%s" opacity=".16"/>
  <!-- 麦秆感极淡斜纹 -->
  <g stroke="%s" stroke-width="2" opacity=".05">
    <path d="M120 1600 L200 1250"/><path d="M300 1600 L360 1300"/><path d="M1140 1600 L1080 1290"/>
    <path d="M1320 1600 L1250 1260"/><path d="M540 1600 L600 1360"/><path d="M900 1600 L840 1350"/>
  </g>
</svg>
""" % (Y1, Y1, G2, G2, G1, G1, G2, G1, G2, G1, G2)

# ── 方案 B：深绿·夜色（深底浅字风格备用）──
SVG_B = u"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 1600" preserveAspectRatio="xMidYMax slice">
  <defs>
    <linearGradient id="night" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0D2A15"/><stop offset=".6" stop-color="#0A2111"/><stop offset="1" stop-color="#07180C"/>
    </linearGradient>
    <radialGradient id="moon" cx=".5" cy=".7" r=".5">
      <stop offset="0" stop-color="%s" stop-opacity=".22"/><stop offset="1" stop-color="%s" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1440" height="1600" fill="url(#night)"/>
  <circle cx="720" cy="600" r="430" fill="none" stroke="%s" stroke-width="26" opacity=".14"/>
  <rect width="1440" height="1600" fill="url(#moon)"/>
  <path d="M0 1260 C 260 1206 470 1318 720 1272 C 980 1224 1210 1330 1440 1276 L1440 1600 L0 1600 Z" fill="%s" opacity=".22"/>
  <path d="M0 1380 C 300 1330 500 1430 760 1390 C 1020 1348 1230 1440 1440 1396 L1440 1600 L0 1600 Z" fill="%s" opacity=".34"/>
  <path d="M0 1490 C 320 1450 560 1530 820 1496 C 1080 1462 1250 1534 1440 1500 L1440 1600 L0 1600 Z" fill="%s" opacity=".5"/>
</svg>
""" % (Y1, Y1, G2, G2, G3, G1)

# ── 方案 C：极简（几乎纯白，只在底部留一缕麦金）──
SVG_C = u"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 1600" preserveAspectRatio="xMidYMax slice">
  <defs>
    <linearGradient id="p" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#F7FBF4"/>
    </linearGradient>
    <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="%s" stop-opacity=".13"/><stop offset="1" stop-color="%s" stop-opacity=".02"/>
    </linearGradient>
  </defs>
  <rect width="1440" height="1600" fill="url(#p)"/>
  <circle cx="720" cy="520" r="440" fill="none" stroke="%s" stroke-width="18" opacity=".05"/>
  <path d="M0 1440 C 340 1400 620 1490 880 1452 C 1120 1418 1290 1480 1440 1452 L1440 1600 L0 1600 Z" fill="url(#g)"/>
</svg>
""" % (G2, G2, G2)

for name, svg in (('bg_field.svg', SVG_A), ('bg_night.svg', SVG_B), ('bg_plain.svg', SVG_C)):
    io.open(os.path.join(IMG, name), 'w', encoding='utf-8', newline='\n').write(svg)
    print('生成', name, os.path.getsize(os.path.join(IMG, name)), '字节')

# ── 换配色：style.css ──
P = os.path.join(HERE, 'assets', 'style.css')
s = io.open(P, encoding='utf-8').read()
s = s.replace('\r\n', '\n')
done = []


def rep(old, new, label, cnt=1):
    global s
    n = s.count(old)
    assert n == cnt, '✗ %s：期望 %d 处，实际 %d 处' % (label, cnt, n)
    s = s.replace(old, new)
    done.append(label)


# 1) 变量：换成队徽色系
rep(""":root{
  --bg:#f5f5f7; --card:#ffffff; --t1:#1d1d1f; --t2:#86868b; --t3:#b0b0b5;
  --line:#ececf0;
  --wheat:#c8871b; --wheat-soft:#fdf4e3;
  --field:#5b8c2a; --blue:#0071e3; --red:#ff3b30; --orange:#ff9500;
  --gold:#d4a017; --silver:#9aa0a6; --bronze:#b0793a;
  --r:18px; --shadow:0 4px 14px rgba(0,0,0,.045);
}""",
    """:root{
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
}""", '① 变量换成队徽色系')

# 2) body：加背景图（固定铺在视口，不随内容拉变形）
rep("""body{
  font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",Arial,sans-serif;
  background:var(--bg); color:var(--t1); -webkit-font-smoothing:antialiased;
  padding:18px 18px 60px; display:flex; flex-direction:column; align-items:center; min-height:100vh;
}
a{color:var(--blue);text-decoration:none}""",
    """body{
  font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",Arial,sans-serif;
  background:var(--bg); color:var(--t1); -webkit-font-smoothing:antialiased;
  padding:18px 18px 60px; display:flex; flex-direction:column; align-items:center; min-height:100vh;
}
/* 背景图：按队徽配色生成的麦田（images/bg_field.svg，另有 bg_night / bg_plain 两个备选） */
body::before{
  content:''; position:fixed; inset:0; z-index:-1; pointer-events:none;
  background:var(--bg) url('../images/bg_field.svg') center bottom / cover no-repeat;
}
a{color:var(--green);text-decoration:none}""", '② body 加背景图')

# 3) 导航选中态：绿底白字
rep(""".nav-item.active{background:#fff; color:var(--wheat); box-shadow:0 2px 8px rgba(0,0,0,.1)}""",
    """.nav-item.active{background:linear-gradient(135deg,var(--green-2),var(--green)); color:#fff; box-shadow:0 3px 10px rgba(20,120,31,.28)}""",
    '③ 导航选中态改队徽绿')

# 4) 卡片：淡绿描边
rep(""".card{background:var(--card); border-radius:var(--r); box-shadow:var(--shadow); padding:22px}""",
    """.card{background:var(--card); border-radius:var(--r); box-shadow:var(--shadow); padding:22px; border:1px solid var(--green-line)}""",
    '④ 卡片加淡绿描边')

# 5) 主按钮：绿渐变
rep("""  border-radius:99px; cursor:pointer; background:var(--wheat); color:#fff; transition:.2s;""",
    """  border-radius:99px; cursor:pointer; background:linear-gradient(135deg,var(--green-2),var(--green)); color:#fff; transition:.2s;""",
    '⑤ 主按钮改绿渐变')
rep(""".btn.ghost{background:#fff; color:var(--t1); box-shadow:0 2px 8px rgba(0,0,0,.07)}
.btn.ghost:hover{color:var(--wheat)}""",
    """.btn.ghost{background:#fff; color:var(--green); box-shadow:0 2px 8px rgba(20,120,31,.1); border:1px solid var(--green-line)}
.btn.ghost:hover{color:var(--green-2); background:var(--green-soft)}""",
    '⑥ 次按钮改绿描边')
rep(""".btn.flat{background:#f2f2f5;color:var(--t1);box-shadow:none}""",
    """.btn.flat{background:var(--green-soft);color:var(--green);box-shadow:none}""",
    '⑦ flat 按钮改浅绿')

# 6) 表单聚焦：绿色
rep(""".field input:focus,.field select:focus{border-color:var(--wheat);box-shadow:0 0 0 3px rgba(200,135,27,.13)}""",
    """.field input:focus,.field select:focus{border-color:var(--green-2);box-shadow:0 0 0 3px rgba(23,133,34,.14)}""",
    '⑧ 表单聚焦改绿')

# 7) chips
rep(""".chip.active{background:var(--wheat);color:#fff}""",
    """.chip.active{background:linear-gradient(135deg,var(--green-2),var(--green));color:#fff}""",
    '⑨ chip 选中改绿')
rep(""".toolbar input[type=search]:focus{border-color:var(--wheat)}""",
    """.toolbar input[type=search]:focus{border-color:var(--green-2); box-shadow:0 0 0 3px rgba(23,133,34,.12)}""",
    '⑩ 搜索框聚焦改绿')

# 8) 总览
rep(""".hero img.logo{width:104px;height:104px;border-radius:26px;object-fit:cover;box-shadow:0 10px 26px rgba(0,0,0,.14);margin-bottom:14px;background:#fff}""",
    """.hero img.logo{width:104px;height:104px;border-radius:26px;object-fit:cover;box-shadow:0 10px 26px rgba(20,120,31,.18);margin-bottom:14px;background:#fff;border:3px solid #fff}""",
    '⑪ 队徽加绿光晕')
rep(""".hero .slogan{font-size:15px;color:var(--wheat);font-weight:700;letter-spacing:3px;margin-top:6px}""",
    """.hero .slogan{font-size:15px;color:var(--wheat);font-weight:700;letter-spacing:3px;margin-top:6px}""", '（slogan 保持麦金）')
rep(""".stat-card .v{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums;color:var(--wheat)}""",
    """.stat-card .v{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums;color:var(--green)}""",
    '⑫ 统计数字改主绿')
rep(""".stat-card{background:#fff;border-radius:var(--r);padding:18px;text-align:center;box-shadow:var(--shadow)}""",
    """.stat-card{background:#fff;border-radius:var(--r);padding:18px;text-align:center;box-shadow:var(--shadow);border:1px solid var(--green-line)}""",
    '⑬ 统计卡加描边')
rep(""".tl-item:before{content:"";position:absolute;left:-22px;top:5px;width:11px;height:11px;border-radius:50%;background:var(--wheat);border:2px solid #fff;box-shadow:0 0 0 2px var(--wheat-soft)}""",
    """.tl-item:before{content:"";position:absolute;left:-22px;top:5px;width:11px;height:11px;border-radius:50%;background:linear-gradient(135deg,var(--wheat-bright),var(--gold));border:2px solid #fff;box-shadow:0 0 0 2px var(--wheat-soft)}""",
    '⑭ 荣誉时间轴圆点改麦金')
rep(""".best-row{display:flex;align-items:center;gap:12px;padding:11px 14px;background:#fafafc;border-radius:13px}""",
    """.best-row{display:flex;align-items:center;gap:12px;padding:11px 14px;background:#F7FAF5;border-radius:13px;border:1px solid var(--green-line)}""",
    '⑮ 榜单行改浅绿底')
rep(""".best-row .tm{font-variant-numeric:tabular-nums;font-weight:700;font-size:14.5px;color:var(--wheat)}""",
    """.best-row .tm{font-variant-numeric:tabular-nums;font-weight:700;font-size:14.5px;color:var(--green)}""",
    '⑯ 榜成绩改主绿')
rep(""".best-row .medal{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;background:#d7d7dc;flex:0 0 auto}""",
    """.best-row .medal{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;background:var(--green-3);flex:0 0 auto}""",
    '⑰ 名次圆标改中绿')

# 9) 表格
rep("""table.tbl td{padding:11px 14px;border-bottom:1px solid #f6f6f8;vertical-align:middle}""",
    """table.tbl td{padding:11px 14px;border-bottom:1px solid #F0F5ED;vertical-align:middle}""",
    '⑱ 表格分隔线改浅绿')
rep("""table.tbl tbody tr:hover{background:#fcfbf8}""",
    """table.tbl tbody tr:hover{background:#F6FAF4}""",
    '⑲ 表格悬停改浅绿')
rep(""".tm{font-variant-numeric:tabular-nums;font-weight:700}""",
    """.tm{font-variant-numeric:tabular-nums;font-weight:700;color:var(--green)}""",
    '⑳ 表格成绩列改主绿')
rep(""".tagbadge{display:inline-block;padding:2px 8px;border-radius:7px;font-size:11px;font-weight:600;background:#f2f2f5;color:var(--t2);margin-right:4px}""",
    """.tagbadge{display:inline-block;padding:2px 8px;border-radius:7px;font-size:11px;font-weight:600;background:#F1F5EF;color:var(--t2);margin-right:4px}""",
    '㉑ 徽章底色改浅绿灰')
rep(""".tagbadge.wheat{background:var(--wheat-soft);color:var(--wheat)}""",
    """.tagbadge.wheat{background:var(--wheat-soft);color:#7A6100}""",
    '㉒ 身份徽章：浅金底深金字')
rep(""".tagbadge.green{background:#eef7e6;color:var(--field)}""",
    """.tagbadge.green{background:var(--green-soft);color:var(--green)}""",
    '㉓ 新增徽章改浅绿')

# 10) 名册卡片 / 照片墙 / 上传区
rep(""".pcard{background:#fff;border-radius:var(--r);padding:17px;box-shadow:var(--shadow);transition:.22s}""",
    """.pcard{background:#fff;border-radius:var(--r);padding:17px;box-shadow:var(--shadow);transition:.22s;border:1px solid var(--green-line)}""",
    '㉔ 名册卡片加描边')
rep(""".pcard:hover{transform:translateY(-2px);box-shadow:0 10px 24px rgba(0,0,0,.075)}""",
    """.pcard:hover{transform:translateY(-2px);box-shadow:0 12px 26px rgba(20,120,31,.14);border-color:var(--green-3)}""",
    '㉕ 名册卡片悬停绿影')
rep(""".pcard .pb b{font-variant-numeric:tabular-nums;color:var(--wheat)}""",
    """.pcard .pb b{font-variant-numeric:tabular-nums;color:var(--green)}""",
    '㉖ 名册成绩改主绿')
rep(""".pitem{position:relative;border-radius:14px;overflow:hidden;cursor:zoom-in;background:#e9e9ec;aspect-ratio:4/3}""",
    """.pitem{position:relative;border-radius:14px;overflow:hidden;cursor:zoom-in;background:#E8F1E4;aspect-ratio:4/3}""",
    '㉗ 照片占位改浅绿')
rep("""  border:2px dashed #dcdce2;border-radius:16px;padding:30px 20px;text-align:center;background:#fcfcfd;""",
    """  border:2px dashed var(--green-line);border-radius:16px;padding:30px 20px;text-align:center;background:#FCFEFB;""",
    '㉘ 上传拖拽区改绿虚线')
rep(""".drop:hover,.drop.over{border-color:var(--wheat);background:var(--wheat-soft)}""",
    """.drop:hover,.drop.over{border-color:var(--green-2);background:var(--green-soft)}""",
    '㉙ 拖拽悬停改绿')

io.open(P, 'w', encoding='utf-8', newline='').write(s.replace('\n', '\r\n'))
print()
print('\n'.join('  ' + d for d in done if d != '（跳过）'))
print('style.css 已更新')
