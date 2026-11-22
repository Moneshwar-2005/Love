const http = require('http');

async function run() {
  const targets = await new Promise((resolve, reject) => {
    http.get('http://127.0.0.1:9222/json', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(JSON.parse(data)));
    }).on('error', reject);
  });

  const page = targets.find(t => t.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);

  ws.addEventListener('message', (event) => {
    const msg = JSON.parse(event.data);
    if (msg.method === 'Log.entryAdded') {
      console.log('LOG ENTRY:', msg.params.entry);
    } else if (msg.method === 'Runtime.consoleAPICalled') {
      console.log('CONSOLE API:', msg.params.type, msg.params.args);
    } else if (msg.method === 'Runtime.exceptionThrown') {
      console.log('EXCEPTION:', msg.params.exceptionDetails);
    }
  });

  ws.send(JSON.stringify({ id: 1, method: 'Log.enable' }));
  ws.send(JSON.stringify({ id: 2, method: 'Console.enable' }));
  ws.send(JSON.stringify({ id: 3, method: 'Runtime.enable' }));

  setTimeout(() => {
    ws.send(JSON.stringify({
      id: 4,
      method: 'Runtime.evaluate',
      params: { expression: 'fetch("http://192.168.0.176:8000/health")' }
    }));
  }, 300);

  setTimeout(() => {
    ws.close();
    process.exit(0);
  }, 2000);
}

run().catch(err => {
  console.error(err);
  process.exit(1);
});
