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
    const timer = setTimeout(() => reject(new Error(`Timeout on ${method}`)), 12000);
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

  const auditResult = await evaluate(`(async () => {
    const baseUrl = 'https://192.168.0.176:8000';
    const ks = window.Capacitor?.Plugins?.LoveKeystore;
    if (!ks) return { error: 'LoveKeystore plugin unavailable' };

    // 1. Retrieve refresh token from Keystore
    const ksItem = await ks.getSecureItem({ key: 'love_sec_vault_refresh_token' });
    if (!ksItem || !ksItem.value) return { error: 'No refresh token in keystore' };

    // 2. Refresh session to verify token validity & rotation
    const refreshResp = await fetch(baseUrl + '/api/v1/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({ refresh_token: ksItem.value })
    });

    if (!refreshResp.ok) {
      return {
        error: 'Refresh request failed',
        status: refreshResp.status,
        text: await refreshResp.text()
      };
    }

    const refreshData = await refreshResp.json();
    const accessToken = refreshData.access_token;
    const newRefreshToken = refreshData.refresh_token;

    // Persist rotated refresh token back to Keystore
    if (newRefreshToken) {
      await ks.setSecureItem({
        key: 'love_sec_vault_refresh_token',
        value: newRefreshToken
      });
    }

    // 3. Query all required endpoints
    const authHeaders = {
      'Authorization': 'Bearer ' + accessToken,
      'Accept': 'application/json'
    };

    const fetchJson = async (path) => {
      try {
        const r = await fetch(baseUrl + path, { headers: authHeaders });
        const data = await r.json();
        return { status: r.status, ok: r.ok, data };
      } catch (e) {
        return { status: 0, ok: false, error: e.message };
      }
    };

    const me = await fetchJson('/api/v1/auth/me');
    const intel = await fetchJson('/api/v1/intelligence/status');
    const convos = await fetchJson('/api/v1/intelligence/conversations');
    const mem = await fetchJson('/api/v1/memory/stats');
    const work = await fetchJson('/api/v1/work/tasks');
    const devices = await fetchJson('/api/v1/devices');
    const sync = await fetchJson('/api/v1/sync/status');

    return {
      tokenRotated: !!newRefreshToken,
      identity: {
        status: me.status,
        username: me.data?.username,
        email: me.data?.email,
        is_owner: me.data?.is_owner,
        is_active: me.data?.is_active,
        is_verified: me.data?.is_verified,
        created_at: me.data?.created_at
      },
      intelligence: {
        status: intel.status,
        ok: intel.ok,
        data: intel.data
      },
      conversations: {
        status: convos.status,
        count: Array.isArray(convos.data) ? convos.data.length : convos.data?.total || 0
      },
      memory: {
        status: mem.status,
        stats: mem.data
      },
      work: {
        status: work.status,
        count: Array.isArray(work.data) ? work.data.length : work.data?.total || 0
      },
      devices: {
        status: devices.status,
        total: devices.data?.total || (Array.isArray(devices.data?.devices) ? devices.data.devices.length : 0),
        devices: (devices.data?.devices || []).map(d => ({
          device_identifier: d.device_identifier ? d.device_identifier.slice(0, 16) + '...' : null,
          device_name: d.device_name,
          device_type: d.device_type,
          is_trusted: d.is_trusted,
          last_seen_at: d.last_seen_at
        }))
      },
      sync: {
        status: sync.status,
        data: sync.data
      }
    };
  })()`);

  console.log(JSON.stringify(auditResult, null, 2));
  ws.close();
}

run().catch(err => {
  console.error('Session verification error:', err);
  process.exit(1);
});
