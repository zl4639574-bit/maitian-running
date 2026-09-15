# -*- coding: utf-8 -*-
"""H 补丁：iPhone HEIC 照片可以直接上传（内置 libheif 解码器，按需加载）"""
import io, os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'app.js')
s = io.open(P, 'rb').read().decode('utf-8').replace('\r\n', '\n')
done = []


def rep(old, new, label, cnt=1):
    global s
    n = s.count(old)
    assert n == cnt, '✗ %s：期望 %d 处，实际 %d 处' % (label, cnt, n)
    s = s.replace(old, new)
    done.append(label)


HELPERS = '''/* ---------------- iPhone HEIC 照片支持（内置解码器，按需加载） ----------------
   iPhone 直接拍的照片是 HEIC，浏览器不认（就是"打不开"那种）。这里用 libheif 现解：
     · 只在真的选到 HEIC 时才去加载 assets/libheif-bundle.js（1.4MB，本地文件，离线可用）；
     · 解出来转成 JPEG 再走原来的压缩/上传流程，队员什么都不用做。 */
let _heifLoading = null;
function isHeicBytes(buf) {
  if (!buf || buf.byteLength < 12) return false;
  const b = new Uint8Array(buf, 0, 12);
  if (String.fromCharCode(b[4], b[5], b[6], b[7]) !== 'ftyp') return false;
  const brand = String.fromCharCode(b[8], b[9], b[10], b[11]).toLowerCase();
  return ['heic', 'heix', 'hevc', 'hevx', 'heim', 'heis', 'hevm', 'hevs', 'mif1', 'msf1'].indexOf(brand) >= 0;
}
function loadHeifLib() {
  if (window.libheif) return Promise.resolve(window.libheif);
  if (_heifLoading) return _heifLoading;
  _heifLoading = new Promise((res, rej) => {
    const sc = document.createElement('script');
    sc.src = ROOT + 'assets/libheif-bundle.js';
    sc.onload = () => window.libheif ? res(window.libheif) : rej(new Error('解码器加载了但没挂上'));
    sc.onerror = () => { _heifLoading = null; rej(new Error('解码器没加载成功')); };
    document.head.appendChild(sc);
  });
  return _heifLoading;
}
/** HEIC → JPEG 的 dataURL；不是 HEIC 返回 null（调用方继续走原流程） */
async function heicToJpegDataUrl(file) {
  const head = await file.slice(0, 16).arrayBuffer();
  if (!isHeicBytes(head)) return null;
  toast('这是 iPhone 的 HEIC 照片，正在自动转成 JPG…', 9000);
  const lib = await loadHeifLib();
  const data = new Uint8Array(await file.arrayBuffer());
  const imgs = new lib.HeifDecoder().decode(data);
  if (!imgs || !imgs.length) throw new Error('这张 HEIC 解不开');
  const im = imgs[0];
  const w = im.get_width(), h = im.get_height();
  const cv = document.createElement('canvas');
  cv.width = w; cv.height = h;
  const ctx = cv.getContext('2d');
  const idt = ctx.createImageData(w, h);
  await new Promise((res, rej) => im.display(idt, (err) => err ? rej(err) : res()));
  ctx.putImageData(idt, 0, 0);
  return cv.toDataURL('image/jpeg', 0.82);
}
/** 统一的取图入口：HEIC 走解码器，其它原样交给 FileReader */
function feedPhoto(f, fr, onFail) {
  (async () => {
    try {
      const conv = await heicToJpegDataUrl(f);
      if (conv) { fr.onload({ target: { result: conv } }); return; }
    } catch (e) { if (onFail) onFail(e); else toast('这张 HEIC 转不了：' + (e && e.message) + '（可以先在相册里转成 JPG）', 11000); return; }
    fr.readAsDataURL(f);
  })();
}

function shrinkPhoto(file) {'''

rep('function shrinkPhoto(file) {', HELPERS, '① 插入 HEIC 解码工具')

# shrinkPhoto 的读取入口
idx = s.index('function shrinkPhoto(file) {')
seg = s[idx:idx + 3000]
assert 'fr.readAsDataURL(file);' in seg
seg2 = seg.replace('fr.readAsDataURL(file);',
                   'feedPhoto(file, fr, () => toast("这张 HEIC 转不了（可以先用相册转成 JPG 再传）", 11000));', 1)
s = s[:idx] + seg2 + s[idx + 3000:]
done.append('③ shrinkPhoto 走 HEIC 入口')

# handlePhotos 的读取入口
rep('    fr.readAsDataURL(f);\n', '    feedPhoto(f, fr, () => { bad.push(f.name); finish(); });\n', '④ 两处取图入口都走 HEIC', 2)

# 提示语更新
rep("""+ ' —— iPhone 的 HEIC 格式浏览器认不了，先在手机相册里转成 JPG（或微信发给自己会自动转码）再传');""",
    """+ ' —— 这些是 iPhone 的 HEIC 照片，页面会自动转换；如果是网络太慢没加载好解码器，稍后重试一次就行');""",
    '⑤ 失败提示改为"会自动转换"')

io.open(P, 'wb').write(s.replace('\n', '\r\n').encode('utf-8'))
print('\n'.join('   ' + d for d in done))
