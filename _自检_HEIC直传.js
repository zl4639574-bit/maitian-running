/* HEIC 直传自检（Node）：直接拿 assets/app.js 里真正的函数跑一遍
   用法：node _自检_HEIC直传.js _测_HEIC_左红右蓝.heic   */
const fs = require('fs'), path = require('path');
const repo = __dirname;

const app = fs.readFileSync(path.join(repo, 'assets', 'app.js'), 'utf8');
const i0 = app.indexOf('let _heifLoading');
const i1 = app.indexOf('/** 统一的取图入口');
if (i0 < 0 || i1 < 0) { console.log('EXTRACT_FAIL 提取不到 HEIC 代码段'); process.exit(1); }
const src = app.slice(i0, i1);

/* 加载内置解码器：先试 require，失败再用 window 垫片 eval */
let libheif = null, how = '';
try { libheif = require(path.join(repo, 'assets', 'libheif-bundle.js')); how = 'require'; }
catch (e) {
  try {
    const g = {}; g.window = g; g.self = g; g.globalThis = g;
    new Function('window', 'self', 'globalThis', 'module', 'exports',
      fs.readFileSync(path.join(repo, 'assets', 'libheif-bundle.js'), 'utf8'))
      (g, g, g, { exports: {} }, {});
    libheif = g.libheif; how = 'window-shim';
  } catch (e2) { console.log('LOAD_FAIL 解码器加载不了:', e.message, '/', e2.message); process.exit(1); }
}
console.log('解码器加载方式:', how, ' HeifDecoder:', typeof (libheif && libheif.HeifDecoder));

let captured = null, decodeMs = 0;
const fakeDoc = {
  createElement() {
    const cv = { width: 0, height: 0 };
    cv.getContext = () => ({
      createImageData: (w, h) => ({ data: new Uint8ClampedArray(w * h * 4), width: w, height: h }),
      putImageData: (idt) => { captured = idt; },
      drawImage: () => {}
    });
    cv.toDataURL = () => 'data:image/raw;base64,' +
      Buffer.from(captured.data.buffer, captured.data.byteOffset, captured.data.length).toString('base64');
    return cv;
  },
  head: { appendChild() {} }
};
const win = { libheif };
const toast = (m) => console.log('[toast]', m);

const api = new Function('window', 'document', 'toast', 'ROOT',
  src + '\nreturn { isHeicBytes: isHeicBytes, heicToJpegDataUrl: heicToJpegDataUrl };')(win, fakeDoc, toast, '');

const heicPath = process.argv[2] || path.join(repo, '_测_HEIC_左红右蓝.heic');
const buf = fs.readFileSync(heicPath);
const ab = (o, n) => buf.buffer.slice(buf.byteOffset + o, buf.byteOffset + Math.min(o + n, buf.length));

console.log('真 HEIC 前 16 字节 brand =', ab(8, 4).byteLength ? String.fromCharCode.apply(null, new Uint8Array(ab(4, 4))) + '/' + String.fromCharCode.apply(null, new Uint8Array(ab(8, 4))) : '?');
console.log('[断言1] 真 HEIC 被识别:', api.isHeicBytes(ab(0, 16)) === true ? 'PASS' : 'FAIL ' + api.isHeicBytes(ab(0, 16)));
const jpgHead = new Uint8Array([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00]).buffer;
console.log('[断言2] 普通 JPG 不误判:', api.isHeicBytes(jpgHead) === false ? 'PASS' : 'FAIL');
const mp4Head = new Uint8Array([0, 0, 0, 0x18, 0x66, 0x74, 0x79, 0x70, 0x6D, 0x70, 0x34, 0x32, 0, 0, 0, 0]).buffer;
console.log('[断言3] mp4 视频不误判:', api.isHeicBytes(mp4Head) === false ? 'PASS' : 'FAIL');

const file = {
  slice: (a, b) => ({ arrayBuffer: async () => ab(a, b - a) }),
  arrayBuffer: async () => ab(0, buf.length)
};

(async () => {
  const t0 = Date.now();
  let out = null, err = null;
  try { out = await api.heicToJpegDataUrl(file); } catch (e) { err = e; }
  decodeMs = Date.now() - t0;
  console.log('转换耗时', decodeMs, 'ms');
  if (err) { console.log('[断言4] HEIC → JPG:', 'FAIL 抛错:', (err && (err.message || err)) + ''); process.exit(2); }
  if (!out || !captured) { console.log('[断言4] HEIC → JPG: FAIL 没转出图像'); process.exit(2); }
  const W = captured.width, H = captured.height;
  const raw = Buffer.from(out.split(',')[1], 'base64');
  const px = (x, y) => { const o = (y * W + x) * 4; return [captured.data[o], captured.data[o + 1], captured.data[o + 2]]; };
  const near = (p, r, g, b, tol) => Math.abs(p[0] - r) < tol && Math.abs(p[1] - g) < tol && Math.abs(p[2] - b) < tol;
  const A = px(80, 80), B = px(W - 80, 80), C = px(80, H - 80);
  console.log('尺寸', W + 'x' + H, ' / 像素字节', raw.length);
  console.log('左上角(应绿 0,255,0)', A, near(A, 0, 255, 0, 40) ? 'PASS' : 'FAIL');
  console.log('右上(应蓝 0,0,255)', B, near(B, 0, 0, 255, 40) ? 'PASS' : 'FAIL');
  console.log('左下(应红 255,0,0)', C, near(C, 255, 0, 0, 40) ? 'PASS' : 'FAIL');
  console.log('toDataURL 前缀', out.slice(0, 24));
  console.log('[断言4] HEIC → JPG: PASS');
})();
