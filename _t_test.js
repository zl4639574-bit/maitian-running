
(async function () {
  var out = [];
  goTab('manage', {msec:'sync'});
  await new Promise(r => setTimeout(r, 600));
  var b = document.getElementById('btnTest');
  out.push('测试按钮=' + (b ? '在' : '缺'));
  if (b) {
    b.click();
    for (var i = 0; i < 80; i++) {
      await new Promise(r => setTimeout(r, 1000));
      var t = (document.getElementById('toast')||{}).textContent || '';
      if (t.indexOf('测试通过')>=0 || t.indexOf('测试失败')>=0 || t.indexOf('写入成功')>=0) break;
    }
    out.push('结果=' + ((document.getElementById('toast')||{}).textContent));
    out.push('按钮恢复=' + document.getElementById('btnTest').textContent);
  }
  return out.join(' | ');
})()
