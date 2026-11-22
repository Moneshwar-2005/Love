const http = require('http');

async function evaluateInApp(expression) {
  // 1. Get targets
  const targets = await new Promise((resolve, reject) => {
    http.get('http://127.0.0.1:9222/json', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(JSON.parse(data)));
    }).on('error', reject);
  });

  const page = targets.find(t => t.type === 'page');
  if (!page || !page.webSocketDebuggerUrl) {
    throw new Error('No page target found');
  }

  // 2. Connect websocket
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.onopen = resolve;
    ws.onerror = reject;
  });

  // 3. Send Runtime.evaluate
  const id = Math.floor(Math.random() * 1000000);
  const req = {
    id,
    method: 'Runtime.evaluate',
    params: {
      expression,
      awaitPromise: true,
      returnByValue: true
    }
  };

  const result = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error('CDP evaluation timed out after 5000ms'));
    }, 5000);

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
    ws.send(JSON.stringify(req));
  });

  ws.close();
  return result;
}

const expr = process.argv.slice(2).join(' ') || 'document.title';
evaluateInApp(expr)
  .then(res => {
    console.log(JSON.stringify(res, null, 2));
    process.exit(0);
  })
  .catch(err => {
    console.error('CDP Evaluation Error:', err);
    process.exit(1);
  });
