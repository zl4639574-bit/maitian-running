# -*- coding: utf-8 -*-
"""
_patchI：照片上传改成「一张一张传 + 自动重试 + 不丢照片 + 说清原因」
背景：安卓手机一次选 6 张，6 张同时往 GitHub 传 → 撞限流/网络抖动 → 4 张失败，
      而且错误原因被 .slice(0,24) 截掉了，只剩「写入 images/up_17894563651」，看不出所以然。
改动：
  1. handlePhotos 整体重写：
     · 先在本机全部解码压缩（并行、只吃本机 CPU），再【串行】上传，一张一张来；
     · 每张失败自动重试 3 次（1.2s / 3.5s 退避）；
     · 传不上去的【退回本机待同步列表】并保留图片数据 → 之后点「同步」还能补传，不丢照片；
     · 失败提示不再截断，直接给出原因（403 限流/权限、401 令牌、404 仓库、网络不通等）；
     · 传的过程中显示「正在传第 n / N 张…（别切到别的 App）」；
     · 压缩上限 1500px → 1200px、质量 0.8 → 0.78（手机流量小、传得快）。
  2. 选图后清空 input.value：修「同一张照片再选一次没反应」（手机上想重试时最常撞到）。
  3. 新增 uploadOne()：串行 + 退避重试的小工具（401/404 这种重试也没用的直接放弃）。
"""
import io, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, 'assets', 'app.js')

src = io.open(P, encoding='utf-8', newline='').read()
orig = src

# ---------- 1) 整段替换 handlePhotos ----------
start_mark = '/** 照片：压缩后存到本机待同步列表 */'
end_mark = '/* -------------------------------------------------- GitHub 同步（队长版） */'
i0 = src.find(start_mark)
i1 = src.find(end_mark)
if i0 < 0 or i1 < 0 or i1 < i0:
    print('找不到 handlePhotos 段落'); sys.exit(1)

new_handle = u'''/** 照片：压缩后存到本机待同步列表；有令牌就【一张一张】直接传线上
    （手机上同时并发传多张会被 GitHub 限流 → 之前"4 张打不开被跳过"就是这个原因） */
function handlePhotos(files) {
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
  const bad = [];        // 打不开 / 压不了
  const fail = [];       // 传不上去（已退回本机待同步）
  let ok = 0, skipped = 0, full = 0, kept = 0, read = 0;

  const summary = () => {
    render();
    const parts = [];
    if (ok) parts.push('已加入 ' + ok + ' 张到「' + album + '」' + (direct ? '（已直接传到线上，再点「同步」照片墙就显示）' : '（待同步）'));
    if (bad.length) parts.push(bad.length + ' 张打不开被跳过：' + bad.slice(0, 2).join('、') + (bad.length > 2 ? ' 等' : '')
      + ' —— 多是不认识的格式，或解码器没加载好：稍后重试一次；还不行就把 iPhone「设置 → 相机 → 格式」改成「兼容性最佳」');
    if (fail.length) parts.push(fail.length + ' 张没传上去（已存在本机，等网络好点点「同步」就能补传）：' + fail.slice(0, 2).join('、') + (fail.length > 2 ? ' 等' : ''));
    if (full) parts.push(full + ' 张没存住：本机存储满了，先点「同步」把已有照片传到线上腾出空间');
    if (skipped) parts.push(skipped + ' 个文件不是图片，已跳过');
    toast(parts.join('；') || '没有可用的图片', 15000);
  };
  const recOf = (it) => ({ album: it.album, albumDate: it.albumDate, file: it.file, caption: it.caption, size: it.size });

  // ---- 第一步：纯本机解码 + 压缩（可以并行，吃本机 CPU） ----
  const chosen = [];
  list.forEach(f => {
    if (!/^image\\//.test(f.type) && !/\\.(jpe?g|png|webp|gif|bmp|heic|heif)$/i.test(f.name)) { skipped++; return; }
    chosen.push(f);
  });
  const items = [];
  const total = chosen.length;
  if (!total) { summary(); return; }
  const maybeGo = () => { if (read >= total) step2(items); };
  chosen.forEach((f, i) => {
    const img = new Image();
    const fr = new FileReader();
    fr.onerror = () => { bad.push(f.name); read++; maybeGo(); };
    fr.onload = () => {
      img.onerror = () => { bad.push(f.name + '（浏览器认不出这个格式）'); read++; maybeGo(); };
      img.onload = () => {
        try {
          const MAX = 1200;                        // 手机上小一点：省流量、传得动
          let w = img.width, h = img.height;
          if (w > MAX) { h = Math.round(h * MAX / w); w = MAX; }
          const cv = document.createElement('canvas');
          cv.width = w; cv.height = h;
          cv.getContext('2d').drawImage(img, 0, 0, w, h);
          const data = cv.toDataURL('image/jpeg', 0.78);
          items.push({
            album, albumDate: (album.match(/\\d{4}/) || [todayStr().slice(0, 4)])[0],
            file: 'up_' + Date.now() + '_' + i + '.jpg',
            caption: f.name.replace(/\\.[^.]+$/, '').slice(0, 18),
            size: Math.round(data.length * 0.75),
            data, fname: f.name,
          });
        } catch (e) {
          bad.push(f.name + '（压缩失败：' + String((e && e.message) || e).slice(0, 30) + '）');
        }
        read++; maybeGo();
      };
      img.src = fr.result;
    };
    feedPhoto(f, fr, () => { bad.push(f.name + '（HEIC 转不出来）'); read++; maybeGo(); });
  });

  // ---- 第二步：一张一张传（串行 + 自动重试）；没令牌就只存本机 ----
  async function step2(its) {
    if (!direct) {
      its.forEach(it => {
        l.photos.push(Object.assign({ data: it.data }, recOf(it)));
        if (!saveLocalOv()) { l.photos.pop(); full++; } else kept++;
      });
      ok = kept; summary(); return;
    }
    const n = its.length;
    const prog = (k) => toast('正在传第 ' + k + ' / ' + n + ' 张照片…（别切到别的 App，传完会提示）', 15000);
    if (n) prog(1);
    for (let k = 0; k < n; k++) {
      if (k > 0) prog(k + 1);
      const it = its[k];
      PHOTO_PREVIEW[it.file] = it.data;            // 本机先能预览
      const r = await uploadOne(cfg, 'images/' + it.file, String(it.data).split(',')[1],
                                '上传照片 ' + album + ' / ' + it.file, 3);
      if (r.ok) { ok++; l.photos.push(recOf(it)); saveLocalOv(); continue; }
      // 传不上去也别丢：退回本机待同步列表（带着图片数据），以后点「同步」还能补传
      l.photos.push(Object.assign({ data: it.data }, recOf(it)));
      if (!saveLocalOv()) { l.photos.pop(); full++; } else kept++;
      fail.push(it.fname + '（' + r.error.slice(0, 60) + '）');
    }
    if (kept) toast('有 ' + kept + ' 张没传上去，但已经存在本机待同步列表里了 —— 网络好了点「同步」就能补传', 15000);
    summary();
  }
}

'''

src = src[:i0] + new_handle + src[i1:]

# ---------- 2) 选图后清空 input.value（同一张再选一次也能触发） ----------
old_pick = """    pd.addEventListener('drop', e => handlePhotos(e.dataTransfer.files));
    pi.onchange = () => handlePhotos(pi.files);"""
new_pick = """    pd.addEventListener('drop', e => handlePhotos(Array.from(e.dataTransfer.files)));
    pi.onchange = () => {                       // 取完就清空：同一张照片再选一次也能触发（手机上重试最常撞）
      const fs = Array.from(pi.files || []);
      pi.value = '';
      handlePhotos(fs);
    };"""
c2 = src.count(old_pick)
src = src.replace(old_pick, new_pick)

# ---------- 3) 新增 uploadOne（放在 ghPut 前面） ----------
anchor = 'async function ghPut(cfg, path, b64, message) {'
if anchor not in src:
    print('找不到 ghPut 锚点'); sys.exit(1)
upload_one = u'''/** 一张照片：失败自动重试（手机上网络抖动/限流很常见）；401/404 这种重试没用的直接放弃 */
async function uploadOne(cfg, path, b64, message, tries) {
  const max = tries || 3;
  let last = null;
  for (let n = 1; n <= max; n++) {
    try { await ghPut(cfg, path, b64, message); return { ok: true }; }
    catch (e) {
      last = e;
      const msg = String((e && e.message) || e);
      const fatal = / 401/.test(msg) || / 404/.test(msg);   // 令牌无效/仓库分支不对：重试也是白试
      if (n >= max || fatal) break;
      await new Promise(r => setTimeout(r, n === 1 ? 1200 : 3500));
    }
  }
  return { ok: false, error: String((last && last.message) || last) };
}

'''
src = src.replace(anchor, upload_one + anchor, 1)

# ---------- 写回（保持 CRLF 行尾，别搞出 \\r\\r\\n） ----------
src = src.replace('\r\n', '\n').replace('\n', '\r\n')
io.open(P, 'w', encoding='utf-8', newline='').write(src)

print('handlePhotos 替换：OK')
print('选图清空替换处数：%d（应为 1）' % c2)
print('uploadOne 插入：OK')
print('长度 %d → %d' % (len(orig), len(src)))
