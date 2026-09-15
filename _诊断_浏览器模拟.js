/* 模拟浏览器：没有 module/exports 的情况下加载 libheif-bundle.js，看 window.libheif 是什么
   （node _诊断_浏览器模拟.js）*/
const fs = require('fs'), path = require('path'), vm = require('vm');
const src = fs.readFileSync(path.join(__dirname, 'assets', 'libheif-bundle.js'), 'utf8');
const sb = { console, setTimeout, clearTimeout, atob, btoa };
sb.window = sb; sb.self = sb; sb.globalThis = sb;
vm.createContext(sb);
vm.runInContext(src, sb, { filename: 'libheif-bundle.js' });
console.log('浏览器模拟：window.libheif 类型 =', typeof sb.libheif);
try {
  const mod = typeof sb.libheif === 'function' ? sb.libheif({}) : sb.libheif;
  console.log('调用工厂后 HeifDecoder =', typeof (mod && mod.HeifDecoder), ' HeifImage =', typeof (mod && mod.HeifImage));
  console.log('结论:', mod && mod.HeifDecoder ? 'PASS 浏览器里可用' : 'FAIL');
} catch (e) { console.log('调用工厂失败:', e.message, '\n结论: FAIL'); }
