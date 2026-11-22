const http = require('http');

async function getPageWsUrl() {
  return new Promise((resolve, reject) => {
    http.get('http://127.0.0.1:9222/json', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        const targets = JSON.parse(data);
        const page = targets.find(t => t.type === 'page');
        if (page && page.webSocketDebuggerUrl) resolve(page.webSocketDebuggerUrl);
        else reject(new Error('Page target not found'));
      });
    }).on('error', reject);
  });
}

function callCdp(ws, method, params) {
  return new Promise((resolve, reject) => {
    const id = Math.floor(Math.random() * 1000000);
    const timer = setTimeout(() => reject(new Error(`Timeout on ${method}`)), 10000);
    const handler = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id === id) {
        clearTimeout(timer);
        ws.removeEventListener('message', handler);
        if (msg.error) reject(msg.error);
        else resolve(msg.result);
      }
    };
    ws.addEventListener('message', handler);
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function run() {
  const wsUrl = await getPageWsUrl();
  const ws = new WebSocket(wsUrl);
  await new Promise((resolve, reject) => {
    ws.onopen = resolve;
    ws.onerror = reject;
  });

  async function evaluate(expr) {
    const res = await callCdp(ws, 'Runtime.evaluate', {
      expression: expr,
      awaitPromise: true,
      returnByValue: true
    });
    return res.result ? res.result.value : res;
  }

  console.log('=' .repeat(70));
  console.log('  LOVE Authenticated API Verification via In-App Session');
  console.log('=' .repeat(70));

  // Run in-app fetch tests
  const results = await evaluate(`(async () => {
    const endpoints = [
      { path: '/api/v1/auth/me', name: 'Identity (/auth/me)' },
      { path: '/api/v1/intelligence/status', name: 'Intelligence Status (/intelligence/status)' },
      { path: '/api/v1/intelligence/conversations', name: 'Conversations (/intelligence/conversations)' },
      { path: '/api/v1/memory/stats', name: 'Memory Stats (/memory/stats)' },
      { path: '/api/v1/work/tasks', name: 'Work Tasks (/work/tasks)' },
      { path: '/api/v1/devices', name: 'Registered Devices (/devices)' },
      { path: '/api/v1/sync/status', name: 'Sync Status (/sync/status)' },
    ];

    const baseUrl = 'https://192.168.0.176:8000';
    // Get in-memory access token via mobileApiClient if available, or direct headers
    const reports = [];

    for (const ep of endpoints) {
      try {
        const fullUrl = baseUrl + ep.path;
        // Check if mobileApiClient exists on window or import
        let res;
        if (window.__LOVE_API_CLIENT__) {
          res = await window.__LOVE_API_CLIENT__.get(ep.path);
          reports.push({ endpoint: ep.path, name: ep.name, status: 200, success: true, data: res });
        } else {
          // fetch using credential cookies or authorization
          const resp = await fetch(fullUrl, {
            headers: { 'Accept': 'application/json' },
            credentials: 'include'
          });
          let json = null;
          try { json = await resp.json(); } catch(e) {}
          reports.push({
            endpoint: ep.path,
            name: ep.name,
            status: resp.status,
            success: resp.ok,
            data: json
          });
        }
      } catch (err) {
        reports.push({ endpoint: ep.path, name: ep.name, status: 0, success: false, error: err.message || String(err) });
      }
    }
    return reports;
  })()`);

  console.log(JSON.stringify(results, null, 2));
  ws.close();
}

run().catch(err => {
  console.error('API Verification error:', err);
  process.exit(1);
});
