# -*- coding: utf-8 -*-
"""清理批量自检加的 5 个假队员 + 说明书【五】补上「添加/批量添加队员」说明"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
TESTNAMES = [u"批量甲", u"批量乙", u"批量丙", u"文件甲", u"文件乙"]

# ① 清掉假队员
ovp = os.path.join(HERE, "data", "overrides.js")
t = io.open(ovp, encoding="utf-8", newline="").read()
head, body = t.split("=", 1)
obj = json.loads(body.strip().rstrip(";"))
nm = obj.get("newMembers") or []
obj["newMembers"] = [m for m in nm if m.get("name") not in TESTNAMES]
io.open(ovp, "w", encoding="utf-8", newline="\n").write(
    head + "= " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n")
print("新增队员: %d -> %d 人（自检的 5 人已删除）" % (len(nm), len(obj["newMembers"])))

# ② 说明书补写
old = u"    队员名册 —— 改学院/专业/年级/身份，也可以把某人从公开名册里删掉（能恢复）"
new = (u"    队员名册 —— 改学院/专业/年级/身份；把某人从公开名册移除（会进「已移除」，点 ↺ 可恢复）\r\n"
       u"                ＋ 添加新队员：填姓名/性别/学院/专业/年级/身份（正式·预备），一个一个加\r\n"
       u"                ＋ 批量添加队员：从 Excel 复制几行直接粘进去（列顺序：姓名 学院 专业 年级 性别 身份，\r\n"
       u"                  有表头也能自动认列），或者选一个 xlsx / csv 文件 → 点「解析并预览」\r\n"
       u"                  → 检查无误后点「把这 N 人加入名册」。重名和不规范的姓名会自动跳过并告诉你。\r\n"
       u"                加完之后都要去「同步」点一次「同步我的修改到线上」，线上名册才会更新。")
for f in [u"使用说明.txt", u"guide.txt"]:
    txt = io.open(f, encoding="utf-8-sig", newline="").read()
    if old in txt:
        io.open(f, "w", encoding="utf-8-sig", newline="").write(txt.replace(old, new))
        print("%s 已更新【五】✓" % f)
    else:
        print("%s ⚠️ 没找到原文" % f)
