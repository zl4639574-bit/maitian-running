/* 诊断 2：把导出的函数调起来，看它返回什么（node _诊断_libheif导出2.js） */
const fs = require('fs'), path = require('path');
const p = path.join(__dirname, 'assets', 'libheif-bundle.js');

function shape(tag, o) {
  console.log('== ' + tag + ' ==');
  if (o === undefined) { console.log('  undefined'); return; }
  if (o === null) { console.log('  null'); return; }
  console.log('  typeof =', typeof o, ' 是 Promise =', typeof o.then === 'function');
  let own = [];
  try { own = Object.getOwnPropertyNames(o); } catch (e) { own = ['<err>']; }
  console.log('  own props(' + own.length + ') =', own.slice(0, 25).join(','));
  console.log('  HeifDecoder =', typeof o.HeifDecoder, ' HeifImage =', typeof o.HeifImage);
}

(async () => {
  const lib = require(p);
  console.log('导出类型:', typeof lib, ' 函数名:', lib.name, ' 参数个数:', lib.length);
  for (const args of [[], [{}]]) {
    try {
      const r = lib.apply(null, args);
      shape('lib(' + JSON.stringify(args) + ')', r);
      if (r && typeof r.then === 'function') {
        const mod = await r;
        shape('await lib(' + JSON.stringify(args) + ')', mod);
        if (mod && mod.HeifDecoder) {
          console.log('>>> 正确用法: const mod = await libheif({}); new mod.HeifDecoder()');
          return;
        }
      } else if (r && r.HeifDecoder) {
        console.log('>>> 正确用法: const mod = libheif({}); new mod.HeifDecoder()');
        return;
      }
    } catch (e) { console.log('lib(' + JSON.stringify(args) + ') 抛错:', e.message); }
  }
})();
