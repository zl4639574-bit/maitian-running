# -*- coding: utf-8 -*-
"""把今天(2026-09-14)在 E:\Desktop\麦田 里产出的文件，整理成桌面上的一个文件夹。
原文件不删、不移动（避免破坏网站），只做副本 + 生成说明.txt"""
import os, io, re, shutil, datetime, sys

SRC = r'E:\Desktop\麦田'
PROJ = os.path.join(SRC, '麦田守望数据中心')
DST = r'E:\Desktop\麦田_今日产出_2026-09-14'
CUT = datetime.datetime(2026, 9, 14, 0, 0, 0)

DESC = {
    '_patch_pb.py': '改动代码用的补丁：个人最好成绩改为只统计正式队员（单场榜仍显示所有人）',
    '_patch_dt.py': '改动代码用的补丁：新增「数据表」分区——导出队员数据表 / 导入修正表批量改正',
    '_patch_dtfix.py': '改动代码用的补丁：修导入修正表 4 个 bug（日期层级 / 身份「队员」 / 名次类型 / 云端自由成绩可改删）',
    '_patch_publish.py': '改动代码用的补丁：修「导入后同步不了」（导入只进本机草稿，加一键发布并同步）',
    '_patch_photo.py': '改动代码用的补丁：修照片上传 3 个 bug（逐张独立处理 / 有令牌直传线上 / HEIC 与容量提示）',
    '_patch_photo2.py': '改动代码用的补丁：修「照片已同步仍显示未同步」+ 去掉缩略图上的照片名',
    '_patch_roster.py': '改动代码用的补丁：数据管理 → 队员名册 加「添加新队员」入口',
    '_patch_roster2.py': '改动代码用的补丁：加「批量添加队员」（粘贴 Excel 行或选 xlsx/csv，自动认表头、预览）',
    '_patch_roster3.py': '改动代码用的补丁：重名不再硬拦（只提醒）；身份是「队员/未分级」时说清原因并可一键搜出来改身份',
    '_patch_roster4.py': '改动代码用的补丁：拼音组词中不触发检索(IME) + 新增队员身份空自动按正式 + 名册区未同步数量提示与一键同步',
    '提取数据.py': '从原始资料提取队伍数据（生成 data/team-data.js）',
    '生成图片.py': '压缩/生成网站用的图片（assets/images）',
    '生成队员数据表.py': '生成《队员数据表.xlsx》和 .csv（队员总表 / 成绩明细 / 说明）',
    '手机检查.py': '公共模块：用 CDP 拉起 Edge、手机视口截图、读页面状态（所有自检脚本都调用它）',
    '_统计.py': '统计线上数据口径（多少队员、多少成绩、多少照片）',
    '_自检.html': '网页内自检页面',
    '_dbg_cdp.py': '调试 CDP 连接的小脚本',
    '_t_test.js': '临时调试文件（可删）',
    '_tl.txt': '临时调试输出（可删）',

    '_同步自检.py': '自检：点「同步」后，用 GitHub 接口读回仓库，确认真的写进去了',
    '_发布自检.py': '自检：本机有未发布改动 → 一键发布 → 同步成功（模拟你的处境）',
    '_照片自检.py': '自检：照片上传（正常 JPG / 存储满）',
    '_照片自检2.py': '自检：照片上传修复后（选完直传线上、逐张处理）',
    '_照片验证.py': '自检：照片同步后不再显示「未同步」、相册里不显示照片名',
    '_名册自检.py': '自检：添加新队员能不能成功、仓库里有没有记录',
    '_批量名册自检.py': '自检：批量添加（粘贴 Excel 行 / 选 xlsx），脏名单是否被跳过',
    '_重名自检.py': '自检：重名不硬拦、身份是「队员」时提示是否准确',
    '_成绩替换自检.py': '自检：上传更快的成绩会自动替换最好成绩，更慢的不动',
    '_数据表自检.py': '自检：导出队员数据表 / 导入修正表（未改动文件导回应为 0 处差异）',
    '_检索与身份自检.py': '自检：拼音组词中不检索、上屏后才检索；新增队员身份空也能显示；名册区未同步提示',
    '_清理自检.py': '清理：删掉自检时留在本机的假数据',
    '_清理名册自检.py': '清理：删掉名册自检加的假队员',
    '_清理批量自检.py': '清理：删掉批量名册自检加的假队员',
    '_清理照片自检.py': '清理：删掉照片自检留下的假照片',
    '_读本机草稿.py': '只读排查：扫描本机浏览器里还没同步的草稿（不改任何东西）',
    '_读本机草稿2.py': '只读排查：扩大范围扫描所有浏览器配置里的草稿',
    '_取证捞草稿.py': '只读排查：从 Edge 数据库里抢救历史版本的草稿（这次就是你名单没显示用到的）',
    '_列全部localStorage键.py': '只读排查：列出网页在本机浏览器里存了哪些数据键',

    '同步面板_手机.png': '截图：手机上的同步面板',
}

PAT_DESC = [
    (r'_自检|_验证', '自检脚本：手机视口真机跑一遍、把结果打印出来'),
    (r'^_patch', '改动代码用的补丁脚本'),
    (r'\.png$', '自检/验证截图'),
    (r'^队员数据表.*\.xlsx$', '队员数据表（Excel）'),
    (r'\.csv$', '队员数据表（CSV，手机也能看）'),
]


def classify(rel, name):
    """返回 (分类文件夹, 说明)"""
    relu = rel.replace('\\', '/')
    if relu.startswith('工具/'):
        return '06_工具与一键小工具', '工具：' + ('GitHub 命令行 gh（已登录）' if 'gh' in relu else 'cloudflared（临时公网隧道，备用）')
    if relu.startswith('云端中转/') or relu.startswith('scripts/'):
        return '07_云端中转与旧脚本（未启用）', '备用方案文件（没启用），留着以后要用云中转时参考'
    if name.endswith('.png'):
        return '04_截图（自检证据）', DESC.get(name, '截图：自检/验证时的界面留证')
    if name in DESC:
        d = DESC[name]
        if name.endswith(('.py', '.js')) and (relu.endswith('.py')):
            pass
        if name in ('_t_test.js', '_tl.txt', '_dbg_cdp.py'):
            return '02_脚本与补丁', d
        if re.search(r'自检|验证|取证|读本机|列全部', name):
            return '03_自检脚本（验证用）', d
        if name.endswith(('.xlsx', '.csv')):
            return '05_数据表', d
        return '02_脚本与补丁', d
    if name.endswith('.png'):
        return '04_截图（自检证据）', PAT_DESC[2][1]
    if name in ('系统代理_打开（要用Clash时用）.bat', '系统代理_关闭（网页打不开就用它）.bat'):
        return '06_工具与一键小工具', '一键小工具：' + ('开 Clash 时双击它（把系统代理打开）' if '打开' in name else '网页打不开时双击它（关掉系统代理）')
    if name == '_proxy_refresh.py':
        return '06_工具与一键小工具', '上面两个 bat 调用的脚本（通知浏览器代理已改，立即生效）'
    if name.endswith(('.xlsx', '.csv')):
        return '05_数据表', '队员数据表（Excel / CSV）——队员总表 + 成绩明细'
    for pat, d in PAT_DESC:
        if re.search(pat, name):
            return '02_脚本与补丁', d
    return '02_脚本与补丁', '今天产出的文件'


def today(p):
    try:
        return datetime.datetime.fromtimestamp(os.path.getmtime(p)) >= CUT
    except OSError:
        return False


SKIP_DIRS = {'.git', '__pycache__', 'node_modules', '.venv'}
SITE_KEEP_DIRS = ['assets', 'captain', 'data', 'images']
SITE_KEEP_FILES = ['index.html', 'guide.txt', '使用说明.txt', '更新数据.bat', '更新并上传.bat', '启动公网链接.bat']

copied = []
failed = []

def cpy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        shutil.copy2(src, dst)
        copied.append((dst, os.path.getsize(dst), os.path.getmtime(dst)))
        return True
    except Exception as e:
        failed.append((src, str(e)))
        return False

if os.path.isdir(DST):
    shutil.rmtree(DST)
os.makedirs(DST)

# ① 网站本体（整棵子树，今天的站点全是我今天做的）
for d in SITE_KEEP_DIRS:
    sd = os.path.join(PROJ, d)
    if not os.path.isdir(sd):
        continue
    for dp, dn, fn in os.walk(sd):
        dn[:] = [x for x in dn if x not in SKIP_DIRS]
        for f in fn:
            s = os.path.join(dp, f)
            r = os.path.relpath(s, PROJ)
            cpy(s, os.path.join(DST, '01_网页系统（双击 index.html）', r))
for f in SITE_KEEP_FILES:
    s = os.path.join(PROJ, f)
    if os.path.isfile(s):
        cpy(s, os.path.join(DST, '01_网页系统（双击 index.html）', f))

# ② 今天的零散文件（麦田 根目录 + 数据中心 根目录）
sources = []
for dp, dn, fn in os.walk(PROJ):
    dn[:] = [x for x in dn if x not in SKIP_DIRS and dp == PROJ or x not in SKIP_DIRS]
    if dp == PROJ:
        continue
    break
for name in os.listdir(PROJ):
    p = os.path.join(PROJ, name)
    if os.path.isfile(p) and name not in SITE_KEEP_FILES and today(p):
        sources.append((p, name, os.path.relpath(p, SRC)))
for name in os.listdir(SRC):
    p = os.path.join(SRC, name)
    if os.path.isfile(p) and today(p):
        sources.append((p, name, name))

for p, name, rel in sources:
    cat, desc = classify(rel, name)
    cpy(p, os.path.join(DST, cat, name))
# 截图目录里的手机截图
ms = os.path.join(PROJ, '手机截图')
if os.path.isdir(ms):
    for f in os.listdir(ms):
        if today(os.path.join(ms, f)):
            cpy(os.path.join(ms, f), os.path.join(DST, '04_截图（自检证据）/手机视口截图', f))
# 工具原件
for rel in ('工具/gh/bin/gh.exe', '工具/cloudflared.exe'):
    p = os.path.join(SRC, *rel.split('/'))
    if os.path.isfile(p):
        cat, desc = classify(rel, os.path.basename(p))
        cpy(p, os.path.join(DST, cat, os.path.basename(p)))
# 备用方案（云中转 / 旧的合并脚本）
for rel in ('云端中转/relay.js', 'scripts/merge_queue.py'):
    p = os.path.join(PROJ, *rel.split('/'))
    if os.path.isfile(p):
        cpy(p, os.path.join(DST, '07_云端中转与旧脚本（未启用）', os.path.basename(p)))

# ③ 生成说明.txt
lines = []
A = lines.append
A('麦田守望数据中心 —— 2026年9月14日 今日产出汇总')
A('=' * 68)
A('')
A('生成时间：%s' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
A('原文件位置：%s（原文件都还在，没有删也没有移动）' % SRC)
A('本文件夹：%s' % DST)
A('')
A('■ 线上网址（永久、手机普通浏览器直接打开、不用 VPN）')
A('   展示版：https://zl4639574-bit.github.io/maitian-running/')
A('   队长版：https://zl4639574-bit.github.io/maitian-running/captain/')
A('   说明书：https://zl4639574-bit.github.io/maitian-running/guide.txt')
A('')
A('■ 文件夹结构')
A('   00_说明（先看这个）.txt          ← 你正在看的这份')
A('   01_网页系统（双击 index.html）\\   ← 网站全部文件 + 启动器 + 说明书')
A('   02_脚本与补丁\\                  ← 我改代码用的补丁脚本 + 数据/图片生成脚本')
A('   03_自检脚本（验证用）\\           ← 每次改完都真机跑一遍的验证脚本')
A('   04_截图（自检证据）\\             ← 自检截图，证明功能真的能用')
A('   05_数据表\\                      ← 队员数据表（Excel/CSV）')
A('   06_工具与一键小工具\\             ← gh / cloudflared / 系统代理开关')
A('   07_云端中转与旧脚本（未启用）\\    ← 备用方案，没启用')
A('')
A('■ 每个文件是干什么的')
A('')
by_cat = {}
for dst, sz, mt in copied:
    rel = os.path.relpath(dst, DST)
    cat = rel.split(os.sep)[0]
    by_cat.setdefault(cat, []).append((rel, sz, mt))
order = sorted(by_cat.keys())
total = 0
for cat in order:
    A('── %s ──' % cat)
    for rel, sz, mt in sorted(by_cat[cat]):
        name = os.path.basename(rel)
        d = DESC.get(name, '')
        total += sz
        A('   %-46s %8s  %s' % (rel.replace(os.sep, '/'), ('%.0fKB' % (sz / 1024)) if sz > 1024 else ('%dB' % sz),
                               datetime.datetime.fromtimestamp(mt).strftime('%H:%M')))
        if d:
            A('         └ %s' % d)
    A('')
A('■ 合计：%d 个文件，%.1f MB' % (len(copied), total / 1048576.0))
A('')
A('■ 今天做出来的功能（都在 01 的网站里）')
A('   1. 展示版 + 队长版两套页面，共用一份数据')
A('   2. 成绩榜：个人最好成绩（只统计正式队员）+ 每场比赛一张榜')
A('   3. 队员名册：添加队员 / 批量添加（粘贴 Excel 行或选 xlsx）/ 改身份 / 重名只提醒不拦')
A('   4. 照片墙：相册分组、点开大图；有令牌时选完直传线上，不占本机空间')
A('   5. 数据表：导出队员数据表(Excel) → 改好 → 导入修正表批量改正并同步')
A('   6. 同步：队长版里一键把改动推到线上（约 1 分钟）')
A('   7. 拼音输入时不打断检索（组词结束才检索）')
A('')
A('■ 常用操作')
A('   手机看：直接打开上面的展示版网址（建议添加到主屏幕）')
A('   电脑看：双击 01_网页系统\\index.html；或打开线上网址')
A('   改数据：队长版 → 数据管理 → 对应的分区 → 改完点「同步到线上」')
A('   网页打不开：双击 06_工具与一键小工具\\系统代理_关闭（网页打不开就用它）.bat')
A('')
A('■ 提醒')
A('   01_网页系统 里是网站本体，改这里的文件不会影响线上（线上要同步才会变）。')
A('   原文件夹 %s 里的同名文件都还在，你可以对比。' % SRC)

txt = '\r\n'.join(lines)
io.open(os.path.join(DST, '00_说明（先看这个）.txt'), 'w', encoding='utf-8-sig').write(txt)

print('目标文件夹：%s' % DST)
print('复制成功 %d 个文件，%.1f MB；失败 %d 个' % (len(copied), total / 1048576.0, len(failed)))
for s, e in failed:
    print('  ✗ %s -> %s' % (s, e))
for cat in order:
    print('  %-34s %d 个' % (cat, len(by_cat[cat])))
