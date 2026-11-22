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
    return await callCdp(ws, 'Runtime.evaluate', {
      expression: expr,
      awaitPromise: true,
      returnByValue: true
    });
  }

  console.log('--- Testing AEAD Authentication Tag Tampering Protection ---');

  // Step 1: Set a secure item
  await evaluate(`window.Capacitor.Plugins.LoveKeystore.setSecureItem({
    key: "tamper_test_key",
    value: "VALID_AUTHENTICATED_VALUE"
  })`);

  // Step 2: Now we will tamper with the entry in SharedPreferences via external command or corrupt it
  // Step 3: Call getSecureItem on the tampered key
  console.log('Step 1: Set item complete.');
  ws.close();
}

run().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
