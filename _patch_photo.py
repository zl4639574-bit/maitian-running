# -*- coding: utf-8 -*-
"""修照片上传：① 逐张处理（一张坏图不再拖垮整批）② 有令牌时选完直传线上，不占本机 5MB ③ 配额/HEIC 明确提示"""
import io

p = "assets/app.js"
s = io.open(p, encoding="utf-8", newline="").read().replace("\r\n", "\n")
orig = len(s)

# ── ① localStorage 写失败时，说清楚到底为什么 ────────────────────────────────
old = r"""function lsSet(k, v) {
  try { localStorage.setItem(k, JSON.stringify(v)); return true; }
  catch (e) { toast('这个浏览器不让存数据，改动无法保存'); return false; }
}"""
new = r"""function lsSet(k, v) {
  try { localStorage.setItem(k, JSON.stringify(v)); return true; }
  catch (e) {
    const full = /quota|exceeded/i.test(String((e && e.name) || '') + ' ' + String((e && e.message) || ''));
    toast(full
      ? '本机存储满了（浏览器只给约 5MB）：先把已有照片点「同步」传到线上，本机就腾空了，再继续加照片'
      : '这个浏览器不让存数据（可能是无痕/隐私模式打开的），改动无法保存 —— 换成普通窗口打开', 12000);
    return false;
  }
}"""
assert s.count(old) == 1, "① lsSet 锚点"
s = s.replace(old, new)

# ── ② saveLocalOv 回传成功与否（照片用它判断有没有真存住）──────────────────
old = r"""function saveLocalOv() {
  LOCAL_OV = LOCAL_OV || {};
  lsSet(LS_LOCAL, LOCAL_OV);
}"""
new = r"""function saveLocalOv() {
  LOCAL_OV = LOCAL_OV || {};
  return lsSet(LS_LOCAL, LOCAL_OV);
}"""
assert s.count(old) == 1, "② saveLocalOv 锚点"
s = s.replace(old, new)

# ── ③ 已直传线上的照片用会话内预览，避免刚传完显示裂图 ──────────────────────
old = r"""function photoSrc(p) {
  return p.data ? p.data : ROOT + 'images/' + p.file;
}"""
new = r"""const PHOTO_PREVIEW = {};   // 本次会话里已直传线上的照片（本地先预览，不占 localStorage）
function photoSrc(p) {
  if (p.data) return p.data;
  if (p.file && PHOTO_PREVIEW[p.file]) return PHOTO_PREVIEW[p.file];
  return ROOT + 'images/' + p.file;
}"""
assert s.count(old) == 1, "③ photoSrc 锚点"
s = s.replace(old, new)

# ── ④ handlePhotos 重写：逐张独立处理 + 可选直传 ────────────────────────────
old = r"""function handlePhotos(files) {
  if (!files || !files.length) return;
  const sel = $('#albSel'), nw = $('#albNew');
  let album = sel ? sel.value : '';
  if (album === '__new') album = (nw && nw.value.trim()) || '新相册';
  if (!album) album = '未分类';
  const list = Array.from(files);
  let done = 0;
  const l = ovLocal();
  l.photos = l.photos || [];
  const out = [];
  list.forEach(f => {
    if (!/^image\//.test(f.type)) return;
    const img = new Image();
    const fr = new FileReader();
    fr.onload = () => {
      img.onload = () => {
        const MAX = 1500;
        let w = img.width, h = img.height;
        if (w > MAX) { h = Math.round(h * MAX / w); w = MAX; }
        const cv = document.createElement('canvas');
        cv.width = w; cv.height = h;
        cv.getContext('2d').drawImage(img, 0, 0, w, h);
        const data = cv.toDataURL('image/jpeg', 0.8);
        out.push({
          album, albumDate: (album.match(/\d{4}/) || [todayStr().slice(0, 4)])[0],
          file: 'up_' + Date.now() + '_' + out.length + '.jpg',
          caption: f.name.replace(/\.[^.]+$/, '').slice(0, 18),
          data, size: Math.round(data.length * 0.75),
        });
        done++;
        if (done === list.length) {
          l.photos = l.photos.concat(out);
          saveLocalOv();
          const mb = out.reduce((a, x) => a + x.size, 0) / 1048576;
          toast('已加入 ' + out.length + ' 张到「' + album + '」（约 ' + mb.toFixed(1) + ' MB，待同步）', 4000);
          render();
        }
      };
      img.src = fr.result;
    };
    fr.readAsDataURL(f);
  });
}"""
new = r"""function handlePhotos(files) {
  if (!files || !files.length) return;
  const sel = $('#albSel'), nw = $('#albNew');
  let album = sel ? sel.value : '';
  if (album === '__new') album = (nw && nw.value.trim()) || '新相册';
  if (!album) album = '未分类';
  const list = Array.from(files);
  const cfg = ghCfg();
  const direct = !!cfg.token;                 // 有令牌：压完直接传线上，不占本机那 5MB
  const l = ovLocal();
  l.photos = l.photos || [];
  let ok = 0, skipped = 0, full = 0;
  const bad = [];
  let seen = 0;
  const finish = () => {
    seen++;
    if (seen < list.length) return;
    render();
    const parts = [];
    if (ok) parts.push('已加入 ' + ok + ' 张到「' + album + '」' + (direct ? '（已直接传到线上，再点「同步」照片墙就显示）' : '（待同步）'));
    if (bad.length) parts.push(bad.length + ' 张打不开被跳过：' + bad.slice(0, 2).join('、') + (bad.length > 2 ? ' 等' : '')
      + ' —— iPhone 的 HEIC 格式浏览器认不了，先在手机相册里转成 JPG（或微信发给自己会自动转码）再传');
    if (full) parts.push(full + ' 张没存住：本机存储满了，先点「同步」把已有照片传到线上腾出空间');
    if (skipped) parts.push(skipped + ' 个文件不是图片，已跳过');
    toast(parts.join('；') || '没有可用的图片', 12000);
  };
  list.forEach((f, i) => {
    if (!/^image\//.test(f.type) && !/\.(jpe?g|png|webp|gif|bmp)$/i.test(f.name)) { skipped++; finish(); return; }
    const img = new Image();
    const fr = new FileReader();
    fr.onerror = () => { bad.push(f.name); finish(); };
    fr.onload = () => {
      img.onerror = () => { bad.push(f.name); finish(); };       // HEIC 等解不开的格式走这里
      img.onload = async () => {
        try {
          const MAX = 1500;
          let w = img.width, h = img.height;
          if (w > MAX) { h = Math.round(h * MAX / w); w = MAX; }
          const cv = document.createElement('canvas');
          cv.width = w; cv.height = h;
          cv.getContext('2d').drawImage(img, 0, 0, w, h);
          const data = cv.toDataURL('image/jpeg', 0.8);
          const rec = {
            album, albumDate: (album.match(/\d{4}/) || [todayStr().slice(0, 4)])[0],
            file: 'up_' + Date.now() + '_' + i + '.jpg',
            caption: f.name.replace(/\.[^.]+$/, '').slice(0, 18),
            size: Math.round(data.length * 0.75),
          };
          if (direct) {
            await ghPut(cfg, 'images/' + rec.file, String(data).split(',')[1],
                        '上传照片 ' + album + ' / ' + rec.file);
            PHOTO_PREVIEW[rec.file] = data;        // 本机先能预览
            l.photos.push(rec);                    // 只存元数据（很小）
            saveLocalOv();
          } else {
            l.photos.push(Object.assign({ data }, rec));
            if (!saveLocalOv()) { l.photos.pop(); full++; finish(); return; }   // 没存住就回退，别骗人
          }
          ok++;
        } catch (e) {
          bad.push(f.name + '（' + String((e && e.message) || e).slice(0, 24) + '）');
        }
        finish();
      };
      img.src = fr.result;
    };
    fr.readAsDataURL(f);
  });
}"""
assert s.count(old) == 1, "④ handlePhotos 锚点"
s = s.replace(old, new)

# ── ⑤ 同步时跳过已经直传过的照片（它们没有 data）────────────────────────────
old = r"""    for (const p of (l.photos || [])) {
      const b64 = String(p.data).split(',')[1];"""
new = r"""    for (const p of (l.photos || [])) {
      if (!p.data) continue;                    // 选照片时已直传线上，这里只写清单
      const b64 = String(p.data).split(',')[1];"""
assert s.count(old) == 1, "⑤ 同步照片循环锚点"
s = s.replace(old, new)

# ── ⑥ 照片区文案：说清楚当前是直传还是暂存 ─────────────────────────────────
old = r"""    <div class="tiny" style="margin-bottom:14px">手机相册里的照片可以直接选，浏览器会自动压缩后再上传（长边 1500px）。</div>"""
new = r"""    <div class="tiny" style="margin-bottom:14px">手机相册里的照片可以直接选，浏览器会自动压缩后再上传（长边 1500px）。
      ${ghCfg().token
        ? '<br>已配好令牌：<b>选完就会直接传到线上</b>，不占用本机空间，可以一次选很多张。'
        : '<br>⚠️ 还没配令牌：照片先存在本机（浏览器只给约 5MB，约 10 张）。<br>建议先到「同步」里配好令牌，之后再传照片就会直接上线上。'}</div>"""
assert s.count(old) == 1, "⑥ 照片文案锚点"
s = s.replace(old, new)

io.open(p, "w", encoding="utf-8", newline="\r\n").write(s)
print("app.js 照片补丁完成: %d -> %d 字符" % (orig, len(s)))
