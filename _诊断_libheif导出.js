/* 诊断 libheif 解码器到底导出了什么（node _诊断_libheif导出.js） */
const fs = require('fs'), path = require('path'), vm = require('vm');
const p = path.join(__dirname, 'assets', 'libheif-bundle.js');
const src = fs.readFileSync(p, 'utf8');

function shape(tag, o) {
  console.log('== ' + tag + ' ==');
  if (o === undefined) { console.log('  undefined'); return; }
  if (o === null) { console.log('  null'); return; }
  console.log('  typeof =', typeof o);
  console.log('  是 Promise =', o && typeof o.then === 'function');
  console.log('  ctor =', o.constructor && o.constructor.name);
  let own = [];
  try { own = Object.getOwnPropertyNames(o); } catch (e) { own = ['<err ' + e.message + '>']; }
  console.log('  own props(' + own.length + ') =', own.slice(0, 30).join(','));
  if (o.HeifDecoder) console.log('  HeifDecoder =', typeof o.HeifDecoder);
  if (o.default) console.log('  default =', typeof o.default, o.default && typeof o.default.HeifDecoder);
}

(async () => {
  let m = null;
  try { m = require(p); } catch (e) { console.log('require 抛错:', e.message); }
  shape('require()', m);
  if (m && typeof m.then === 'function') shape('await require()', await m);

  const sandbox = { module: { exports: {} }, exports: {}, console, process, require, Buffer,
    TextDecoder, TextEncoder, URL, setTimeout, clearTimeout, Promise };
  sandbox.globalThis = sandbox;
  let v = null;
  try {
    v = vm.runInNewContext(src + '\n;typeof libheif!=="undefined"?libheif:undefined', sandbox, { filename: 'libheif-bundle.js' });
    shape('vm 里的 libheif 变量', v);
  } catch (e) { console.log('vm 跑错:', e.message); }
  if (v && typeof v.then === 'function') shape('await vm libheif', await v);
  else if (v && v.default && typeof v.default.then === 'function') shape('await vm libheif.default', await v.default);
})();
