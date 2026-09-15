# -*- coding: utf-8 -*-
"""把 parseSec/fmtSec 换成"距离感知 + 合理性择优"的版本，并加 secSuspicion 提醒函数"""
import io, os, sys

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'app.js')
s = io.open(P, encoding='utf-8', newline='').read()
if 'function pickSec(' in s:
    print('已经改过了，跳过'); sys.exit(0)

i0 = s.index('function parseSec(v) {')
i_fmt = s.index('function fmtSec(sec) {', i0)
tail = "  return h >= 1 ? h + ':' + p2(m) + ':' + p2(s) : m + ':' + p2(s);"
i_end = s.index('}', s.index(tail, i_fmt)) + 1
old = s[i0:i_end]
assert 'function fmtSec' in old and old.count('function ') == 2, '切片不对'

NEW = u'''/** 各项目的合理用时范围（秒）—— 用来把「1:24:00 / 1:24」这类写法读对
    （半马的 1:24 = 1 小时 24 分，不是 1 分 24 秒；5000 米的 17:02:00 反而是 17 分 02 秒） */
const SEC_RANGE = [
  [/800\\s*米|0?\\.8\\s*公里/, 70, 900],
  [/1000|1\\s*公里/, 100, 1500],
  [/1500/, 160, 1800],
  [/3000|3\\s*公里/, 420, 3600],
  [/5000|5\\s*公里|5K/i, 620, 5400],
  [/10000|10\\s*公里|10K/i, 1300, 10800],
  [/4\\s*公里|4000/, 500, 5400],
  [/12\\s*公里|12000/, 1400, 10800],
  [/16\\s*公里|16000/, 1900, 14400],
  [/半马|半程|21\\.0975/, 3000, 18000],
  [/全马|全程|42\\.195/, 6600, 32400],
];
function secRange(ev) {
  const s = String(ev == null ? '' : ev);
  for (let i = 0; i < SEC_RANGE.length; i++) if (SEC_RANGE[i][0].test(s)) return [SEC_RANGE[i][1], SEC_RANGE[i][2]];
  return [20, 36000];                    // 不知道项目：只排除明显不合理的值
}

/** 从几个候选读数里挑最合理的：按候选顺序取第一个落在合理范围内的；
    都不在范围内就取离范围最近的（宁可保住数值，也不乱丢） */
function pickSec(cands, ev) {
  const r = secRange(ev);
  const good = (cands || []).filter(c => typeof c === 'number' && isFinite(c) && c > 0);
  if (!good.length) return null;
  for (let i = 0; i < good.length; i++) if (good[i] >= r[0] && good[i] <= r[1]) return good[i];
  const d = c => (c < r[0] ? Math.log(r[0] / c) : Math.log(c / r[1]));
  return good.slice().sort((a, b) => d(a) - d(b))[0];
}

/** 成绩 → 秒。第二个参数是「项目/距离」，给了才能把 1:24:00 这种写法读对（半马 = 1 小时 24 分）
    支持：17:35 / 1:23:29 / 18'35" / 18.5（分钟）/ Excel 时间格式（0.0583 = 1:24:00）/ 直接写秒数 */
function parseSec(v, ev) {
  if (v === null || v === undefined || v === '') return null;
  if (v instanceof Date) {
    if (v.getFullYear() > 1900) return null;
    const h = v.getHours(), m = v.getMinutes(), s = v.getSeconds();
    return pickSec([h * 3600 + m * 60 + s, h * 60 + m + s / 60], ev);   // 真·时:分:秒 / 分钟塞在小时槽
  }
  if (typeof v === 'number') {
    if (v > 0 && v < 1) {
      const t = v * 86400, h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), s = Math.round(t % 60);
      return pickSec([h * 3600 + m * 60 + s, h * 60 + m + s / 60], ev);
    }
    return pickSec([v, v * 60], ev);      // 写秒数 / 写分钟
  }
  let s = String(v).trim()
    .replace(/[\\u2019\\u2018\\u2032]/g, "'").replace(/[\\u201d\\u201c\\u2033]/g, '"').replace(/\\uff1a/g, ':').replace(/\\s/g, '');
  if (!s) return null;
  if (/dns|dnf|缺|误|请假|未参加|无成绩|退赛/i.test(s)) return null;
  s = s.replace(/[\\uff08(][^)\\uff09]*[)\\uff09]/g, '').trim();
  if (s.indexOf("'") >= 0 || s.indexOf('"') >= 0) {
    const p = s.split(/['"]/).filter(x => x !== '').map(Number);
    if (p.some(isNaN)) return null;
    if (p.length === 1) return pickSec([p[0], p[0] * 60], ev);
    if (p.length === 2) return pickSec([p[0] * 60 + p[1], p[0] * 3600 + p[1] * 60], ev);   // 18'35" 传统读作 分'秒"
    return null;
  }
  if (s.indexOf(':') >= 0) {
    const p = s.split(':').filter(x => x !== '').map(Number);
    if (p.some(isNaN)) return null;
    if (p.length === 3) {
      // 两种读法：时:分:秒（半马 1:24:00 = 1 小时 24 分）/ 小时槽其实是分钟（5000 米 17:02:00 = 17 分 02 秒）
      return pickSec([p[0] * 3600 + p[1] * 60 + p[2], p[2] === 0 ? p[0] * 60 + p[1] : null], ev);
    }
    if (p.length === 2) return pickSec([p[0] * 60 + p[1], p[0] * 3600 + p[1] * 60], ev);   // 分:秒（长距离就是 时:分）
    return null;
  }
  const f = parseFloat(s);
  if (isNaN(f) || f <= 0) return null;
  return pickSec([f, f * 60], ev);
}

function fmtSec(sec) {
  if (sec === null || sec === undefined || isNaN(sec)) return '-';
  sec = Math.round(sec * 10) / 10;
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = Math.round(sec % 60);
  const p2 = n => (n < 10 ? '0' + n : '' + n);
''' + tail + u'''
}

/** 这个成绩对该项目来说"不太像"吗？→ 返回一句提醒（没有就返回空串）。只提醒，不改存进去的值 */
function secSuspicion(sec, ev) {
  if (!sec || !ev) return '';
  const r = secRange(ev);
  if (sec >= r[0] && sec <= r[1]) return '';
  return '⚠️ 「' + ev + '」读成 ' + fmtSec(sec) + ' 不太常见，核对一下（想写 1 小时 24 分就写 1:24:00）';
}
'''

io.open(P, 'w', encoding='utf-8', newline='').write(s[:i0] + NEW + s[i_end:])
print('已替换：%d 字符 → %d 字符' % (len(old), len(NEW)))
