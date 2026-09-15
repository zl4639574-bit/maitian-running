# -*- coding: utf-8 -*-
"""生成「要上传的表格」模板（xlsx，单工作表、只有表头，方便直接套用）
   输出：桌面 麦田守望_上传表格模板\\ + 仓库 模板\\（手机也能下载）
"""
import io, os, shutil

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

PROJ = os.path.dirname(os.path.abspath(__file__))
DESK = r'E:\Desktop\麦田守望_上传表格模板'
REPO = os.path.join(PROJ, 'templates')   # 仓库里用 ASCII 目录名，手机上直接点链接不会遇到中文转义问题

HEAD_FILL = PatternFill('solid', fgColor='2F6B39')
HEAD_FONT = Font(bold=True, color='FFFFFF', size=11)
NOTE_FONT = Font(color='8A7314', size=10)
THIN = Side(style='thin', color='C9C9C9')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

# (文件名, 工作表名, 表头, 每列宽度, 宽的示例提示行)
TABLES = [
    ('01_队员资料收集表.xlsx', '队员资料', 
     ['姓名', '性别', '学院', '专业', '年级', '800米', '1500米', '3000米', '5000米', '10000米', '半马', '全马'],
     [10, 6, 16, 16, 8, 9, 9, 9, 9, 10, 9, 9],
     '没有的项填「无」；成绩写法 1:23:29（时:分:秒）或 17:02（分:秒）；一行一个人。'),
    ('02_一场比赛成绩单.xlsx', '成绩单',
     ['姓名', '性别', '学院', '成绩', '名次'],
     [10, 6, 18, 12, 8],
     '一场比赛一个文件（导入时在网页上选「项目/距离」和「日期」）；非队员、外校选手也能一起放进来。'),
    ('03_名册批量添加.xlsx', '新队员名册',
     ['姓名', '学院', '专业', '年级', '性别', '身份'],
     [10, 18, 18, 8, 6, 10],
     '身份填「正式」或「预备」，空着按「正式」算；一行一个人。'),
]


def build(path, sheet, head, widths, note):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    for i, h in enumerate(head, 1):
        c = ws.cell(row=1, column=i, value=h)
        c.fill, c.font, c.border = HEAD_FILL, HEAD_FONT, BORDER
        c.alignment = Alignment(horizontal='center', vertical='center')
        ws.column_dimensions[get_column_letter(i)].width = widths[i - 1]
    ws.row_dimensions[1].height = 22
    ws.freeze_panes = 'A2'
    n = len(head)
    for i in range(2, 6):                       # 5 行空白 + 细边框，方便照着填
        for j in range(1, n + 1):
            ws.cell(row=i, column=j).border = BORDER
    ws.cell(row=7, column=1, value='填写说明：' + note).font = NOTE_FONT
    ws.cell(row=8, column=1, value='示例（别照抄，换成真实数据）：' + ' | '.join(
        {'姓名': '张某某', '性别': '男', '学院': '林学院', '专业': '林学2101', '年级': '2023', '身份': '正式',
         '成绩': '18:35', '名次': '3', '800米': '2:20', '1500米': '4:55', '3000米': '10:20',
         '5000米': '18:35', '10000米': '39:10', '半马': '1:23:29', '全马': '2:58:00'}.get(h, '—')
        for h in head)).font = NOTE_FONT
    os.makedirs(os.path.dirname(path), exist_ok=True)
    wb.save(path)
    return os.path.getsize(path)


NOTE_TXT = u"""════════════════════════════════════════════════════════════════
  麦田守望长跑队 · 上传表格模板（怎么套用）
  生成：2026-09-15    网址永久有效
════════════════════════════════════════════════════════════════

【这三个文件分别用在哪】

  01_队员资料收集表.xlsx
      用于：队长版 → 数据管理 → 队员名册 →「＋ 导入收集表（Excel/CSV，一行一个人）」
      表头必须是：姓名 性别 学院 专业 年级 800米 1500米 3000米 5000米 10000米 半马 全马
      · 没有的项填「无」（不会进成绩榜）
      · 成绩写法：1:23:29（时:分:秒）、17:02（分:秒）、2:58:00（全马）
      · 多出来的列（提交时间 / 填写人 / 备注…）会被自动忽略
      · 腾讯文档收集表导出的 Excel 一般直接就能导，不用改；这份是"要建表 / 别人发来格式不对"时的标准样子

  02_一场比赛成绩单.xlsx
      用于：队长版 → 上传成绩 → ② 批量导入 Excel / CSV（把文件拖进去）
      表头：姓名 性别 学院 成绩 名次（性别/学院/名次可以没有）
      · 一个文件 = 一场比赛的一个项目；「项目/距离」和「日期」在网页上选（导入前会让你确认列对不对）
      · 整场成绩册（含非队员、外校选手）可以直接整张表拖进去：他们只进这一场的榜，
        不进名册、不进个人最好成绩榜
      · 成绩写法同上；Excel 里存成时间格式的（单元格显示 17:35、实际是 0.7326）也认

  03_名册批量添加.xlsx
      用于：队长版 → 数据管理 → 队员名册 →「＋ 批量添加队员」→ 选 Excel/CSV 文件
      表头：姓名 学院 专业 年级 性别 身份（身份填「正式」/「预备」，空着按「正式」）
      · 没有表头也行：那就要按 姓名 学院 专业 年级 性别 身份 这个顺序放
      · 加完点「同步我的修改到线上」才上线

【另外两种"上传"不是选文件，而是导出→改→导回】

  · 队员数据表（改名册/成绩最全的方式）
      队长版 → 数据管理 → 数据表 →「导出为 Excel」→ 在电脑上改 → 再选这个文件导回来。
      这份文件里有「编号」列，是程序认每条成绩用的，**千万别手动做一份**（要用网页导出的那份）。

  · 个人最好成绩（一行一条）
      队长版 → 数据管理 → 队员名册 →「＋ 单独添加个人最好成绩」下面的框里直接粘：
          姓名,项目,成绩[,日期,备注]
          阿巴小洛,半马,1:23:29,2025.4.21,杨凌马拉松
      逗号或制表符都行，可以从 Excel 里复制一整列粘进去。

【常见坑】

  · 表头行要在前 8 行以内；表头里要有「姓名」两个字，否则认不出来
  · 姓名别写错字 —— 写错会被当成另一个人（成绩上报页/添加成绩时会提醒你核对）
  · 手机上也能看这份说明与模板：
      https://zl4639574-bit.github.io/maitian-running/templates/00_guide.txt
      https://zl4639574-bit.github.io/maitian-running/guide.txt   （完整使用说明）
"""


def main():
    os.makedirs(DESK, exist_ok=True)
    os.makedirs(REPO, exist_ok=True)
    print('生成模板：')
    for fn, sheet, head, widths, note in TABLES:
        for d in (DESK, REPO):
            p = os.path.join(d, fn)
            size = build(p, sheet, head, widths, note)
        print('   %-26s %5.1f KB  表头：%s' % (fn, size / 1024.0, ' '.join(head)))
    txt = NOTE_TXT.replace('\n', '\r\n')
    # 桌面那份用中文名（用户双击看）；仓库那份用 ASCII 名（手机上点链接不会遇到中文转义）
    for d, name in ((DESK, '00_说明（先看这个）.txt'), (REPO, '00_guide.txt')):
        io.open(os.path.join(d, name), 'w', encoding='utf-8-sig', newline='').write(txt)
    print('   %-26s %5.1f KB' % ('00_说明（先看这个）.txt', os.path.getsize(os.path.join(DESK, '00_说明（先看这个）.txt')) / 1024.0))
    print('\n目录：\n   %s\n   %s' % (DESK, REPO))


if __name__ == '__main__':
    main()
