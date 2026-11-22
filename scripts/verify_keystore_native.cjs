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
    const handler = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id === id) {
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
    console.log('RAW EVAL for [' + expr.slice(0, 40) + '...]:', JSON.stringify(res));
    if (res?.exceptionDetails) {
      console.error('EXCEPTION DETAILS:', JSON.stringify(res.exceptionDetails));
    }
    return res?.result?.value;
  }

  console.log('--- Starting Keystore Native Verification ---');

  // 1. isHardwareBacked
  const hw = await evaluate('window.Capacitor.Plugins.LoveKeystore.isHardwareBacked()');
  console.log('1. isHardwareBacked:', JSON.stringify(hw));

  // 2. setSecureItem with synthetic test value
  const setRes = await evaluate(`window.Capacitor.Plugins.LoveKeystore.setSecureItem({
    key: "synthetic_keystore_test_key",
    value: "LOVE_SYNTHETIC_CIPHERTEXT_PROBE_778899"
  })`);
  console.log('2. setSecureItem:', JSON.stringify(setRes));

  // 3. getSecureItem
  const getRes = await evaluate(`window.Capacitor.Plugins.LoveKeystore.getSecureItem({
    key: "synthetic_keystore_test_key"
  })`);
  console.log('3. getSecureItem:', JSON.stringify(getRes));

  // 4. Verification check
  if (getRes && getRes.value === 'LOVE_SYNTHETIC_CIPHERTEXT_PROBE_778899') {
    console.log('4. Encryption & Decryption Integrity: PASSED');
  } else {
    console.error('4. Encryption & Decryption Integrity: FAILED', getRes);
  }

  ws.close();
  process.exit(0);
}

run().catch(err => {
  console.error('Test execution failed:', err);
  process.exit(1);
});
