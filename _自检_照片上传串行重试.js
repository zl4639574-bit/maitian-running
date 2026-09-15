/* 照片上传自检（Node）：串行 + 重试 + 不丢数据
   用法：node _自检_照片上传串行重试.js  */
const fs = require('fs'), path = require('path');
const app = fs.readFileSync(path.join(__dirname, 'assets', 'app.js'), 'utf8');
const i0 = app.indexOf('/** 一张照片：失败自动重试');
const i1 = app.indexOf('async function ghPut(cfg, path, b64, message) {');
if (i0 < 0 || i1 < 0) { console.log('提取失败'); process.exit(1); }
const src = app.slice(i0, i1);

function makeUploadOne(fakeGhPut) {
  return new Function('ghPut', src + '\nreturn uploadOne;')(fakeGhPut);
}
const err403 = () => new Error('写入 images/up_x.jpg 失败 403｜权限不够：令牌的 Contents 要选 Read and write（或访问太频繁，稍等再试）　{"message":"You have exceeded a secondary rate limit. Please wait a few minutes before you try again."}');
const err401 = () => new Error('写入 images/up_x.jpg 失败 401｜令牌无效或已过期：重新生成一个再粘一次　{"message":"Bad credentials"}');

(async () => {
  let pass = 0, fail = 0;
  const t = (name, cond, extra) => { if (cond) { pass++; console.log('  PASS ' + name); } else { fail++; console.log('  FAIL ' + name + (extra ? ' → ' + extra : '')); } };

  // 1) 限流 403：前两次失败、第三次成功 → 应重试并成功
  {
    let calls = 0, left = 2;
    const fake = async () => { calls++; if (left-- > 0) throw err403(); return {}; };
    const t0 = Date.now();
    const r = await makeUploadOne(fake)({ branch: 'master' }, 'images/a.jpg', 'AAA', 'msg', 3);
    console.log('用例1 重试后成功：调用 ' + calls + ' 次，用时 ' + (Date.now() - t0) + 'ms');
    t('三次内重试成功', r.ok === true, JSON.stringify(r));
    t('确实重试了 3 次', calls === 3, 'calls=' + calls);
  }
  // 2) 一直 403 → 试满 3 次放弃，且带回完整原因（不截断）
  {
    let calls = 0;
    const fake = async () => { calls++; throw err403(); };
    const r = await makeUploadOne(fake)({ branch: 'master' }, 'images/b.jpg', 'BBB', 'msg', 3);
    const reason = String(r.error || '');
    console.log('用例2 放弃时的原因：' + reason.slice(0, 60) + '…（共 ' + reason.length + ' 字）');
    t('失败返回 ok:false', r.ok === false);
    t('试满 3 次', calls === 3, 'calls=' + calls);
    t('原因没被截断（含 GitHub 原文）', reason.length > 100 && /secondary rate limit/.test(reason));
  }
  // 3) 401 令牌无效 → 不该白试 3 次
  {
    let calls = 0;
    const fake = async () => { calls++; throw err401(); };
    const r = await makeUploadOne(fake)({ branch: 'master' }, 'images/c.jpg', 'CCC', 'msg', 3);
    t('401 只试 1 次就放弃', calls === 1 && r.ok === false, 'calls=' + calls);
  }
  // 4) 串行：handlePhotos 里是否真的是一张一张 await（看代码形态第 3 步）
  {
    const ok = /for \(let k = 0; k < n; k\+\+\)[\s\S]{0,400}await uploadOne\(/.test(app);
    t('第二步是 for 循环里 await uploadOne（串行，不是 forEach 并发）', ok);
  }
  // 5) 传失败的照片会退回本机待同步列表（不丢）
  {
    const ok = /传不上去也别丢[\s\S]{0,300}l\.photos\.push\(Object\.assign\(\{ data: it\.data \}, recOf\(it\)\)\)/.test(app);
    t('失败的照片带 data 退回本机待同步', ok);
  }
  // 6) 选图后清空 value（同一张再选能触发）
  {
    t('input.value 选完就清空', /pi\.value = '';\s*\n\s*handlePhotos\(fs\)/.test(app));
  }
  console.log('\n结果：' + pass + ' 项通过，' + fail + ' 项失败');
  process.exit(fail ? 1 : 0);
})();
