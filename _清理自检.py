# -*- coding: utf-8 -*-
"""清理自检测试成绩 + 更新说明书里那段「去数据管理→同步发布」的误导说法"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ov = os.path.join(HERE, "data", "overrides.js")

# ① 从 overrides.js 里删掉自检记录
t = io.open(ov, encoding="utf-8", newline="").read()
head, body = t.split("=", 1)
obj = json.loads(body.strip().rstrip(";"))
before = len(obj.get("results") or [])
obj["results"] = [r for r in (obj.get("results") or []) if r.get("uid") != "selftest_pub"]
new = head + "= " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n"
io.open(ov, "w", encoding="utf-8", newline="\n").write(new)
print("overrides.js: 自由成绩 %d -> %d 条（已删除自检记录）" % (before, len(obj["results"])))

# ② 说明书：把「去数据管理→同步发布」改成「一键发布并同步」
old = u"导入或录入之后，成绩先存在本机；要进全队榜，去「数据管理 → 比赛成绩」\r\n   把成绩并到某场比赛里，再点「同步我的修改到线上」。"
new = (u"导入或录入之后，成绩先存在本机（页面会显示「本机有 N 条成绩还没上线」）。\r\n"
       u"   点「上传成绩」页里的蓝色按钮「发布并同步到线上」，一键就上线了，全队立刻能看到。\r\n"
       u"   想做成「某场比赛一张榜」（而不是自由成绩），去「数据管理 → 比赛成绩」把它们\r\n"
       u"   并进那场比赛的榜单再同步。同步面板里也会提示「N 条还没发布」并给一键按钮。")
for f in ["使用说明.txt", "guide.txt"]:
    t = io.open(f, encoding="utf-8-sig", newline="").read()
    if old in t:
        io.open(f, "w", encoding="utf-8-sig", newline="").write(t.replace(old, new))
        print(f, "已更新【二】说明 ✓")
    else:
        print(f, "⚠️ 没找到原文，跳过（可能已改过）")
