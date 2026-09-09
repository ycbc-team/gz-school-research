/* 验证 apps/web/map-middle/index.html：检查渲染状态 + 点击有支撑点位后信息卡内容 */
const { spawn } = require('child_process');
const fs = require('fs');
const http = require('http');

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const URL = 'http://localhost:8734/apps/web/map-middle/index.html';
const PORT = 9223;
const OUT_PNG = '/Users/bytedance/Developer/gz_school_research/.preview/map_middle/card.png';

const chrome = spawn(CHROME, [
  '--headless', '--disable-gpu', '--no-sandbox',
  `--remote-debugging-port=${PORT}`,
  '--window-size=1440,900',
  '--user-data-dir=/tmp/chrome-cdp-map',
  URL
], { stdio: 'ignore' });

function getJson(path) {
  return new Promise((res, rej) => {
    http.get(`http://127.0.0.1:${PORT}${path}`, r => {
      let d = ''; r.on('data', c => d += c); r.on('end', () => res(JSON.parse(d)));
    }).on('error', rej);
  });
}

(async () => {
  let target = null;
  for (let i = 0; i < 40; i++) {
    try {
      const list = await getJson('/json');
      const t = list.find(x => x.type === 'page' && x.url.includes('map-middle'));
      if (t) { target = t; break; }
    } catch (e) {}
    await new Promise(r => setTimeout(r, 500));
  }
  if (!target) throw new Error('no page target');

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0; const pending = {};
  ws.onmessage = ev => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending[msg.id]) { pending[msg.id](msg.result); delete pending[msg.id]; }
  };
  const send = (method, params = {}) => new Promise(res => {
    const mid = ++id; pending[mid] = res;
    ws.send(JSON.stringify({ id: mid, method, params }));
  });
  const evalJs = async expr => {
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
    if (r && r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result ? r.result.value : undefined;
  };

  await send('Runtime.enable');
  await send('Page.enable');
  await new Promise(r => setTimeout(r, 7000)); // 等待地图与瓦片加载

  const state = await evalJs(`JSON.stringify({
    markers: document.querySelectorAll('.leaflet-interactive').length,
    status: (document.getElementById('status-text')||{}).textContent || '',
    tierSchools: (window.GZ_MIDDLE_TIER1||{}).schools ? window.GZ_MIDDLE_TIER1.schools.length : -1,
    poiSchools: (window.GZ_MIDDLE_SCHOOLS||{}).schools ? window.GZ_MIDDLE_SCHOOLS.schools.length : -1,
    redPaths: [...document.querySelectorAll('.leaflet-interactive')].filter(p => (p.getAttribute('fill')||'').toUpperCase() === '#E11D48').length,
    amberPaths: [...document.querySelectorAll('.leaflet-interactive')].filter(p => (p.getAttribute('fill')||'').toUpperCase() === '#F59E0B').length
  })`);
  console.log('STATE ' + state);

  const clicked = await evalJs(`(() => {
    const els = [...document.querySelectorAll('.leaflet-interactive')];
    const tier = els.find(p => (p.getAttribute('fill')||'').toUpperCase() === '#E11D48');
    if (!tier) return 'no red marker';
    tier.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
    return 'clicked red marker';
  })()`);
  console.log('CLICK ' + clicked);
  await new Promise(r => setTimeout(r, 600));

  const card = await evalJs(`(() => {
    const el = document.getElementById('school-info');
    return JSON.stringify({
      hidden: el.hidden,
      text: (document.getElementById('si-body').textContent || '').replace(/\\s+/g, ' ').slice(0, 400)
    });
  })()`);
  console.log('CARD ' + card);

  const shot = await send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(OUT_PNG, Buffer.from(shot.data, 'base64'));
  console.log('SHOT ' + OUT_PNG);
  chrome.kill();
  process.exit(0);
})().catch(e => { console.error('ERR ' + (e && e.message || e)); chrome.kill(); process.exit(1); });
