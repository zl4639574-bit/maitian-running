/**
 * 麦田守望长跑队 · 云端中转函数
 * ------------------------------------------------------------------
 * 作用：网页里不再有任何令牌。网页只调用本函数，本函数用存在
 *       环境变量里的 GitHub 令牌去读写仓库。谁打开网页都只点按钮。
 *
 * 环境变量（在云函数控制台里配置，不写进代码）：
 *   GH_TOKEN   = github_pat_... / ghp_...   （必须有 Contents: Read and write 权限）
 *   GH_OWNER   = zl4639574-bit              （可省略，默认就是这个）
 *   GH_REPO    = maitian-running            （可省略）
 *   GH_BRANCH  = master                     （可省略）
 *
 * 接口：
 *   GET  /ping          → {"ok":true,...}   用于确认函数活着
 *   GET  /data          → 返回当前线上 overrides 数据
 *   POST /save          → {"overrides":{...}} 提交数据（会写进仓库）
 *   POST /photo         → {"name":"xxx.jpg","data":"<base64>"} 上传一张照片
 *   POST /delete-photo  → {"name":"xxx.jpg"} 删除一张照片
 *
 * 单文件、零依赖，Node.js 18+ 可直接跑（阿里云 FC / 腾讯云 SCF 的 Web 函数都行）。
 */

const API = 'https://api.github.com';

const CFG = {
  owner: process.env.GH_OWNER || 'zl4639574-bit',
  repo: process.env.GH_REPO || 'maitian-running',
  branch: process.env.GH_BRANCH || 'master',
  token: process.env.GH_TOKEN || '',
  dataPath: process.env.DATA_PATH || 'data/overrides.js',
};

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Max-Age': '600',
};

function reply(statusCode, obj) {
  return {
    statusCode,
    headers: Object.assign({ 'Content-Type': 'application/json; charset=utf-8' }, CORS),
    body: typeof obj === 'string' ? obj : JSON.stringify(obj),
  };
}

function ghHeaders() {
  return {
    Authorization: 'Bearer ' + CFG.token,
    Accept: 'application/vnd.github+json',
    'User-Agent': 'maitian-relay',
    'Content-Type': 'application/json',
  };
}

async function ghGet(path) {
  const r = await fetch(API + path, { headers: ghHeaders() });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error('GitHub 读取失败 ' + r.status + ' ' + (await r.text()).slice(0, 200));
  return r.json();
}

async function ghPut(path, contentB64, message) {
  // 先取 sha（文件已存在时必须带）
  let sha = null;
  const cur = await ghGet(`/repos/${CFG.owner}/${CFG.repo}/contents/${encodeURI(path)}?ref=${encodeURIComponent(CFG.branch)}`);
  if (cur && cur.sha) sha = cur.sha;
  const body = { message, content: contentB64, branch: CFG.branch };
  if (sha) body.sha = sha;
  const r = await fetch(API + `/repos/${CFG.owner}/${CFG.repo}/contents/${encodeURI(path)}`, {
    method: 'PUT', headers: ghHeaders(), body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error('GitHub 写入失败 ' + r.status + ' ' + (await r.text()).slice(0, 300));
  return r.json();
}

async function ghDelete(path, message) {
  const cur = await ghGet(`/repos/${CFG.owner}/${CFG.repo}/contents/${encodeURI(path)}?ref=${encodeURIComponent(CFG.branch)}`);
  if (!cur || !cur.sha) return { ok: true, skipped: '文件不存在' };
  const r = await fetch(API + `/repos/${CFG.owner}/${CFG.repo}/contents/${encodeURI(path)}`, {
    method: 'DELETE', headers: ghHeaders(),
    body: JSON.stringify({ message, sha: cur.sha, branch: CFG.branch }),
  });
  if (!r.ok) throw new Error('GitHub 删除失败 ' + r.status + ' ' + (await r.text()).slice(0, 200));
  return r.json();
}

function b64(str) { return Buffer.from(str, 'utf8').toString('base64'); }

async function handle(method, path, body) {
  if (method === 'OPTIONS') return { statusCode: 204, headers: CORS, body: '' };

  if (path === '/ping' || path === '/' || path === '') {
    return reply(200, { ok: true, service: '麦田守望数据中心中转', repo: CFG.owner + '/' + CFG.repo,
                        branch: CFG.branch, hasToken: !!CFG.token });
  }

  if (path === '/data' && method === 'GET') {
    const f = await ghGet(`/repos/${CFG.owner}/${CFG.repo}/contents/${encodeURI(CFG.dataPath)}?ref=${encodeURIComponent(CFG.branch)}`);
    if (!f) return reply(200, { overrides: null });
    const txt = Buffer.from(f.content, 'base64').toString('utf8');
    const m = txt.match(/=\s*([\s\S]*?);\s*$/);
    let ov = null;
    try { ov = m ? JSON.parse(m[1]) : null; } catch (e) {}
    return reply(200, { overrides: ov });
  }

  if (path === '/save' && method === 'POST') {
    if (!body || typeof body !== 'object') return reply(400, { error: '请提交 JSON' });
    const ov = body.overrides;
    if (!ov || typeof ov !== 'object') return reply(400, { error: '缺少 overrides 字段' });
    const txt = '/* 由云端中转自动写入 */\nwindow.TEAM_OVERRIDES = ' + JSON.stringify(ov, null, 1) + ';\n';
    if (txt.length > 3.5 * 1024 * 1024) return reply(413, { error: '数据太大（超过 3.5MB）' });
    await ghPut(CFG.dataPath, b64(txt), '网页提交：更新队伍数据');
    return reply(200, { ok: true, saved: txt.length });
  }

  if (path === '/photo' && method === 'POST') {
    const { name, data } = body || {};
    if (!name || !data) return reply(400, { error: '缺少 name / data' });
    const clean = String(name).replace(/[^\w.\-]/g, '_');
    const target = 'images/' + (/\.(jpg|jpeg|png|webp)$/i.test(clean) ? clean : clean + '.jpg');
    await ghPut(target, String(data).replace(/^data:[^,]+,/, ''), '网页提交：上传照片 ' + target);
    return reply(200, { ok: true, file: target });
  }

  if (path === '/delete-photo' && method === 'POST') {
    const { name } = body || {};
    if (!name) return reply(400, { error: '缺少 name' });
    await ghDelete('images/' + String(name).replace(/[^\w.\-]/g, '_'), '网页提交：删除照片');
    return reply(200, { ok: true });
  }

  return reply(404, { error: '未知接口 ' + path });
}

/* ------------------------------------------------------------------
   入口：兼容阿里云函数计算 FC（Web 函数）和腾讯云云函数 SCF（Web 函数）
   ------------------------------------------------------------------ */
async function run(event) {
  try {
    const method = (event.httpMethod || (event.requestContext && event.requestContext.http && event.requestContext.http.method)
                    || (event.requestContext && event.requestContext.httpMethod) || 'GET').toUpperCase();
    let path = event.path || event.rawPath || (event.requestContext && event.requestContext.http && event.requestContext.http.path) || '/';
    path = String(path).replace(/^\/[^/]*\.(run|fcapp|tcloudbaseapp)\//, '/');  // 有些平台会在 path 前拼函数名
    path = '/' + String(path).replace(/^\/+/, '').split('?')[0];
    let body = null;
    if (event.body) {
      const raw = event.isBase64Encoded ? Buffer.from(event.body, 'base64').toString('utf8') : event.body;
      try { body = JSON.parse(raw); } catch (e) { body = null; }
    }
    return await handle(method, path, body);
  } catch (e) {
    return reply(500, { error: String(e && e.message || e) });
  }
}

exports.handler = (event, context) => run(event || {});              // 阿里云 FC
exports.main_handler = (event, context) => run(event || {});         // 腾讯云 SCF
exports.main = (event, context) => run(event || {});                 // 其他平台
if (require.main === module) {                                        // 本地自测：node relay.js
  run({ httpMethod: 'GET', path: '/ping' }).then(r => console.log(r.statusCode, r.body));
}
