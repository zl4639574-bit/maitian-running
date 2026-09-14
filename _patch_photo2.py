# -*- coding: utf-8 -*-
"""① 修「照片同步后仍显示尚未同步」（区块只列真正的本机未同步照片 + 同步后提示已上线）
   ② 照片墙/预览/灯箱不再显示每张照片的名字（缩略图上的文字浮层）"""
import io

p = "assets/app.js"
s = io.open(p, encoding="utf-8", newline="").read().replace("\r\n", "\n")
orig = len(s)

# ── ① 照片管理区的「本机新加」区块：只看真·未同步的；同步完给明确反馈 ──────────
old = r"""    <div id="photoPreview" style="margin-top:16px"></div>
    ${(ov().photos || []).length ? `
    <div style="margin-top:20px">
      <h3>本机新加的照片（${ov().photos.length} 张，尚未同步）</h3>
      <div class="pgrid">${ov().photos.map((p, i) => `
        <div class="pitem"><img src="${photoSrc(p)}"><div class="cap">${esc(p.album)}</div>
          <button class="btn danger sm" data-pdel="${i}" style="position:absolute;top:6px;right:6px">删</button></div>`).join('')}
      </div>
    </div>` : ''}"""
new = r"""    <div id="photoPreview" style="margin-top:16px"></div>
    ${(LOCAL_OV && (LOCAL_OV.photos || []).length) ? `
    <div style="margin-top:20px">
      <h3>还没同步的照片（${LOCAL_OV.photos.length} 张）</h3>
      <div class="tiny" style="margin:8px 0 12px">点「数据管理 → 同步 → 同步我的修改到线上」，这些照片就会出现在照片墙里。</div>
      <div class="pgrid">${LOCAL_OV.photos.map((p, i) => `
        <div class="pitem"><img src="${photoSrc(p)}">
          <button class="btn danger sm" data-pdel="${i}" style="position:absolute;top:6px;right:6px">删</button></div>`).join('')}
      </div>
    </div>` : ''}
    ${(CLOUD_OV && (CLOUD_OV.photos || []).length) ? `
    <div class="notice" style="margin-top:16px">
      ${(LOCAL_OV && (LOCAL_OV.photos || []).length)
        ? '已上线的照片：' + CLOUD_OV.photos.length + ' 张（上面那批同步后也会计入）'
        : '✅ 照片全部已同步上线：' + CLOUD_OV.photos.length + ' 张，在「照片墙」里可以看到'}
    </div>` : ''}"""
assert s.count(old) == 1, "① 照片管理区块锚点"
s = s.replace(old, new)

# ── ② 照片墙相册内：不再显示每张照片的名字 ─────────────────────────────────
old = r"""          <img src="${photoSrc(p)}" loading="lazy" alt="${esc(p.caption)}">
          <div class="cap">${esc(p.caption || '')}</div>"""
new = r"""          <img src="${photoSrc(p)}" loading="lazy" alt="">"""
assert s.count(old) == 1, "② 照片墙 caption 锚点"
s = s.replace(old, new)

# ── ③ 灯箱（放大查看）只留序号，不显示名字 ─────────────────────────────────
old = r"""  $('#lbCap').textContent = p.c + '  (' + (lbIdx + 1) + '/' + lbList.length + ')';"""
new = r"""  $('#lbCap').textContent = (lbIdx + 1) + ' / ' + lbList.length;"""
assert s.count(old) == 1, "③ 灯箱 caption 锚点"
s = s.replace(old, new)

io.open(p, "w", encoding="utf-8", newline="\r\n").write(s)
print("app.js 已改: %d -> %d 字符" % (orig, len(s)))
