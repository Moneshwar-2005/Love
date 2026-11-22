// test_mobile_login_eval.js
const http = require('http');

async function getWsUrl() {
  return new Promise((resolve, reject) => {
    http.get('http://localhost:9222/json', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        const list = JSON.parse(data);
        const page = list.find(t => t.type === 'page' && t.url.includes('localhost'));
        if (page && page.webSocketDebuggerUrl) {
          resolve(page.webSocketDebuggerUrl);
        } else {
          reject(new Error('No webview page target found'));
        }
      });
    }).on('error', reject);
  });
}

async function run() {
  const wsUrl = await getWsUrl();
  console.log('Connecting to WebSocket:', wsUrl);
  const ws = new WebSocket(wsUrl);

  let idCounter = 1;
  const pending = new Map();

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(msg.error);
      else resolve(msg.result);
    }
  };

  await new Promise(resolve => ws.onopen = resolve);

  function send(method, params = {}) {
    const id = idCounter++;
    return new Promise((resolve, reject) => {
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  // 1. Switch to Create Account mode by clicking the Create Account button
  console.log('Clicking Create Account button...');
  const switchRes = await send('Runtime.evaluate', {
    expression: `
      (() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const createTab = buttons.find(b => b.textContent.trim() === 'Create Account');
        if (createTab) {
          createTab.click();
          return { clicked: true, text: createTab.textContent.trim() };
        }
        return { clicked: false };
      })()
    `,
    returnByValue: true
  });
  console.log('Switch to register result:', switchRes.result.value);

  await new Promise(r => setTimeout(r, 600));

  // Check registration form rendered
  const checkRegister = await send('Runtime.evaluate', {
    expression: `
      (() => {
        const email = document.querySelector('input[type="email"]');
        const user = document.querySelector('input[type="text"]');
        const pass = document.querySelector('input[type="password"]');
        const buttons = Array.from(document.querySelectorAll('button'));
        const activeTab = buttons.find(b => b.classList.contains('bg-cyan-500'));
        return {
          activeTabText: activeTab ? activeTab.textContent.trim() : null,
          emailPresent: !!email,
          userPresent: !!user,
          passPresent: !!pass,
          allButtons: buttons.map(b => b.textContent.replace(/\\s+/g, ' ').trim())
        };
      })()
    `,
    returnByValue: true
  });
  console.log('Register mode status:', checkRegister.result.value);

  // 2. Switch back to Sign In using the bottom link ("Already have an account? Sign In")
  console.log('Clicking "Already have an account? Sign In" bottom link...');
  const switchBackRes = await send('Runtime.evaluate', {
    expression: `
      (() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const signInLink = buttons.find(b => b.textContent.includes('Already have an account? Sign In'));
        if (signInLink) {
          signInLink.click();
          return { clicked: true, text: signInLink.textContent.trim() };
        }
        return { clicked: false };
      })()
    `,
    returnByValue: true
  });
  console.log('Switch back via bottom link result:', switchBackRes.result.value);

  await new Promise(r => setTimeout(r, 600));

  const checkSignIn = await send('Runtime.evaluate', {
    expression: `
      (() => {
        const userOrEmail = document.querySelector('input[type="text"]');
        const pass = document.querySelector('input[type="password"]');
        const email = document.querySelector('input[type="email"]');
        const buttons = Array.from(document.querySelectorAll('button'));
        const activeTab = buttons.find(b => b.classList.contains('bg-cyan-500'));
        return {
          activeTabText: activeTab ? activeTab.textContent.trim() : null,
          userOrEmailPresent: !!userOrEmail,
          emailFieldPresent: !!email,
          passPresent: !!pass
        };
      })()
    `,
    returnByValue: true
  });
  console.log('Sign in mode status after bottom link:', checkSignIn.result.value);

  ws.close();
}

run().catch(console.error);
