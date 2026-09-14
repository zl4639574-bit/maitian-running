# -*- coding: utf-8 -*-
"""让「上传成绩 → 导入/录入」一键发布并同步到线上（修掉那段没人能猜到的中间步骤）"""
import io

p = "assets/app.js"
s = io.open(p, encoding="utf-8", newline="").read().replace("\r\n", "\n")
orig = len(s)

# ── ① 上传页：把误导读者的提示换掉，并加「发布并同步」按钮 ───────────────────
old1 = """    <div class="notice" style="margin-top:16px">
      ${batch ? '导入的成绩先存在本机。要让全队都看到，去 <b>数据管理 → 同步</b> 发布到线上。'
              : '这里的成绩只保存在<b>你这台设备的浏览器</b>里，别人看不到自己手机上的这一份。'}
    </div>
  </div>"""
new1 = """    ${batch && L.length ? `
    <div class="notice" style="margin-top:16px;border-color:var(--wheat)">
      <b>本机有 ${L.length} 条成绩还没上线。</b><br>
      点下面的按钮就发布 + 同步到线上（约 1 分钟），全队立刻能看到。<br>
      想做成「某场比赛一张榜」，也可以去 <b>数据管理 → 比赛成绩</b> 把它们并进那场比赛。
    </div>
    <div class="chips" style="margin-top:12px">
      <button class="btn" id="btnPublishSync">发布并同步到线上（${L.length} 条）</button>
      <button class="btn ghost" data-go="manage" data-msec="comp">改成并进某场比赛 →</button>
    </div>` : ''}

    <div class="notice" style="margin-top:16px">
      ${batch ? '成绩先存在<b>本机</b>；点上面的「发布并同步到线上」，全队才能看到。'
              : '这里的成绩只保存在<b>你这台设备的浏览器</b>里，别人看不到自己手机上的这一份。'}
    </div>
  </div>"""
assert s.count(old1) == 1, "① 锚点未命中"
s = s.replace(old1, new1)

# ── ② 同步面板：没有待同步但有本机录入时，直接给一键按钮 ─────────────────────
old2 = """      <br>你的修改会提交到这个仓库，GitHub Pages 会自动重新发布（约 1 分钟）。
    </div>"""
new2 = """      <br>你的修改会提交到这个仓库，GitHub Pages 会自动重新发布（约 1 分钟）。
    </div>
    ${(!pend && myResults().length) ? `
    <div class="notice" style="border-color:var(--wheat);margin-top:12px;line-height:2">
      ⚠️ 你还有 <b>${myResults().length}</b> 条在「上传成绩」里导入/录入的成绩，只是存在本机、<b>还没发布</b>，
      所以同步按钮是灰的。<br>
      <button class="btn sm" id="btnPubSync2" style="margin-top:8px">发布这 ${myResults().length} 条并同步到线上</button>
    </div>` : ''}"""
assert s.count(old2) == 1, "② 锚点未命中"
s = s.replace(old2, new2)

# ── ③ 抽出「发布」逻辑 + 新增「发布并同步」 ─────────────────────────────────
old3 = """  const pm = $('#btnPublishMine');
  if (pm) pm.onclick = () => {
    const mine = myResults();
    if (!mine.length) return toast('还没有录入的成绩');
    const l = ovLocal();
    l.results = (l.results || []).concat(mine.map(r => Object.assign({}, r, { local: false, published: true })));
    saveLocalOv();
    setMyResults([]);
    toast('已把 ' + mine.length + ' 条成绩发布（记得同步到线上）', 4000);
    render();
  };"""
new3 = """  const pm = $('#btnPublishMine');
  if (pm) pm.onclick = publishAndSync;          // 自由成绩区：发布 + 同步一步到位
  const p2 = $('#btnPubSync2');
  if (p2) p2.onclick = publishAndSync;          // 同步分区：本机有没发布的成绩时出现
  const p3 = $('#btnPublishSync');
  if (p3) p3.onclick = publishAndSync;          // 上传成绩页：导入完就能看到的大按钮"""
assert s.count(old3) == 1, "③ 锚点未命中"
s = s.replace(old3, new3)

# ── ④ 插入 publishMine / publishAndSync 两个函数（放在 ovLocal 之后）────────
anchor = """function ovLocal() { return LOCAL_OV || (LOCAL_OV = {}); }"""
assert s.count(anchor) == 1, "④ 锚点未命中"
s = s.replace(anchor, anchor + """

/** 把「上传成绩」里录入/导入的成绩，转成「待同步到线上」的正式成绩（清空本机草稿） */
function publishMine() {
  const mine = myResults();
  if (!mine.length) return 0;
  const l = ovLocal();
  l.results = (l.results || []).concat(mine.map(r => Object.assign({}, r, { local: false, published: true })));
  saveLocalOv();
  setMyResults([]);
  return mine.length;
}

/** 一键：发布本机录入的成绩 → 直接同步到线上（没配令牌则只发布，并提示去配） */
async function publishAndSync() {
  const n = publishMine();
  render();
  if (!n) return toast('本机没有新录入的成绩');
  const cfg = ghCfg();
  if (!cfg.token) return toast('已把 ' + n + ' 条标成待上线，但还没配「访问令牌」→ 数据管理 → 同步 里填一次即可', 10000);
  toast('已发布 ' + n + ' 条，正在同步到线上…（约 1 分钟）', 6000);
  await pushToGitHub();
}""")

# ── ⑤ 导入完成后不要跳走，留在上传页看到那个按钮 ─────────────────────────────
old5 = """  toast('导入 ' + out.length + ' 条' + (bad ? '，跳过 ' + bad + ' 条成绩认不出的' : '')
        + (noName ? '，跳过 ' + noName + ' 条没姓名的' : ''), 4000);
  state.tab = 'board';
  render();"""
new5 = """  toast('已导入 ' + out.length + ' 条' + (bad ? '，跳过 ' + bad + ' 条成绩认不出的' : '')
        + (noName ? '，跳过 ' + noName + ' 条没姓名的' : '')
        + (MODE === 'captain' ? '；点下面「发布并同步到线上」全队才能看到' : ''), 7000);
  state.tab = MODE === 'captain' ? 'upload' : 'board';   // 队长留在本页，才能看到发布按钮
  render();"""
assert s.count(old5) == 1, "⑤ 锚点未命中"
s = s.replace(old5, new5)

# ── ⑥ 同步按钮灰着时，提示真正原因 ─────────────────────────────────────────
old6 = """  if (!pendingCount()) return toast('没有需要同步的修改');"""
new6 = """  if (!pendingCount()) {
    const mine = myResults().length;
    return toast(mine ? ('本机没有待同步的改动 —— 但「上传成绩」里有 ' + mine + ' 条还没发布，先去那页点「发布并同步到线上」')
                      : '没有需要同步的修改', 9000);
  }"""
assert s.count(old6) == 1, "⑥ 锚点未命中"
s = s.replace(old6, new6)

io.open(p, "w", encoding="utf-8", newline="\r\n").write(s)
print("app.js 补丁完成: %d -> %d 字符" % (orig, len(s)))
