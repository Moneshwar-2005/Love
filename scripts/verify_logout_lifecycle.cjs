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
  console.log('=' .repeat(70));
  console.log('  LOVE Mobile Logout & Session Cleanup Verification');
  console.log('=' .repeat(70));

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

  const result = await evaluate(`(async () => {
    const ks = window.Capacitor?.Plugins?.LoveKeystore;
    if (!ks) return { error: 'LoveKeystore plugin unavailable' };

    const baseUrl = 'https://192.168.0.176:8000';

    // 1. Check refresh token exists before logout
    const preItem = await ks.getSecureItem({ key: 'love_sec_vault_refresh_token' });
    const hasPreToken = !!(preItem && preItem.value);

    // 2. Perform server-side revocation
    let serverRevocationStatus = null;
    if (hasPreToken) {
      try {
        const logoutResp = await fetch(baseUrl + '/api/v1/auth/logout', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify({ refresh_token: preItem.value })
        });
        serverRevocationStatus = logoutResp.status;
      } catch (err) {
        serverRevocationStatus = 'error: ' + err.message;
      }
    }

    // 3. Remove refresh token from Keystore
    await ks.removeSecureItem({ key: 'love_sec_vault_refresh_token' });

    // 4. Verify Keystore deletion
    const postItem = await ks.getSecureItem({ key: 'love_sec_vault_refresh_token' });
    const tokenRemoved = !postItem || !postItem.value;

    // 5. Verify unauthenticated protected endpoint rejection
    let unauthMeStatus = null;
    try {
      const meResp = await fetch(baseUrl + '/api/v1/auth/me', {
        headers: { 'Accept': 'application/json' }
      });
      unauthMeStatus = meResp.status;
    } catch (e) {
      unauthMeStatus = 'error: ' + e.message;
    }

    // 6. Verify revoked token rejection on refresh endpoint
    let revokedRefreshStatus = null;
    if (preItem?.value) {
      try {
        const refResp = await fetch(baseUrl + '/api/v1/auth/refresh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify({ refresh_token: preItem.value })
        });
        revokedRefreshStatus = refResp.status;
      } catch (e) {
        revokedRefreshStatus = 'error: ' + e.message;
      }
    }

    // 7. Verify login screen restoration
    const hasSignInButton = Array.from(document.querySelectorAll('button')).some(b => b.innerText.includes('Sign In'));
    const hasUsernameInput = !!document.querySelector('input[type="text"], input[type="email"]');
    const hasPasswordInput = !!document.querySelector('input[type="password"]');

    return {
      preLogoutTokenExisted: hasPreToken,
      serverRevocationStatus,
      tokenRemovedFromKeystore: tokenRemoved,
      unauthenticatedMeStatus: unauthMeStatus,
      revokedRefreshTokenStatus: revokedRefreshStatus,
      loginScreenRestored: {
        hasSignInButton,
        hasUsernameInput,
        hasPasswordInput
      }
    };
  })()`);

  console.log(JSON.stringify(result, null, 2));
  ws.close();
}

run().catch(err => {
  console.error('Logout verification error:', err);
  process.exit(1);
});
