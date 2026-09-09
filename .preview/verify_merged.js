/* 验证 apps/web/map/index.html（中小学合并地图）+ support.html + index.html 入口 */
const { spawn } = require('child_process');
const fs = require('fs');
const http = require('http');
const path = require('path');

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const ROOT = 'http://127.0.0.1:8734';
const MAP_URL = ROOT + '/apps/web/map/index.html';
const SUPPORT_URL = ROOT + '/apps/web/support.html';
const INDEX_URL = ROOT + '/apps/web/index.html';
const PORT = 9224;
const OUT_DIR = '/Users/bytedance/Developer/gz_school_research/.preview/verify_merged';
fs.mkdirSync(OUT_DIR, { recursive: true });

const chrome = spawn(CHROME, [
  '--headless', '--disable-gpu', '--no-sandbox',
  `--remote-debugging-port=${PORT}`,
  '--window-size=1440,900',
  '--user-data-dir=/tmp/chrome-cdp-merged',
  MAP_URL
], { stdio: 'ignore' });

function getJson(p) {
  return new Promise((res, rej) => {
    http.get(`http://127.0.0.1:${PORT}${p}`, r => {
      let d = ''; r.on('data', c => d += c); r.on('end', () => res(JSON.parse(d)));
    }).on('error', rej);
  });
}

(async () => {
  let target = null;
  for (let i = 0; i < 40; i++) {
    try {
      const list = await getJson('/json');
      const t = list.find(x => x.type === 'page' && x.url.includes('map/index.html'));
      if (t) { target = t; break; }
    } catch (e) {}
    await new Promise(r => setTimeout(r, 500));
  }
  if (!target) throw new Error('no page target');

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0; const pending = {};
  const localStatus = {};
  const failed = [];
  ws.onmessage = ev => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending[msg.id]) { pending[msg.id](msg.result); delete pending[msg.id]; }
    if (msg.method === 'Network.responseReceived' && msg.params && msg.params.response) {
      const u = msg.params.response.url;
      if (u.startsWith(ROOT)) {
        const s = msg.params.response.status;
        if (!(s >= 200 && s < 300)) failed.push({ url: u, status: s });
        localStatus[u] = s;
      }
    }
  };
  const send = (method, params = {}) => new Promise(res => {
    const mid = ++id; pending[mid] = res;
    ws.send(JSON.stringify({ id: mid, method, params }));
  });
  const evalJs = async expr => {
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    if (r && r.exceptionDetails) throw new Error('EVAL: ' + JSON.stringify(r.exceptionDetails).slice(0, 500));
    return r.result ? r.result.value : undefined;
  };
  const shot = async name => {
    const r = await send('Page.captureScreenshot', { format: 'png' });
    const f = path.join(OUT_DIR, name);
    fs.writeFileSync(f, Buffer.from(r.data, 'base64'));
    console.log('SHOT ' + f);
  };

  await send('Runtime.enable');
  await send('Page.enable');
  await send('Network.enable');
  await new Promise(r => setTimeout(r, 9000)); // 等待地图与瓦片加载

  /* ---------- 1. 基础渲染：4 类颜色 + 总量 ---------- */
  const base = await evalJs(`(() => {
    const els = [...document.querySelectorAll('.leaflet-interactive')];
    const cnt = c => els.filter(p => (p.getAttribute('fill')||'').toUpperCase() === c).length;
    const glowCnt = c => [...document.querySelectorAll('path')].filter(p =>
      (p.getAttribute('stroke')||'').toLowerCase().replace(/\\s/g,'') === c && !p.classList.contains('leaflet-interactive')).length;
    return JSON.stringify({
      pN: cnt('#94A3B8'), pT: cnt('#2563EB'), mN: cnt('#A8A29E'), mT: cnt('#DC2626'),
      total: els.length,
      glowP: glowCnt('rgba(37,99,235,0.35)'),
      glowM: glowCnt('rgba(220,38,38,0.35)'),
      status: (document.getElementById('status-text')||{}).textContent || '',
      legend: (document.getElementById('legend-rows').textContent||'').replace(/\\s+/g,' ').trim(),
      legendSum: (document.getElementById('legend-sum').textContent||'').replace(/\\s+/g,' ').trim(),
      title: document.title
    });
  })()`);
  console.log('BASE ' + base);
  const b = JSON.parse(base);
  const check = (cond, name) => { console.log((cond ? 'PASS' : 'FAIL') + ' ' + name); if (!cond) process.exitCode = 1; };
  check(b.total === 1228, 'total markers = 1228 (got ' + b.total + ')');
  check(b.pN === 798, 'primary normal #94A3B8 = 798 (got ' + b.pN + ')');
  check(b.pT === 120, 'primary tier #2563EB = 120 (got ' + b.pT + ')');
  check(b.mN === 190, 'middle normal #A8A29E = 190 (got ' + b.mN + ')');
  check(b.mT === 120, 'middle tier #DC2626 = 120 (got ' + b.mT + ')');
  check(b.glowP === 50, 'primary glow (有支撑) = 50 (got ' + b.glowP + ')');
  check(b.glowM === 90, 'middle glow (有支撑) = 90 (got ' + b.glowM + ')');
  check(b.title.includes('中小学'), 'page title 中小学');
  check(b.legend.includes('小学普通') && b.legend.includes('小学第一梯队') && b.legend.includes('初中普通') && b.legend.includes('初中第一梯队'), 'legend 4 classes');
  check(!b.legend.includes('支撑度') && !b.legend.includes('说明页'), 'legend has NO support link');
  check(b.legendSum.includes('1228'), 'legend sum 1228 (got ' + b.legendSum + ')');
  await shot('map.png');

  /* ---------- 2. 筛选 checkbox 实时生效 + 全选/全不选 ---------- */
  const f1 = await evalJs(`(() => {
    document.getElementById('f-m-tier').click(); // 取消初中第一梯队
    return JSON.stringify({
      mT: [...document.querySelectorAll('.leaflet-interactive')].filter(p => (p.getAttribute('fill')||'').toUpperCase() === '#DC2626').length,
      total: document.querySelectorAll('.leaflet-interactive').length,
      sum: (document.getElementById('legend-sum').textContent||'').replace(/\\s+/g,' ')
    });
  })()`);
  console.log('FILTER1 ' + f1);
  const fb1 = JSON.parse(f1);
  check(fb1.mT === 0 && fb1.total === 1108, 'uncheck 初中梯队 -> mT=0 total=1108 (got ' + fb1.total + ')');
  check(fb1.sum.includes('1108'), 'legend sum updates to 1108');

  const f2 = await evalJs(`(() => {
    document.getElementById('f-none').click();
    return document.querySelectorAll('.leaflet-interactive').length;
  })()`);
  console.log('FILTER2 none -> ' + f2);
  check(f2 === 0, '全不选 -> 0 markers (got ' + f2 + ')');

  const f3 = await evalJs(`(() => {
    document.getElementById('f-all').click();
    return JSON.stringify({
      total: document.querySelectorAll('.leaflet-interactive').length,
      pT: [...document.querySelectorAll('.leaflet-interactive')].filter(p => (p.getAttribute('fill')||'').toUpperCase() === '#2563EB').length
    });
  })()`);
  console.log('FILTER3 all -> ' + f3);
  const fb3 = JSON.parse(f3);
  check(fb3.total === 1228 && fb3.pT === 120, '全选 -> 1228 restored (got ' + fb3.total + ')');

  const f4 = await evalJs(`(() => {
    document.getElementById('f-p-normal').click(); // 取消小学普通
    return JSON.stringify({
      pN: [...document.querySelectorAll('.leaflet-interactive')].filter(p => (p.getAttribute('fill')||'').toUpperCase() === '#94A3B8').length,
      total: document.querySelectorAll('.leaflet-interactive').length,
      sum: (document.getElementById('legend-sum').textContent||'').replace(/\\s+/g,' ')
    });
  })()`);
  console.log('FILTER4 ' + f4);
  const fb4 = JSON.parse(f4);
  check(fb4.pN === 0 && fb4.total === 430, 'uncheck 小学普通 -> pN=0 total=430 (got ' + fb4.total + ')');
  // 恢复全选
  await evalJs(`document.getElementById('f-all').click(); 0;`);

  /* ---------- 3. 点击小学梯队点位：招生数据 + 梯队信号 + 链接 ../support.html ---------- */
  const clickP = await evalJs(`(() => {
    const els = [...document.querySelectorAll('.leaflet-interactive')].filter(p => (p.getAttribute('fill')||'').toUpperCase() === '#2563EB');
    for (const el of els) {
      el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
      const txt = (document.getElementById('si-body').textContent || '').replace(/\\s+/g,' ');
      if (txt.includes('学区') || txt.includes('计划班数')) {
        return JSON.stringify({
          found: true,
          name: (document.querySelector('.si-name')||{}).textContent || '',
          text: txt.slice(0, 500),
          link: (document.querySelector('.si-tier-link a')||{}).getAttribute('href') || ''
        });
      }
    }
    return JSON.stringify({ found: false });
  })()`);
  console.log('CLICK_P ' + clickP);
  const cp = JSON.parse(clickP);
  check(cp.found === true, 'primary tier card shows enrollment data');
  check(cp.found && /有支撑|部分支撑/.test(cp.text), 'primary tier card shows tier badge');
  check(cp.found && /出口机制|教育集团|2026班数|学位预警|省一级/.test(cp.text), 'primary tier card shows tier signals');
  check(cp.found && cp.link === '../support.html', 'primary card support link = ../support.html (got ' + (cp.found ? cp.link : 'n/a') + ')');
  await shot('card_primary.png');

  /* ---------- 4. 点击初中梯队点位：中考信号 + 梯队徽标 + 链接 ---------- */
  const clickM = await evalJs(`(() => {
    const els = [...document.querySelectorAll('.leaflet-interactive')].filter(p => (p.getAttribute('fill')||'').toUpperCase() === '#DC2626');
    if (!els.length) return JSON.stringify({ found: false });
    els[0].dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
    return JSON.stringify({
      found: true,
      name: (document.querySelector('.si-name')||{}).textContent || '',
      text: (document.getElementById('si-body').textContent || '').replace(/\\s+/g,' ').slice(0, 500),
      link: (document.querySelector('.si-tier-link a')||{}).getAttribute('href') || '',
      badge: (document.querySelector('.si-tier .badge')||{}).textContent || ''
    });
  })()`);
  console.log('CLICK_M ' + clickM);
  const cm = JSON.parse(clickM);
  check(cm.found === true, 'middle tier marker found & clicked');
  check(/有支撑|部分支撑/.test(cm.badge || ''), 'middle card badge 有支撑/部分支撑 (got ' + cm.badge + ')');
  check(/中考成绩|示范性高中|教育集团|建校年份|指标到校/.test(cm.text), 'middle card shows 中考 signals');
  check(cm.link === '../support.html', 'middle card support link = ../support.html (got ' + cm.link + ')');
  await shot('card_middle.png');

  /* ---------- 5. 点击普通点位：学段提示 + 区名 ---------- */
  const clickN = await evalJs(`(() => {
    const el = [...document.querySelectorAll('.leaflet-interactive')].find(p => (p.getAttribute('fill')||'').toUpperCase() === '#94A3B8');
    if (!el) return JSON.stringify({ found: false });
    el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
    const t = (document.getElementById('si-body').textContent || '').replace(/\\s+/g,' ');
    const a = document.querySelector('.si-tier-link a');
    return JSON.stringify({ found: true, text: t.slice(0, 300), link: a ? a.getAttribute('href') : '' });
  })()`);
  console.log('CLICK_N ' + clickN);
  const cn = JSON.parse(clickN);
  check(cn.found && cn.text.includes('小学') && cn.text.includes('所在区'), 'normal primary card shows 学段+区名');
  check(cn.found && cn.link === '', 'normal card has NO support link');

  /* ---------- 6. 资源 200 检查（本地资源无 404） ---------- */
  await new Promise(r => setTimeout(r, 1000));
  console.log('LOCAL_REQ ' + Object.keys(localStatus).length + ' failed: ' + JSON.stringify(failed));
  check(failed.length === 0, 'no failed local resources (got ' + failed.length + ')');

  /* ---------- 7. support.html：初中表格 + 标题 ---------- */
  await send('Page.navigate', { url: SUPPORT_URL });
  await new Promise(r => setTimeout(r, 4000));
  const sup = await evalJs(`JSON.stringify({
    title: document.title,
    mFull: document.querySelectorAll('#tbl-m-full tr').length,
    mPart: document.querySelectorAll('#tbl-m-part tr').length,
    pFull: document.querySelectorAll('#tbl-full tr').length,
    pPart: document.querySelectorAll('#tbl-part tr').length,
    hasRules: (document.body.textContent||'').includes('中考成绩') && (document.body.textContent||'').includes('指标到校'),
    nav: (document.querySelector('.nav a')||{}).textContent || ''
  })`);
  console.log('SUPPORT ' + sup);
  const sp = JSON.parse(sup);
  check(sp.title.includes('小学+初中'), 'support title 小学+初中 (got ' + sp.title + ')');
  check(sp.mFull === 41, 'support middle 有支撑 table = 41 rows (got ' + sp.mFull + ')');
  check(sp.mPart === 12, 'support middle 部分支撑 table = 12 rows (got ' + sp.mPart + ')');
  check(sp.pFull === 21 && sp.pPart === 36, 'support primary tables 21/36 preserved (got ' + sp.pFull + '/' + sp.pPart + ')');
  check(sp.hasRules === true, 'support has 中考成绩/指标到校 signal sections');
  await shot('support.png');

  /* ---------- 8. 入口页：单一地图入口 ---------- */
  await send('Page.navigate', { url: INDEX_URL });
  await new Promise(r => setTimeout(r, 2500));
  const idx = await evalJs(`JSON.stringify({
    mapLinks: [...document.querySelectorAll('a[href="map/index.html"]')].length,
    middleLinks: [...document.querySelectorAll('a[href*="map-middle"]')].length,
    supportLinks: [...document.querySelectorAll('a[href="support.html"]')].length,
    bodyText: (document.body.textContent||'').replace(/\\s+/g,' ').slice(0, 300)
  })`);
  console.log('INDEX ' + idx);
  const ix = JSON.parse(idx);
  check(ix.mapLinks === 1, 'index has exactly 1 map entry (got ' + ix.mapLinks + ')');
  check(ix.middleLinks === 0, 'index has NO map-middle entry');
  check(ix.supportLinks === 1, 'index keeps support entry');
  await shot('index.png');

  console.log('DONE');
  chrome.kill();
  process.exit(process.exitCode || 0);
})().catch(e => { console.error('ERR ' + (e && e.message || e)); chrome.kill(); process.exit(1); });
