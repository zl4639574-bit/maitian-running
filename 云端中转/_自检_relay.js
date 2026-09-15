/* 自检：中转代码（真跑一遍，不连云）—— node 云端中转/_自检_relay.js  */
const path = require('path');
const relay = require('./relay.js');

let ok = true;
const check = (label, cond, extra) => {
  console.log('   ' + (cond ? '✅' : '❌') + ' ' + label + (extra ? '　' + extra : ''));
  if (!cond) ok = false;
};
const env = { GH_TOKEN: 'github_pat_TEST', GH_OWNER: 'o', GH_REPO: 'r', GH_BRANCH: 'master', TEAM_CODE: 'maitian-2017' };
Object.assign(process.env, env);          // 三个平台入口读的都是 process.env
const goodScores = { code: 'maitian-2017', type: 'scores', payload: { date: '2026.09.15',
  rows: [{ name: '李小龙', event: '5000米', fmt: '17:52', sec: 1072, date: '2026.09.15', meet: '校运会' }] } };
const goodMember = { code: 'maitian-2017', type: 'member', payload: { name: '汪楷', sex: '男', college: '林学院',
  major: '林学2301', grade: '2023', pb: { '5000米': '18:35', '半马': '无' },
  photo: 'data:image/jpeg;base64,' + 'A'.repeat(400) } };

// 假的 GitHub：记下每次 PUT
let puts = [];
let nextStatus = 200;
const realFetch = global.fetch;
global.fetch = async (url, opt) => {
  puts.push({ url: String(url), body: JSON.parse(opt.body || '{}') });
  const st = nextStatus;
  return { ok: st >= 200 && st < 300, status: st, text: async () => '{"message":"stub"}' };
};
let ipSeq = 0;
const ev = (body, method, headers) => ({ method: method || 'POST', body: typeof body === 'string' ? body : JSON.stringify(body),
  headers: Object.assign({ 'x-forwarded-for': '10.0.0.' + (++ipSeq % 250) }, headers || {}) });

(async () => {
  console.log('① 正常提交（三种入口都要能跑）');
  let r = await relay.main_handler(ev(goodScores), {});
  check('SCF main_handler：成绩提交成功', r.statusCode === 200 && JSON.parse(r.body).ok === true, r.body.slice(0, 60));
  r = await relay.main(ev(goodMember), {});
  check('CloudBase main：资料提交成功', r.statusCode === 200 && JSON.parse(r.body).ok === true);
  r = await relay.handler(ev(goodScores), {});
  check('阿里云 FC handler（事件形态）：成功', r.statusCode === 200 && JSON.parse(r.body).ok === true);
  check('兼容 base64 请求体（部分网关会编码）',
    (await relay.main_handler({ httpMethod: 'POST', isBase64Encoded: true, body: Buffer.from(JSON.stringify(goodScores)).toString('base64'), headers: {} }, {})).statusCode === 200);

  console.log('\n①b 腾讯云「函数 URL」风格事件（API 网关触发器已下线 → 走函数 URL）');
  r = await relay.main_handler({ requestContext: { http: { method: 'POST' } }, isBase64Encoded: true,
    headers: { 'x-forwarded-for': '10.9.9.9' }, body: Buffer.from(JSON.stringify(goodScores)).toString('base64') }, {});
  check('函数URL（requestContext.http.method + base64）：成功', r.statusCode === 200 && JSON.parse(r.body).ok === true, r.body.slice(0, 40));
  r = await relay.main_handler({ httpMethod: 'POST', headers: { 'x-forwarded-for': '10.9.9.10' }, body: goodScores }, {});
  check('body 已经是对象：也能处理', r.statusCode === 200 && JSON.parse(r.body).ok === true);
  r = await relay.main_handler({ httpMethod: 'POST', headers: { 'x-forwarded-for': '10.9.9.11' },
    code: 'maitian-2017', type: 'scores', payload: goodScores.payload }, {});
  check('字段被铺平在 event 上：也能处理', r.statusCode === 200 && JSON.parse(r.body).ok === true);
  r = await relay.main_handler({ httpMethod: 'POST', headers: { 'content-type': 'text/plain;charset=UTF-8', 'x-forwarded-for': '10.9.9.12' },
    body: JSON.stringify(goodScores) }, {});
  check('Content-Type 是 text/plain 也照收（客户端靠这个绕开跨域预检）', r.statusCode === 200);

  console.log('\n② 写到哪、怎么写（只新增、不覆盖）');
  const last = puts[puts.length - 1];
  check('写到 data/inbox/ 下的 .json', /\/contents\/data\/inbox\/\d{14}-[a-z0-9]+\.json$/.test(last.url), last.url.slice(-40));
  check('提交内容里没有 sha（⇒ 只能新建，覆盖不了已有文件）', last.body.sha === undefined);
  check('带上了分支 master', last.body.branch === 'master');
  const written = JSON.parse(Buffer.from(last.body.content, 'base64').toString('utf8'));
  check('文件里是标准结构 {id,type,at,data}', !!written.id && written.type === 'maitian-scores' && !!written.data.rows);
  const memberPut = puts.find(p => JSON.parse(Buffer.from(p.body.content, 'base64').toString('utf8')).type === 'maitian-member');
  const md = JSON.parse(Buffer.from(memberPut.body.content, 'base64').toString('utf8'));
  check('资料里保留了照片和成绩', md.data.photo.startsWith('data:image/') && md.data.pb['5000米'] === '18:35');
  check('"无"的项目被剔除', md.data.pb['半马'] === undefined);

  console.log('\n③ 防滥用');
  r = await relay.main_handler(ev({ ...goodScores, code: 'wrong' }), {});
  check('口令不对 → 400', r.statusCode === 400 && /口令/.test(r.body));
  r = await relay.main_handler({ httpMethod: 'OPTIONS', headers: {} }, {});
  check('预检 OPTIONS → 204（跨域必须）', r.statusCode === 204 && r.headers['Access-Control-Allow-Origin'] === '*');
  r = await relay.main_handler({ httpMethod: 'GET', headers: {} }, {});
  check('GET → 405', r.statusCode === 405);
  r = await relay.main_handler({ httpMethod: 'POST', body: 'not json', headers: {} }, {});
  check('不是 JSON → 400', r.statusCode === 400);
  r = await relay.main_handler(ev({ code: 'maitian-2017', type: 'member', payload: { name: 'abc<script>', pb: {} } }), {});
  check('姓名非法 → 400', r.statusCode === 400);
  r = await relay.main_handler(ev({ code: 'maitian-2017', type: 'scores', payload: { rows: [] } }), {});
  check('没有成绩行 → 400', r.statusCode === 400);
  const big = { code: 'maitian-2017', type: 'member', payload: { name: '汪楷', photo: 'data:image/jpeg;base64,' + 'A'.repeat(300 * 1024) } };
  r = await relay.main_handler(ev(big), {});
  check('超过 200KB → 400（照片不会把仓库塞爆）', r.statusCode === 400, JSON.parse(r.body).error);
  // 限流：连续 6 次同 IP
  let last429 = 0;
  for (let i = 0; i < 6; i++) {
    const rr = await relay.main_handler(ev(goodScores, 'POST', { 'x-forwarded-for': '9.9.9.9' }), {});
    if (rr.statusCode === 429) last429++;
  }
  check('同一 IP 超过 5 次/分钟 → 429 限流', last429 >= 1, '被拦 ' + last429 + ' 次');

  console.log('\n④ GitHub 侧出错时的提示');
  nextStatus = 403;
  r = await relay.main_handler(ev(goodScores), {});
  check('令牌没权限 → 明确提示改 Contents 权限', r.statusCode === 500 && /Read and write/.test(r.body), JSON.parse(r.body).error);
  nextStatus = 422;
  r = await relay.main_handler(ev(goodScores), {});
  check('重复提交（同名已存在）→ 409 不让覆盖', r.statusCode === 409, JSON.parse(r.body).error);
  nextStatus = 500;
  r = await relay.main_handler(ev(goodScores), {});
  check('GitHub 500 → 502 并说明写仓库失败', r.statusCode === 502, JSON.parse(r.body).error);
  const keepToken = process.env.GH_TOKEN;
  delete process.env.GH_TOKEN;
  r = await relay.main_handler(ev(goodScores), {});
  check('缺 GH_TOKEN → 提示"还没配好"', r.statusCode === 500 && /还没配好/.test(r.body), JSON.parse(r.body).error);
  process.env.GH_TOKEN = keepToken;

  global.fetch = realFetch;
  console.log('\n总判定：' + (ok ? '✅ 全部通过' : '❌ 有项目未通过'));
  process.exit(ok ? 0 : 1);
})();
