# -*- coding: utf-8 -*-
"""新增「令牌体检」：只看不改，直接判定令牌能不能写这个仓库，并给出精确的中文修复建议"""
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


# ① 同步面板里加按钮 + 结果区
rep("""      <button class="btn ghost" id="btnTest">测试同步（不改数据）</button>""",
    """      <button class="btn ghost" id="btnTest">测试同步（会写一次测试标记）</button>
      <button class="btn ghost" id="btnTokenCheck">检查令牌权限（只看不改）</button>""",
    '①a 加「检查令牌权限」按钮')

rep("""  const bTest = $('#btnTest');
  if (bTest) bTest.onclick = testSync;""",
    """  const bTest = $('#btnTest');
  if (bTest) bTest.onclick = testSync;

  const bChk = $('#btnTokenCheck');
  if (bChk) bChk.onclick = checkToken;""",
    '①b 绑定点击')

# ② 体检函数
rep("""async function testSync() {""",
    """/** 令牌体检：只用 GET，不写任何数据。判据 = 仓库接口返回的 permissions.push */
async function checkToken() {
  const cfg = ghCfg();
  const box = $('#tokenCheckBox') || (function () {
    const c = $('#tokenCheck') || (function () {
      const d = document.createElement('div'); d.id = 'tokenCheck';
      const b = $('#btnTokenCheck'); if (b && b.parentNode) b.parentNode.parentNode.appendChild(d);
      return d;
    })();
    const d2 = document.createElement('div'); d2.id = 'tokenCheckBox'; c.appendChild(d2);
    return d2;
  })();
  if (!box) return;
  if (!cfg.token) {
    box.innerHTML = '<div class="notice" style="margin-top:12px">还没填令牌。先在下面「访问令牌」里粘一个 → 点「保存设置」→ 再点这里检查。</div>';
    return;
  }
  const btn = $('#btnTokenCheck');
  if (btn) { btn.disabled = true; btn.textContent = '检查中…'; }
  const lines = [];
  const add = (ok, t) => lines.push((ok === null ? '· ' : (ok ? '✅ ' : '❌ ')) + t);
  const mask = cfg.token.slice(0, 11) + '…' + cfg.token.slice(-4);
  add(null, '仓库 ' + cfg.owner + '/' + cfg.repo + '　分支 ' + (cfg.branch || 'master') + '　令牌 ' + mask);
  let who = null, push = null, repoOk = false;
  try {
    const r1 = await fetch(GH + '/user', { headers: ghHeaders(cfg), cache: 'no-store' });
    if (r1.ok) {
      const j1 = await r1.json();
      who = j1.login;
      add(true, '令牌属于账号：' + j1.login + '（' + (j1.type || 'User') + '）');
    } else {
      add(false, '令牌本身有问题：HTTP ' + r1.status + ghHint(r1.status) + '｜GitHub 原话：' + (await safeMsg(r1)));
    }
  } catch (e) { add(false, '网络不通（先看系统代理开关）：' + (e && e.message)); }

  try {
    const r2 = await fetch(GH + '/repos/' + cfg.owner + '/' + cfg.repo, { headers: ghHeaders(cfg), cache: 'no-store' });
    const need = r2.headers.get('x-accepted-github-permissions');
    const scope = r2.headers.get('x-accepted-oauth-scopes');
    if (r2.ok) {
      const j2 = await r2.json();
      const p = j2.permissions || {};
      push = !!p.push; repoOk = true;
      add(true, '能读到仓库：' + j2.full_name + '　这个令牌的权限：' + (p.pull ? '可读 ' : '不可读 ') + (p.push ? '可写' : '（不能写）'));
      if (push) {
        add(true, '结论：令牌可以写 ✅ 直接点「同步我的修改到线上」即可。');
        if (j2.private === false) add(null, '提示：这是公开仓库，任何人对网页都是只读的，写权限只属于有令牌的人。');
      } else {
        add(false, '结论：令牌能读到仓库，但没有写入权限 → 这就是 403「Resource not accessible by permission token」的原因。');
        add(null, '要改两处（改完必须重新生成令牌，旧令牌不会自动升级）：');
        add(null, '① 令牌页面 → Repository access → 选 Only select repositories → 勾上 ' + cfg.owner + '/' + cfg.repo);
        add(null, '② 同一页面 → Permissions → Repository permissions → 找到 Contents → 选 Read and write');
        if (who && who !== cfg.owner) add(null, '③ 这个令牌属于「' + who + '」，不是仓库主人 → 还要让仓库主人在 Settings → Collaborators 里把你加为协作者');
      }
    } else {
      add(false, '读不到仓库：HTTP ' + r2.status + ghHint(r2.status) + '｜GitHub 原话：' + (await safeMsg(r2)));
      if (need) add(null, 'GitHub 说需要这个权限：' + need);
      if (scope) add(null, '经典令牌需要勾的 scope：' + scope);
      add(null, '常见原因：① 令牌的 Repository access 里没勾这个仓库　② 令牌账号还不是仓库协作者　③ 用户名/仓库名写错了');
      if (r2.status === 404 && who) add(null, '你现在用的是「' + who + '」的令牌，仓库主人是「' + cfg.owner + '」' + (who === cfg.owner ? '' : '：先去加协作者，再重新生成令牌'));
    }
  } catch (e) { add(false, '网络不通：' + (e && e.message)); }

  if (btn) { btn.disabled = false; btn.textContent = '检查令牌权限（只看不改）'; }
  box.innerHTML = '<div class="notice" style="margin-top:12px;border-color:var(--wheat)">'
    + lines.map(t => esc(t)).join('<br>') + '</div>';
}

/** 读 GitHub 报错的原始 message（如 Resource not accessible by permission token） */
async function safeMsg(r) {
  try {
    const t = await r.text();
    const m = t.match(/"message"\\s*:\\s*"([^"]+)"/);
    return m ? m[1] : (t || '').slice(0, 80);
  } catch (e) { return ''; }
}

async function testSync() {""",
    '② 体检函数 checkToken + safeMsg')

io.open(P, 'wb').write(s.replace('\n', '\r\n').encode('utf-8'))
print('\n'.join('   ' + d for d in done))
