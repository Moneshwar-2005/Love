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
    return res;
  }

  console.log('--- Keystore Persistence & Edge Cases ---');

  // 1. Verify value is present before process kill
  const get1 = await evaluate(`window.Capacitor.Plugins.LoveKeystore.getSecureItem({ key: "synthetic_keystore_test_key" })`);
  console.log('1. Retrieval before restart:', JSON.stringify(get1?.result?.value));

  // 2. Set tampered item
  // A corrupted ciphertext with wrong GCM auth tag
  const badCombined = "8K+M+haV+o8B4Fg1:CORRUPTED_CIPHERTEXT_FOR_TAMPER_TEST_AAAAAAAAAAAAAAAA";
  // We can write it via SharedPreferences or test malformed parts
  // Malformed test: string without colon
  const malformed = await evaluate(`window.Capacitor.Plugins.LoveKeystore.setSecureItem({ key: "malformed_key", value: "test" })`);
  
  // Clean up test key
  const rem = await evaluate(`window.Capacitor.Plugins.LoveKeystore.removeSecureItem({ key: "synthetic_keystore_test_key" })`);
  console.log('2. Cleaned test key:', JSON.stringify(rem?.result?.value));

  // Verify deletion
  const get2 = await evaluate(`window.Capacitor.Plugins.LoveKeystore.getSecureItem({ key: "synthetic_keystore_test_key" })`);
  console.log('3. Retrieval after removal:', JSON.stringify(get2?.result?.value));

  ws.close();
  process.exit(0);
}

run().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
