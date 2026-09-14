# -*- coding: utf-8 -*-
"""删掉自检添加的假队员 自检新队员"""
import io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ovp = os.path.join(HERE, "data", "overrides.js")
t = io.open(ovp, encoding="utf-8", newline="").read()
head, body = t.split("=", 1)
obj = json.loads(body.strip().rstrip(";"))
nm = obj.get("newMembers") or []
obj["newMembers"] = [m for m in nm if m.get("name") != u"自检新队员"]
io.open(ovp, "w", encoding="utf-8", newline="\n").write(
    head + "= " + json.dumps(obj, indent=1, ensure_ascii=False) + ";\n")
print("新增队员: %d -> %d 人（已删除自检假队员）" % (len(nm), len(obj["newMembers"])))
