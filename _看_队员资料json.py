# -*- coding: utf-8 -*-
"""看一眼队员导出的 .json 资料文件里到底有什么（不改任何东西）"""
import io, os, sys, json, shutil

SRC = r"D:\weixindocument\xwechat_files\wxid_83piiowb9hc222_57aa\msg\file\2026-09\麦田守望_我的资料_王金豪.json"

print("文件存在：", os.path.exists(SRC))
if not os.path.exists(SRC):
    # 找不到就给个提示：列一下那个目录里有哪些 json
    d = os.path.dirname(SRC)
    if os.path.isdir(d):
        print("同目录下的 json：")
        for n in os.listdir(d):
            if n.lower().endswith('.json'):
                print("   ", n)
    sys.exit(1)

print("大小：", round(os.path.getsize(SRC) / 1024, 1), "KB")
raw = io.open(SRC, encoding='utf-8', errors='replace').read()
try:
    d = json.loads(raw)
except Exception as e:
    print("不是标准 JSON：", e)
    print("开头 200 字：", raw[:200])
    sys.exit(1)

print("\n顶层字段：", list(d.keys()) if isinstance(d, dict) else type(d).__name__)


def show(k, v, depth=0):
    pad = '  ' * (depth + 1)
    if isinstance(v, str):
        if v.startswith('data:'):
            print('%s%s: 【图片 dataURL】约 %.0f KB' % (pad, k, len(v) * 0.75 / 1024))
        else:
            print('%s%s: %s' % (pad, k, v[:80]))
    elif isinstance(v, dict):
        print('%s%s: {' % (pad, k))
        for kk, vv in v.items():
            show(kk, vv, depth + 1)
        print('%s}' % pad)
    elif isinstance(v, list):
        print('%s%s: [%d 项]' % (pad, k, len(v)))
        for it in v[:6]:
            show('·', it, depth + 1)
    else:
        print('%s%s: %r' % (pad, k, v))


if isinstance(d, dict):
    for k, v in d.items():
        show(k, v)

# 拷一份到桌面，方便在文件对话框里选
dst = os.path.join(r"E:\Desktop", "麦田守望_我的资料_王金豪.json")
try:
    shutil.copy2(SRC, dst)
    print("\n已复制到桌面：", dst, "（%.0f KB）" % (os.path.getsize(dst) / 1024))
except Exception as e:
    print("\n复制到桌面失败：", e)
