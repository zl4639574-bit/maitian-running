// 成绩解析自检（node，不用浏览器）
// 1) 表格用例：写法定 → 期望秒数
// 2) 回归：把线上现有数据里所有成绩的原始写法重新解析一遍，除了已知会被修正的少数，
//    结果必须跟线上存的值一致（不许把老数据读歪）
const fs = require('fs');
const path = require('path');
const HERE = __dirname;

// ── 从 app.js 里抠出成绩解析这几个函数（保持和线上同一份代码）──
const src = fs.readFileSync(path.join(HERE, 'assets', 'app.js'), 'utf8');
const i0 = src.indexOf('const SEC_RANGE = [');
const i1 = src.indexOf('function distM(');
if (i0 < 0 || i1 < 0) { console.error('抠不出解析函数'); process.exit(2); }
const code = src.slice(i0, i1);
eval(code);   // 定义 SEC_RANGE / secRange / pickSec / parseSec / fmtSec / secSuspicion

let bad = 0, n = 0;
function eq(input, ev, want, label) {
  n++;
  const sec = parseSec(input, ev);
  const got = sec === null ? null : Math.round(sec * 10) / 10;
  const ok = (got === want);
  if (!ok) { bad++; console.log('❌ ' + label + '  parseSec(' + JSON.stringify(input) + ', ' + JSON.stringify(ev) + ') = ' + got + '，期望 ' + want + '（' + (sec ? fmtSec(sec) : '-') + '）'); }
  else console.log('✅ ' + label + '  ' + JSON.stringify(input) + ' [' + ev + '] → ' + fmtSec(got));
}

console.log('=== 1) 这次报的 bug ===');
eq('1:24:00', '半马', 5040, '半马 1:24:00');
eq('1:24', '半马', 5040, '半马 1:24');
eq('1:24:30', '半马', 5070, '半马 1:24:30');
eq('4:20:00', '全马', 15600, '全马 4:20:00');
eq('2:58', '全马', 10680, '全马 2:58');
eq('1:23:29', '半马', 5009, '半马 1:23:29');

console.log('\n=== 2) 老写法不能被读歪（短距离）===');
eq('17:35', '5000米', 1055, '5000米 17:35');
eq('17:02:00', '5000米', 1022, '5000米 17:02:00（Excel 小时槽=分钟）');
eq('2:15:00', '800米', 135, '800米 2:15:00');
eq('2:15', '800米', 135, '800米 2:15');
eq('5:00:00', '1500米', 300, '1500米 5:00:00');
eq('10:10:00', '3000米', 610, '3000米 10:10:00');
eq('37:30:00', '10000米', 2250, '10000米 37:30:00');
eq('18:35', '5000米', 1115, '5000米 18:35');
eq("18'35\"", '5000米', 1115, '5000米 18\'35"');
eq('18.5', '5000米', 1110, '5000米 18.5（分钟）');
eq('1022', '5000米', 1022, '5000米 1022（秒数）');
eq('1:04:30', '半马', 3870, '半马 1:04:30');
eq('84', '半马', 5040, '半马 84（写分钟）');
eq('1:24:00', '', 5040, '不知道项目时的 1:24:00（默认按时:分:秒）');
eq('17:02:00', '', 1022, '不知道项目时的 17:02:00（17 小时太离谱 → 按分:秒）');
eq('0:17:02', '5000米', 1022, '5000米 0:17:02');
eq(0.0583333, '半马', 5040, '半马 Excel 真时间 0.0583');
eq(0.7097222, '5000米', 1022, '5000米 Excel 小时槽 0.7097');

console.log('\n=== 3) 回归：线上现有数据重新解析一遍 ===');
function load(p) {
  const t = fs.readFileSync(p, 'utf8').replace(/^\uFEFF/, '');
  const a = t.indexOf('{'), b = t.lastIndexOf('}');
  if (a < 0 || b < 0) throw new Error('这个文件里没有 JSON：' + p);
  return JSON.parse(t.slice(a, b + 1));
}
const BASE = load(path.join(HERE, 'data', 'team-data.js'));
const OV = load(path.join(HERE, 'data', 'overrides.js'));
const recs = [];
(BASE.datasets || []).forEach(ds => (ds.records || []).forEach(r => recs.push({ r: r, ev: r.event || (ds.events && ds.events[0] ? ds.events[0].event : '') })));
(BASE.pb || []).forEach(r => recs.push({ r: r, ev: r.event }));
(OV.compRecords ? Object.keys(OV.compRecords) : []).forEach(k => (OV.compRecords[k] || []).forEach(r => recs.push({ r: r, ev: r.event })));
(OV.results || []).forEach(r => recs.push({ r: r, ev: r.event }));
(OV.pbAdded || []).forEach(r => recs.push({ r: r, ev: r.event }));
let diffs = 0, checked = 0, changed = [];
recs.forEach(x => {
  const r = x.r;
  const rawIn = (r.raw && String(r.raw).trim()) ? r.raw : (r.fmt || '');
  if (!rawIn && !r.sec) return;
  const news = parseSec(rawIn, x.ev);
  if (news === null) { return; }
  checked++;
  const old = Math.round(Number(r.sec) * 10) / 10, now = Math.round(news * 10) / 10;
  if (Math.abs(old - now) > 0.6) { diffs++; changed.push([r.name, x.ev, rawIn, old, now]); }
});
console.log('  复查 ' + checked + ' 条；与线上存量不一致的：' + diffs);
changed.slice(0, 25).forEach(c => console.log('   · ' + c[0] + ' ' + c[1] + ' 「' + c[2] + '」 线上=' + c[3] + '(' + fmtSec(c[3]) + ') → 现在会读成 ' + c[4] + '(' + fmtSec(c[4]) + ')'));
if (changed.length > 25) console.log('   … 还有 ' + (changed.length - 25) + ' 条');
const onlyLong = changed.every(c => /半马|全马|半程|全程|马拉松/.test(c[1]) || c[3] < 300);
console.log('  不一致的是不是都落在"半马/全马被读成 1 分多"这一类：' + (onlyLong ? '是 ✅（正是要修的 bug）' : '不是 ❌ 需要人工看'));

console.log('\n' + (bad === 0 && onlyLong ? '✅ 全部通过（表格 ' + n + ' 项；回归 ' + checked + ' 条）' : '❌ 有问题：表格失败 ' + bad + ' 项'));
process.exit(bad === 0 && onlyLong ? 0 : 1);
